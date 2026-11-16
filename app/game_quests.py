"""Weekly quests (Kiloos DEMO): server-side progress, view model and claim state.

Pure functions only: no database access and no import of ``app.game``, so ``game`` can call them
while building its payloads. Claims, XP awards and idempotency live in ``game.claim_quest``.

Progress is derived from the completed-mission history of the current ISO week (UTC). The browser
never sends progress and never decides whether a quest is complete.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

QUESTS_CATALOG_PATH = Path(__file__).with_name("game_quests_catalog.json")

CategoryOf = Callable[[str], str | None]


@lru_cache(maxsize=1)
def quests_catalog() -> dict[str, Any]:
    return json.loads(QUESTS_CATALOG_PATH.read_text(encoding="utf-8"))


def quest_definition(quest_id: str) -> dict[str, Any] | None:
    return next((quest for quest in quests_catalog()["quests"] if quest["id"] == quest_id), None)


def week_key(day_key: str) -> str:
    """ISO week of a UTC date key, for example ``2026-W46``."""
    year, week, _ = date.fromisoformat(day_key).isocalendar()
    return f"{year}-W{week:02d}"


def week_bounds(day_key: str) -> tuple[str, str]:
    """Monday and Sunday (UTC date keys) of the ISO week that contains ``day_key``."""
    day = date.fromisoformat(day_key)
    start = day - timedelta(days=day.weekday())
    return start.isoformat(), (start + timedelta(days=6)).isoformat()


def _objective_progress(
    quest: dict[str, Any],
    entries: list[dict[str, Any]],
    category_of: CategoryOf,
    team_completions: int,
) -> int:
    objective = quest["objective"]
    kind = objective["type"]
    if kind == "completions":
        return len(entries)
    if kind == "category":
        wanted = objective["category"]
        return sum(1 for entry in entries if category_of(entry["missionId"]) == wanted)
    if kind == "distinct_categories":
        categories = {category_of(entry["missionId"]) for entry in entries}
        categories.discard(None)
        return len(categories)
    if kind == "team_completions":
        return team_completions
    if kind == "active_days":
        return len({str(entry["completedAt"])[:10] for entry in entries})
    raise ValueError(f"Unknown quest objective type: {kind}")


def _claims_for_week(progress: dict[str, Any], wk: str) -> dict[str, dict[str, Any]]:
    state = progress.get("quests") or {}
    if state.get("week") != wk:
        return {}
    return dict(state.get("claimed", {}))


def weekly_quests(
    progress: dict[str, Any],
    day_key: str,
    category_of: CategoryOf,
    team_completions: int = 0,
) -> dict[str, Any]:
    """View model for the current ISO week: progress, claim status and reward per quest."""
    wk = week_key(day_key)
    start, end = week_bounds(day_key)
    claimed = _claims_for_week(progress, wk)
    entries = [
        entry
        for entry in progress.get("history", [])
        if week_key(str(entry["completedAt"])[:10]) == wk
    ]
    views: list[dict[str, Any]] = []
    for quest in quests_catalog()["quests"]:
        target = int(quest["objective"]["target"])
        raw = _objective_progress(quest, entries, category_of, team_completions)
        claim = claimed.get(quest["id"])
        complete = raw >= target
        views.append(
            {
                "id": quest["id"],
                "title": quest["title"],
                "description": quest["description"],
                "icon": quest.get("icon", "target"),
                "objective": dict(quest["objective"]),
                "progress": min(raw, target),
                "target": target,
                "complete": complete,
                "status": "claimed" if claim else "claimable" if complete else "in_progress",
                "claimed": claim is not None,
                "claimedAt": claim.get("claimedAt") if claim else None,
                "rewardXp": int(quest["rewardXp"]),
            }
        )
    return {"label": "DEMO", "weekKey": wk, "weekStart": start, "weekEnd": end, "quests": views}


def with_claim(
    progress: dict[str, Any], day_key: str, quest_id: str, claimed_at: str, xp: int
) -> dict[str, Any]:
    """Claim state after one more claim. Claims from earlier weeks are dropped."""
    wk = week_key(day_key)
    claimed = _claims_for_week(progress, wk)
    claimed[quest_id] = {"claimedAt": claimed_at, "xp": xp}
    return {"week": wk, "claimed": claimed}
