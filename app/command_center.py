"""Management command-center figures (DEMO): game engagement within the viewer's scope.

Every figure is computed from stored game progress and completions, for the representatives in the
viewer's scope only (the same scope as the rest of the overview). These are engagement numbers from
DEMO game data. They are not sales KPIs, and no reward is calculated from them.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from typing import Any

from app import game, game_quests

ACTIVE_WINDOW_DAYS = 7
RECENT_LIMIT = 8


def build(
    conn: sqlite3.Connection,
    rep_ids: Iterable[str],
    names: dict[str, str],
    now: datetime | None = None,
) -> dict[str, Any]:
    ids = sorted(set(rep_ids))
    now = now or datetime.now(UTC)
    since = (now - timedelta(days=ACTIVE_WINDOW_DAYS)).isoformat(timespec="seconds")
    base_missions = [mission["id"] for mission in game.catalog()["missions"]]
    levels = game.catalog()["game_config"]["levels"]
    achievement_titles = {item["id"]: item["title"] for item in game.catalog()["achievements"]}

    states: dict[str, dict[str, Any]] = {}
    active: set[str] = set()
    recent_claims: list[dict[str, Any]] = []
    if ids:
        # The id list travels as one JSON parameter, so every query stays fully parameterized.
        ids_json = json.dumps(ids)
        for row in conn.execute(
            """SELECT user_id, state_json FROM game_progress
               WHERE user_id IN (SELECT value FROM json_each(?))""",
            (ids_json,),
        ):
            states[row["user_id"]] = json.loads(row["state_json"])
        active = {
            row["user_id"]
            for row in conn.execute(
                """SELECT DISTINCT user_id FROM game_completions
                   WHERE completed_at >= ? AND user_id IN (SELECT value FROM json_each(?))""",
                (since, ids_json),
            )
        }
        for row in conn.execute(
            """SELECT user_id, quest_id, xp_awarded, claimed_at FROM game_quest_claims
               WHERE claimed_at >= ? AND user_id IN (SELECT value FROM json_each(?))
               ORDER BY claimed_at DESC LIMIT ?""",
            (since, ids_json, RECENT_LIMIT),
        ):
            quest = game_quests.quest_definition(row["quest_id"])
            recent_claims.append(
                {
                    "user_id": row["user_id"],
                    "name": names.get(row["user_id"], "—"),
                    "quest": quest["title"] if quest else row["quest_id"],
                    "xp": int(row["xp_awarded"]),
                    "at": row["claimed_at"],
                }
            )

    # Demo reps are pre-onboarded with zero XP, so "played" means XP earned or a mission completed.
    played = {
        rep_id
        for rep_id, state in states.items()
        if int(state.get("xp", 0)) > 0
        or any(
            int(record.get("completions", 0)) > 0 for record in state.get("missions", {}).values()
        )
    }
    done = sum(
        1
        for state in states.values()
        for mission_id in base_missions
        if int(state.get("missions", {}).get(mission_id, {}).get("completions", 0)) > 0
    )
    possible = len(ids) * len(base_missions)

    per_level: dict[int, dict[str, int]] = {item["level"]: {"reps": 0, "xp": 0} for item in levels}
    for rep_id in ids:
        xp = int(states.get(rep_id, {}).get("xp", 0))
        bucket = per_level[game._level(xp)]
        bucket["reps"] += 1
        bucket["xp"] += xp

    achievements = [
        {
            "user_id": rep_id,
            "name": names.get(rep_id, "—"),
            "achievement": achievement_titles.get(achievement_id, achievement_id),
            "at": at,
        }
        for rep_id, state in states.items()
        for achievement_id, at in state.get("achievements", {}).items()
    ]
    achievements.sort(key=lambda item: item["at"], reverse=True)

    return {
        "label": "DEMO",
        "window_days": ACTIVE_WINDOW_DAYS,
        "reps": len(ids),
        "players": len(played),
        "active_players": len(active),
        "mission_completion": {
            "done": done,
            "possible": possible,
            "pct": round(100 * done / possible) if possible else 0,
            "missions_per_rep": len(base_missions),
        },
        "xp_distribution": [
            {
                "level": item["level"],
                "title": item["title"],
                "reps": per_level[item["level"]]["reps"],
                "xp": per_level[item["level"]]["xp"],
            }
            for item in levels
        ],
        "recent_achievements": achievements[:RECENT_LIMIT],
        "recent_claims": recent_claims,
        "note": (
            "مشارکت ویزیتورهای محدودهٔ شما، بر پایهٔ داده‌های نمایشی بازی. "
            "این ارقام شاخص فروش نیستند و هیچ پاداشی از آن‌ها محاسبه نمی‌شود."
        ),
    }


def activity(
    conn: sqlite3.Connection,
    rep_ids: Iterable[str],
    names: dict[str, str],
    limit: int = 60,
) -> list[dict[str, Any]]:
    """Recent player activity, newest first: missions, level-ups, quest claims and achievements."""
    ids = sorted(set(rep_ids))
    if not ids:
        return []
    ids_json = json.dumps(ids)
    titles = {m["id"]: m["title"] for m in game._all_missions()}
    titles.update({row["id"]: row["title"] for row in conn.execute("SELECT id, title FROM admin_missions")})
    achievement_titles = {item["id"]: item["title"] for item in game.catalog()["achievements"]}
    items: list[dict[str, Any]] = []

    for row in conn.execute(
        """SELECT user_id, mission_id, completed_at,
                  json_extract(response_json, '$.entry.rewards.xp') AS xp,
                  json_extract(response_json, '$.entry.levelBefore') AS level_before,
                  json_extract(response_json, '$.entry.levelAfter') AS level_after
           FROM game_completions
           WHERE user_id IN (SELECT value FROM json_each(?))
           ORDER BY completed_at DESC LIMIT ?""",
        (ids_json, limit),
    ):
        name = names.get(row["user_id"], "—")
        base = {"user_id": row["user_id"], "name": name, "at": row["completed_at"]}
        items.append(
            {**base, "kind": "mission", "title": titles.get(row["mission_id"], row["mission_id"]),
             "xp": int(row["xp"] or 0)}
        )
        if row["level_after"] and row["level_before"] and row["level_after"] > row["level_before"]:
            items.append({**base, "kind": "level", "title": str(row["level_after"]), "xp": None})

    for row in conn.execute(
        """SELECT user_id, quest_id, xp_awarded, claimed_at FROM game_quest_claims
           WHERE user_id IN (SELECT value FROM json_each(?))
           ORDER BY claimed_at DESC LIMIT ?""",
        (ids_json, limit),
    ):
        quest = game_quests.quest_definition(row["quest_id"])
        items.append(
            {"kind": "quest", "user_id": row["user_id"], "name": names.get(row["user_id"], "—"),
             "title": quest["title"] if quest else row["quest_id"], "xp": int(row["xp_awarded"]),
             "at": row["claimed_at"]}
        )

    for row in conn.execute(
        "SELECT user_id, state_json FROM game_progress WHERE user_id IN (SELECT value FROM json_each(?))",
        (ids_json,),
    ):
        for achievement_id, at in json.loads(row["state_json"]).get("achievements", {}).items():
            items.append(
                {"kind": "achievement", "user_id": row["user_id"],
                 "name": names.get(row["user_id"], "—"),
                 "title": achievement_titles.get(achievement_id, achievement_id), "xp": None, "at": at}
            )

    items.sort(key=lambda item: item["at"], reverse=True)
    return items[:limit]
