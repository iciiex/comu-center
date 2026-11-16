"""Administrator mission management (DEMO): create, activate and assign missions.

Custom missions are completed through the normal server-authoritative game path (answers are
validated, XP is computed on the server, completions are idempotent). The administrator only
decides whether a mission exists, whether it is active, and who it is assigned to.
"""

from __future__ import annotations

import sqlite3
import uuid
from typing import Any

from app import db, game

KINDS = ("daily", "weekly", "sales", "product", "coverage", "streak", "team")
SCOPES = ("all", "branch", "team", "user")
CUSTOM_PREFIX = "custom-"


class AdminMissionError(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def _context(conn: sqlite3.Connection, user_id: str) -> dict[str, str | None]:
    row = conn.execute(
        "SELECT branch_code, supervisor_id FROM employee_positions WHERE user_id = ?", (user_id,)
    ).fetchone()
    return {
        "branch": row["branch_code"] if row else None,
        "team": row["supervisor_id"] if row else None,
    }


def _settings(conn: sqlite3.Connection, org_id: str) -> dict[str, sqlite3.Row]:
    rows = conn.execute("SELECT * FROM mission_settings WHERE organization_id = ?", (org_id,))
    return {row["mission_id"]: row for row in rows}


def _allowed(setting: sqlite3.Row | None, user_id: str, ctx: dict[str, str | None]) -> bool:
    if setting is None:
        return True
    if setting["status"] != "active":
        return False
    scope, value = setting["scope"], setting["scope_value"]
    if scope == "all":
        return True
    if scope == "branch":
        return ctx["branch"] == value
    if scope == "team":
        return ctx["team"] == value
    return user_id == value


def build_mission(row: sqlite3.Row, order: int = 100) -> dict[str, Any]:
    """A custom mission in the same shape as catalog missions (one result step, one note)."""
    return {
        "id": row["id"],
        "order": order,
        "title": row["title"],
        "shortTitle": row["title"][:24],
        "description": row["description"],
        "category": row["category"],
        "difficulty": "medium",
        "estimatedMinutes": 2,
        "xpReward": int(row["xp_reward"]),
        "coinReward": 0,
        "unlock": {},
        "isCustom": True,
        "kind": row["kind"],
        "completion": {"requiredSteps": ["result"]},
        "steps": [
            {
                "id": "result",
                "type": "choice",
                "label": "نتیجه",
                "question": "نتیجهٔ اجرای این مأموریت چه بود؟",
                "options": [
                    {"id": "done", "label": "کامل انجام شد", "emoji": "✅", "hint": "طبق برنامه"},
                    {
                        "id": "partial",
                        "label": "بخشی انجام شد",
                        "emoji": "🟡",
                        "hint": "نیاز به ادامه",
                    },
                    {
                        "id": "blocked",
                        "label": "مانع داشتم",
                        "emoji": "🚧",
                        "hint": "به کمک نیاز دارم",
                    },
                ],
            },
            {
                "id": "note",
                "type": "note",
                "label": "یادداشت",
                "question": "توضیحی برای تیم دارید؟",
                "helper": "اختیاری؛ یک خط کافی است.",
                "placeholder": "مثلاً: مشتری فردا پاسخ می‌دهد",
                "maxLength": 240,
            },
        ],
    }


def custom_for_user(conn: sqlite3.Connection, org_id: str, user_id: str) -> list[dict[str, Any]]:
    """Active custom missions assigned to this user."""
    settings = _settings(conn, org_id)
    ctx = _context(conn, user_id)
    rows = conn.execute(
        "SELECT * FROM admin_missions WHERE organization_id = ? ORDER BY created_at, id", (org_id,)
    ).fetchall()
    return [
        build_mission(row, 100 + index)
        for index, row in enumerate(rows)
        if _allowed(settings.get(row["id"]), user_id, ctx)
    ]


def hidden_for_user(conn: sqlite3.Connection, org_id: str, user_id: str) -> list[str]:
    """Catalog or sales mission ids the administrator switched off or assigned elsewhere."""
    settings = _settings(conn, org_id)
    ctx = _context(conn, user_id)
    return [
        mission_id
        for mission_id, row in settings.items()
        if not mission_id.startswith(CUSTOM_PREFIX) and not _allowed(row, user_id, ctx)
    ]


def get_custom(
    conn: sqlite3.Connection, org_id: str, user_id: str, mission_id: str
) -> dict[str, Any] | None:
    return next((m for m in custom_for_user(conn, org_id, user_id) if m["id"] == mission_id), None)


def _all_definitions(conn: sqlite3.Connection, org_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM admin_missions WHERE organization_id = ? ORDER BY created_at, id", (org_id,)
    ).fetchall()
    base = [*game.catalog()["missions"], *game.sales_catalog()["missions"]]
    return [*base, *[build_mission(row, 100 + i) for i, row in enumerate(rows)]]


def overview(conn: sqlite3.Connection, org_id: str) -> dict[str, Any]:
    """Admin view: every mission with status, assignment and how many visitors completed it."""
    settings = _settings(conn, org_id)
    done = {
        row["mission_id"]: (row["players"], row["completions"])
        for row in conn.execute(
            """SELECT mission_id, COUNT(DISTINCT user_id) AS players, COUNT(*) AS completions
               FROM game_completions GROUP BY mission_id"""
        )
    }
    missions = []
    for definition in _all_definitions(conn, org_id):
        setting = settings.get(definition["id"])
        players, completions = done.get(definition["id"], (0, 0))
        missions.append(
            {
                "id": definition["id"],
                "title": definition["title"],
                "description": definition["description"],
                "category": definition["category"],
                "kind": definition.get("kind"),
                "xp_reward": definition["xpReward"],
                "is_custom": bool(definition.get("isCustom")),
                "is_sales": bool(definition.get("orgAward")),
                "status": setting["status"] if setting else "active",
                "scope": setting["scope"] if setting else "all",
                "scope_value": setting["scope_value"] if setting else None,
                "players_completed": players,
                "completions": completions,
            }
        )
    branches = [
        dict(row)
        for row in conn.execute(
            "SELECT code, name FROM branches WHERE organization_id = ? ORDER BY code", (org_id,)
        )
    ]
    teams = [
        {"id": row["supervisor_id"], "name": row["name"]}
        for row in conn.execute(
            """SELECT DISTINCT p.supervisor_id, s.full_name AS name FROM employee_positions p
               JOIN users s ON s.id = p.supervisor_id
               WHERE p.organization_id = ? AND p.supervisor_id IS NOT NULL ORDER BY s.full_name""",
            (org_id,),
        )
    ]
    visitors = [
        {"id": row["user_id"], "name": row["full_name"], "code": row["employee_code"]}
        for row in conn.execute(
            """SELECT p.user_id, u.full_name, p.employee_code FROM employee_positions p
               JOIN users u ON u.id = p.user_id
               WHERE p.organization_id = ? AND p.position = 'rep' ORDER BY p.employee_code""",
            (org_id,),
        )
    ]
    return {
        "is_demo": True,
        "missions": missions,
        "branches": branches,
        "teams": teams,
        "visitors": visitors,
        "categories": {k: v["label"] for k, v in game.catalog()["categories"].items()},
        "kinds": list(KINDS),
    }


def _validate_scope(conn: sqlite3.Connection, org_id: str, scope: Any, value: Any) -> str | None:
    if scope not in SCOPES:
        raise AdminMissionError(422, "INVALID_SCOPE", "دامنهٔ اختصاص نامعتبر است.")
    if scope == "all":
        return None
    if not isinstance(value, str) or not value:
        raise AdminMissionError(422, "INVALID_SCOPE", "مقصد اختصاص را انتخاب کنید.")
    queries = {
        "branch": "SELECT 1 FROM branches WHERE organization_id = ? AND code = ?",
        "team": "SELECT 1 FROM employee_positions WHERE organization_id = ? AND supervisor_id = ?",
        "user": "SELECT 1 FROM employee_positions WHERE organization_id = ? AND user_id = ?",
    }
    if conn.execute(queries[scope], (org_id, value)).fetchone() is None:
        raise AdminMissionError(404, "SCOPE_TARGET_NOT_FOUND", "مقصد اختصاص پیدا نشد.")
    return value


def create(conn: sqlite3.Connection, admin: Any, payload: dict[str, Any]) -> dict[str, Any]:
    title = str(payload.get("title", "")).strip()
    description = str(payload.get("description", "")).strip()
    category = payload.get("category")
    kind = payload.get("kind")
    xp = payload.get("xp_reward")
    if not 3 <= len(title) <= 60:
        raise AdminMissionError(422, "INVALID_TITLE", "عنوان باید بین ۳ تا ۶۰ نویسه باشد.")
    if not 5 <= len(description) <= 240:
        raise AdminMissionError(422, "INVALID_DESCRIPTION", "شرح باید بین ۵ تا ۲۴۰ نویسه باشد.")
    if category not in game.catalog()["categories"]:
        raise AdminMissionError(422, "INVALID_CATEGORY", "دستهٔ مأموریت نامعتبر است.")
    if kind not in KINDS:
        raise AdminMissionError(422, "INVALID_KIND", "نوع مأموریت نامعتبر است.")
    if isinstance(xp, bool) or not isinstance(xp, int) or not 10 <= xp <= 500:
        raise AdminMissionError(422, "INVALID_XP", "امتیاز تجربه باید بین ۱۰ تا ۵۰۰ باشد.")
    scope = payload.get("scope", "all")
    scope_value = _validate_scope(conn, admin.organization_id, scope, payload.get("scope_value"))
    mission_id = f"{CUSTOM_PREFIX}{uuid.uuid4().hex[:10]}"
    now = db.now_iso()
    conn.execute(
        """INSERT INTO admin_missions
           (id, organization_id, title, description, category, kind, xp_reward, created_by, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (mission_id, admin.organization_id, title, description, category, kind, xp, admin.id, now),
    )
    conn.execute(
        """INSERT INTO mission_settings
           (organization_id, mission_id, status, scope, scope_value, updated_by, updated_at)
           VALUES (?, ?, 'active', ?, ?, ?, ?)""",
        (admin.organization_id, mission_id, scope, scope_value, admin.id, now),
    )
    conn.commit()
    return {"id": mission_id}


def update(
    conn: sqlite3.Connection, admin: Any, mission_id: str, payload: dict[str, Any]
) -> dict[str, Any]:
    known = {d["id"] for d in _all_definitions(conn, admin.organization_id)}
    if mission_id not in known:
        raise AdminMissionError(404, "MISSION_NOT_FOUND", "مأموریت پیدا نشد.")
    current = _settings(conn, admin.organization_id).get(mission_id)
    status = payload.get("status", current["status"] if current else "active")
    if status not in ("active", "inactive"):
        raise AdminMissionError(422, "INVALID_STATUS", "وضعیت نامعتبر است.")
    scope = payload.get("scope", current["scope"] if current else "all")
    value = payload.get("scope_value", current["scope_value"] if current else None)
    value = _validate_scope(conn, admin.organization_id, scope, value)
    conn.execute(
        """INSERT INTO mission_settings
           (organization_id, mission_id, status, scope, scope_value, updated_by, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(organization_id, mission_id) DO UPDATE SET
             status = excluded.status, scope = excluded.scope, scope_value = excluded.scope_value,
             updated_by = excluded.updated_by, updated_at = excluded.updated_at""",
        (admin.organization_id, mission_id, status, scope, value, admin.id, db.now_iso()),
    )
    conn.commit()
    return {"id": mission_id, "status": status, "scope": scope, "scope_value": value}
