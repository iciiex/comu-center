"""Game-economy rewards for approved Kiloos missions (D-009 PROPOSED).

XP and coins live in the Sales Quest Arena economy: ``game_reward_events`` (append-only ledger)
plus the ``game_progress`` projection. Nothing here touches ``score_events``,
``point_transactions`` or ``point_wallets`` — organizational points stay in ``scoring``.

``grant_game_reward`` never opens or commits a transaction: the caller (review approval or an
auto-approved submission) owns it, so the status change, the organizational score and the game
reward commit or roll back together.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from typing import Any

from app import game


def reward_values(conn: sqlite3.Connection, submission: sqlite3.Row) -> tuple[int, int]:
    """XP/coins frozen at submit time; legacy rows fall back to the mission's current values."""
    xp = submission["game_xp_snapshot"]
    coins = submission["game_coins_snapshot"]
    if xp is None or coins is None:
        mission = conn.execute(
            "SELECT game_xp, game_coins FROM missions WHERE id = ?", (submission["mission_id"],)
        ).fetchone()
        if mission is None:
            return 0, 0
        xp = mission["game_xp"] if xp is None else xp
        coins = mission["game_coins"] if coins is None else coins
    return int(xp), int(coins)


def grant_game_reward(conn: sqlite3.Connection, submission: sqlite3.Row) -> bool:
    """Credit game XP/coins once for an approved submission. Returns True only when it granted."""
    if submission["status"] != "approved":
        return False
    xp, coins = reward_values(conn, submission)
    if xp == 0 and coins == 0:
        return False

    now = game._now()
    completed_at = now.isoformat()
    cursor = conn.execute(
        """INSERT OR IGNORE INTO game_reward_events
           (id, user_id, source_type, source_id, mission_id, xp, coins, created_at)
           VALUES (?, ?, 'mission_submission', ?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), submission["user_id"], submission["id"], submission["mission_id"],
         xp, coins, completed_at),
    )
    if cursor.rowcount != 1:
        return False  # already granted: a retry or repeated approval changes nothing

    user = conn.execute(
        "SELECT id, full_name FROM users WHERE id = ?", (submission["user_id"],)
    ).fetchone()
    progress = game._initialize(conn, user["id"], user["full_name"])
    day_key = game._day_key(now)

    xp_before = int(progress["xp"])
    xp_after = xp_before + xp
    coins_after = int(progress["coins"]) + coins
    last_active = progress["streak"].get("lastActiveDate")
    gap = game._date_diff(last_active, day_key) if last_active else None
    streak_count = (
        int(progress["streak"]["count"])
        if gap == 0
        else int(progress["streak"]["count"]) + 1
        if gap == 1
        else 1
    )
    note = (submission["note"] or "").strip()
    answers: dict[str, Any] = {"answer": note} if note else {}
    entry = {
        "id": f"{int(now.timestamp() * 1000):x}-{uuid.uuid4().hex[:6]}",
        "missionId": submission["mission_id"],
        "completedAt": completed_at,
        "answers": answers,
        "flags": ["note_added"] if note else [],
        "wasDaily": False,
        "rewards": {
            "lines": [
                {"ruleId": "mission_complete", "label": "Mission approved", "xp": xp,
                 "coins": coins}
            ],
            "xp": xp,
            "coins": coins,
        },
        "xpBefore": xp_before,
        "xpAfter": xp_after,
        "coinsAfter": coins_after,
        "levelBefore": game._level(xp_before),
        "levelAfter": game._level(xp_after),
        "streakAfter": streak_count,
        "achievementsUnlocked": [],
    }
    previous = progress.setdefault("missions", {}).get(submission["mission_id"], {})
    progress["missions"][submission["mission_id"]] = {
        "completions": int(previous.get("completions", 0)) + 1,
        "firstCompletedAt": previous.get("firstCompletedAt") or completed_at,
        "lastCompletedAt": completed_at,
        "bestRating": previous.get("bestRating"),
    }
    progress["xp"] = xp_after
    progress["coins"] = coins_after
    progress["streak"] = {
        "count": streak_count,
        "best": max(int(progress["streak"]["best"]), streak_count),
        "lastActiveDate": day_key,
    }
    progress.setdefault("drafts", {}).pop(submission["mission_id"], None)
    history = [entry, *game._history(conn, user["id"], limit=199)]
    progress["history"] = history[: int(game.catalog()["game_config"]["history"]["maxEntries"])]
    unlocked = game._new_achievements(progress, progress["history"])
    entry["achievementsUnlocked"] = unlocked
    for achievement_id in unlocked:
        progress.setdefault("achievements", {})[achievement_id] = completed_at

    # Mirror into game_completions so /history lists approvals next to device-style completions.
    key = f"approval:{submission['id']}"
    conn.execute(
        """INSERT INTO game_completions
           (id, user_id, mission_id, idempotency_key, request_sha256, response_json, completed_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            str(uuid.uuid4()),
            user["id"],
            submission["mission_id"],
            key,
            hashlib.sha256(key.encode()).hexdigest(),
            json.dumps({"entry": entry, "date_key": day_key}, ensure_ascii=False,
                       separators=(",", ":")),
            completed_at,
        ),
    )
    game._save(conn, user["id"], progress)
    return True
