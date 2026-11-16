"""Rankings for the Kiloos demo: individual, branch and team, over season, day, week or month.

Organizational points come from the append-only score ledger. Game XP comes from completed missions
and claimed weekly quests. Windows (daily, weekly, monthly) count what was recorded inside them, in
UTC:
  - score events are timestamped when a sales row is processed, not on the sale date;
  - game XP is timestamped when a mission or quest is completed.
The season is the active competition window; it has no previous window, so it has no movement.
Movement compares a player's rank with the same ranking over the previous window of equal length.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, date, datetime, timedelta
from typing import Any

from app import game, repo

SCOPES = ("individual", "branch", "team")
WINDOWS = ("season", "daily", "weekly", "monthly")
UNBOUNDED_START = "0000-01-01T00:00:00+00:00"
UNBOUNDED_END = "9999-12-31T23:59:59+00:00"
UNASSIGNED = "unassigned"


def _stamp(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat(timespec="seconds")


def _midnight(day: date) -> datetime:
    return datetime(day.year, day.month, day.day, tzinfo=UTC)


def window_bounds(window: str, now: datetime) -> dict[str, Any]:
    """Inclusive UTC bounds of the current and the previous window, as stored timestamps.

    ``window`` must be daily, weekly or monthly. Season bounds come from the competition.
    """
    today = now.astimezone(UTC).date()
    if window == "daily":
        start_day = today
        end_day = today + timedelta(days=1)
        prev_day = today - timedelta(days=1)
        label = f"Today · {today.isoformat()} (UTC)"
    elif window == "weekly":
        start_day = today - timedelta(days=today.weekday())
        end_day = start_day + timedelta(days=7)
        prev_day = start_day - timedelta(days=7)
        iso_year, iso_week, _ = today.isocalendar()
        last_day = end_day - timedelta(days=1)
        label = (
            f"Week {iso_year}-W{iso_week:02d} · "
            f"{start_day.isoformat()} – {last_day.isoformat()} (UTC)"
        )
    elif window == "monthly":
        start_day = today.replace(day=1)
        end_day = (start_day + timedelta(days=32)).replace(day=1)
        prev_day = (start_day - timedelta(days=1)).replace(day=1)
        label = f"{start_day:%Y-%m} · calendar month (UTC)"
    else:
        raise ValueError(f"Window has no calendar bounds: {window}")
    start = _midnight(start_day)
    end = _midnight(end_day) - timedelta(seconds=1)
    prev_start = _midnight(prev_day)
    prev_end = _midnight(start_day) - timedelta(seconds=1)
    return {
        "label": label,
        "start": _stamp(start),
        "end": _stamp(end),
        "previous_start": _stamp(prev_start),
        "previous_end": _stamp(prev_end),
    }


def _points(
    conn: sqlite3.Connection, org_id: str, start: str, end: str
) -> dict[str, dict[str, Any]]:
    rows = conn.execute(
        """SELECT se.user_id, SUM(se.points) AS total, MIN(se.occurred_at) AS first_at
           FROM score_events se
           JOIN users u ON u.id = se.user_id
           WHERE u.organization_id = ? AND se.occurred_at >= ? AND se.occurred_at <= ?
           GROUP BY se.user_id""",
        (org_id, start, end),
    ).fetchall()
    return {
        row["user_id"]: {"total": int(row["total"]), "first_at": row["first_at"]} for row in rows
    }


def _window_game_xp(conn: sqlite3.Connection, start: str, end: str) -> dict[str, int]:
    xp: dict[str, int] = {}
    for row in conn.execute(
        """SELECT user_id, SUM(json_extract(response_json, '$.entry.rewards.xp')) AS xp
           FROM game_completions WHERE completed_at >= ? AND completed_at <= ? GROUP BY user_id""",
        (start, end),
    ):
        xp[row["user_id"]] = xp.get(row["user_id"], 0) + int(row["xp"] or 0)
    for row in conn.execute(
        """SELECT user_id, SUM(xp_awarded) AS xp
           FROM game_quest_claims WHERE claimed_at >= ? AND claimed_at <= ? GROUP BY user_id""",
        (start, end),
    ):
        xp[row["user_id"]] = xp.get(row["user_id"], 0) + int(row["xp"] or 0)
    return xp


def _season_game_state(conn: sqlite3.Connection, user_ids: list[str]) -> dict[str, dict[str, int]]:
    if not user_ids:
        return {}
    marks = ",".join("?" * len(user_ids))
    out: dict[str, dict[str, int]] = {}
    for row in conn.execute(
        f"SELECT user_id, state_json FROM game_progress WHERE user_id IN ({marks})",  # noqa: S608
        user_ids,
    ):
        xp = int(json.loads(row["state_json"]).get("xp", 0))
        out[row["user_id"]] = {"xp": xp, "level": game._level(xp)}
    return out


def _participants(conn: sqlite3.Connection, org_id: str) -> list[sqlite3.Row]:
    return conn.execute(
        """SELECT u.id AS user_id, u.full_name, p.employee_code, p.branch_code, p.supervisor_id,
                  b.name AS branch_name
           FROM users u
           LEFT JOIN employee_positions p ON p.user_id = u.id
           LEFT JOIN branches b ON b.organization_id = u.organization_id AND b.code = p.branch_code
           WHERE u.organization_id = ? AND u.role = 'visitor' AND u.is_active = 1""",
        (org_id,),
    ).fetchall()


def _names(conn: sqlite3.Connection, org_id: str) -> dict[str, str]:
    return {
        row["id"]: row["full_name"]
        for row in conn.execute(
            "SELECT id, full_name FROM users WHERE organization_id = ?", (org_id,)
        )
    }


def _measure(
    conn: sqlite3.Connection,
    org_id: str,
    people: list[sqlite3.Row],
    scope: str,
    window: str,
    start: str,
    end: str,
    names: dict[str, str],
) -> list[dict[str, Any]]:
    """Organizational points and game XP per participant, aggregated to the requested scope."""
    points = _points(conn, org_id, start, end)
    season_state = _season_game_state(conn, [p["user_id"] for p in people])
    if window == "season":
        xp_by_user = {uid: state["xp"] for uid, state in season_state.items()}
    else:
        xp_by_user = _window_game_xp(conn, start, end)

    if scope == "individual":
        return [
            {
                "key": p["user_id"],
                "user_id": p["user_id"],
                "name": p["full_name"],
                "subtitle": p["branch_name"] or p["branch_code"] or "",
                "employee_code": p["employee_code"],
                "branch_code": p["branch_code"],
                "branch_name": p["branch_name"],
                "supervisor_id": p["supervisor_id"],
                "members": 1,
                "org_points": points.get(p["user_id"], {}).get("total", 0),
                "first_at": points.get(p["user_id"], {}).get("first_at"),
                "game_xp": xp_by_user.get(p["user_id"], 0),
                # Level is always the player's current level, whatever the window.
                "level": season_state.get(p["user_id"], {}).get("level"),
            }
            for p in people
        ]

    groups: dict[str, list[sqlite3.Row]] = {}
    for p in people:
        if scope == "team":
            key = p["supervisor_id"] or UNASSIGNED
        else:
            key = p["branch_code"] or UNASSIGNED
        groups.setdefault(key, []).append(p)

    out: list[dict[str, Any]] = []
    for key, members in groups.items():
        first = members[0]
        if scope == "team":
            name = (
                names.get(first["supervisor_id"], "Unassigned")
                if key != UNASSIGNED
                else "Unassigned"
            )
            subtitle = first["branch_name"] or first["branch_code"] or ""
        else:
            name = first["branch_name"] or first["branch_code"] or "Unassigned"
            subtitle = f"{len(members)} representatives"
        firsts = [points[m["user_id"]]["first_at"] for m in members if m["user_id"] in points]
        out.append(
            {
                "key": key,
                "user_id": None,
                "name": name,
                "subtitle": subtitle,
                "employee_code": None,
                "branch_code": first["branch_code"] if scope == "team" else key,
                "branch_name": first["branch_name"],
                "supervisor_id": first["supervisor_id"] if scope == "team" else None,
                "members": len(members),
                "org_points": sum(points.get(m["user_id"], {}).get("total", 0) for m in members),
                "first_at": min(firsts) if firsts else None,
                "game_xp": sum(xp_by_user.get(m["user_id"], 0) for m in members),
                "level": None,
            }
        )
    return out


def _ordered(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        items,
        key=lambda i: (-i["org_points"], -i["game_xp"], i["first_at"] or "9999", i["name"]),
    )


def _previous_ranks(items: list[dict[str, Any]]) -> dict[str, int]:
    """Ranks in the previous window. Only entries with activity there get a rank."""
    ranks: dict[str, int] = {}
    for position, item in enumerate(_ordered(items), start=1):
        if item["org_points"] or item["game_xp"]:
            ranks[item["key"]] = position
    return ranks


def build(
    conn: sqlite3.Connection,
    org_id: str,
    viewer_id: str,
    *,
    scope: str = "individual",
    window: str = "season",
    branch: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    if scope not in SCOPES or window not in WINDOWS:
        raise ValueError("Unsupported scope or window.")
    now = now or datetime.now(UTC)
    competition = repo.active_competition(conn, org_id)

    if window == "season":
        start = competition["starts_at"] if competition else UNBOUNDED_START
        end = competition["ends_at"] if competition else UNBOUNDED_END
        previous = None
        label = competition["title"] if competition else "Season"
        period = None
    else:
        bounds = window_bounds(window, now)
        start, end, label = bounds["start"], bounds["end"], bounds["label"]
        previous = (bounds["previous_start"], bounds["previous_end"])
        period = {
            "start": bounds["start"],
            "end": bounds["end"],
            "previous_start": bounds["previous_start"],
            "previous_end": bounds["previous_end"],
        }

    participants = _participants(conn, org_id)
    viewer = next((p for p in participants if p["user_id"] == viewer_id), None)
    # The branch filter narrows individual rankings only; branch and team rankings stay complete.
    people = [
        p
        for p in participants
        if not (scope == "individual" and branch and p["branch_code"] != branch)
    ]
    names = _names(conn, org_id)
    items = _ordered(_measure(conn, org_id, people, scope, window, start, end, names))

    previous_ranks: dict[str, int] = {}
    if previous is not None:
        prev_items = _measure(conn, org_id, people, scope, window, previous[0], previous[1], names)
        previous_ranks = _previous_ranks(prev_items)

    rows: list[dict[str, Any]] = []
    for position, item in enumerate(items, start=1):
        active = bool(item["org_points"] or item["game_xp"])
        prev_rank = previous_ranks.get(item["key"])
        movement: str | None = None
        places: int | None = None
        if previous is not None and active:
            if prev_rank is None:
                movement = "new"
            else:
                places = prev_rank - position
                movement = "up" if places > 0 else "down" if places < 0 else "same"
        if scope == "individual":
            is_me = item["user_id"] == viewer_id
            in_my_group = False
        elif scope == "team":
            is_me = False
            in_my_group = viewer is not None and (
                item["key"] == (viewer["supervisor_id"] or UNASSIGNED)
            )
        else:
            is_me = False
            in_my_group = viewer is not None and (
                item["key"] == (viewer["branch_code"] or UNASSIGNED)
            )
        rows.append(
            {
                "rank": position,
                "previous_rank": prev_rank,
                "movement": movement,
                "places": abs(places) if places is not None else None,
                "id": item["key"],
                "user_id": item["user_id"],
                "name": item["name"],
                "subtitle": item["subtitle"],
                "employee_code": item["employee_code"],
                "branch_code": item["branch_code"],
                "branch_name": item["branch_name"],
                "members": item["members"],
                "org_points": item["org_points"],
                "game_xp": item["game_xp"],
                "level": item["level"],
                "is_me": is_me,
                "in_my_group": in_my_group,
            }
        )

    me = next((row for row in rows if row["is_me"] or row["in_my_group"]), None)
    note = (
        "فصل = رقابت فعال. رتبه بر پایهٔ امتیاز سازمانی (دفتر ثبت غیرقابل ویرایش) است؛ "
        "امتیاز تجربهٔ بازی مجموع تاکنون است و جداگانه نمایش داده می‌شود."
        if window == "season"
        else "بازه = آنچه در همین بازه (به وقت UTC) ثبت شده است. امتیاز سازمانی هنگام پردازش "
        "ردیف فروش و امتیاز تجربه هنگام انجام مأموریت یا چالش زمان‌گذاری می‌شود. جابه‌جایی "
        "با بازهٔ قبلی هم‌طول مقایسه می‌شود؛ «جدید» یعنی در بازهٔ قبل فعالیتی نبوده است."
    )
    return {
        "is_demo": True,
        "scope": scope,
        "window": window,
        "window_label": label,
        "period": period,
        "competition": (
            {
                "title": competition["title"],
                "starts_at": competition["starts_at"],
                "ends_at": competition["ends_at"],
                "is_sample": bool(competition["is_sample"]),
            }
            if competition
            else None
        ),
        "rows": rows,
        "me": me,
        "totals": {
            "groups": len(rows),
            "org_points": sum(row["org_points"] for row in rows),
            "game_xp": sum(row["game_xp"] for row in rows),
        },
        "note": note,
    }
