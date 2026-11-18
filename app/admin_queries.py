"""Read-only admin read models for the demo panel (MODE: P).

Every query is scoped to the caller's organization through ``users.organization_id``
(or ``sales_records.organization_id``). Nothing here writes to the score ledger.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from app import repo

SOURCE_TYPES = {"mission_submission", "sales_record"}


def metrics(conn: sqlite3.Connection, org_id: str) -> dict[str, Any]:
    users = conn.execute(
        """SELECT COUNT(*) AS total, COALESCE(SUM(is_active), 0) AS active
           FROM users WHERE organization_id = ?""",
        (org_id,),
    ).fetchone()
    wallet = conn.execute(
        """SELECT COALESCE(SUM(w.balance), 0) AS total FROM point_wallets w
           JOIN users u ON u.id = w.user_id WHERE u.organization_id = ?""",
        (org_id,),
    ).fetchone()["total"]
    ledger = conn.execute(
        """SELECT COALESCE(SUM(se.points), 0) AS total, COUNT(*) AS events
           FROM score_events se JOIN users u ON u.id = se.user_id
           WHERE u.organization_id = ?""",
        (org_id,),
    ).fetchone()
    sales = conn.execute(
        """SELECT COALESCE(SUM(amount), 0) AS amount, COUNT(*) AS records
           FROM sales_records WHERE organization_id = ? AND status IN ('valid', 'scored')""",
        (org_id,),
    ).fetchone()
    return {
        "users_total": users["total"],
        "users_active": users["active"],
        "wallet_points": wallet,
        "ledger_points": ledger["total"],
        "score_events": ledger["events"],
        "sales_amount": sales["amount"],
        "sales_valid_records": sales["records"],
        "pending_reviews": repo.count_queue(conn, org_id, "submitted"),
    }


def top_visitors(conn: sqlite3.Connection, org_id: str, limit: int = 5) -> list[sqlite3.Row]:
    return conn.execute(
        """SELECT u.id, u.full_name, COALESCE(w.balance, 0) AS balance
           FROM users u LEFT JOIN point_wallets w ON w.user_id = u.id
           WHERE u.organization_id = ? AND u.role = 'visitor' AND u.is_active = 1
           ORDER BY balance DESC, u.full_name LIMIT ?""",
        (org_id, limit),
    ).fetchall()


def _event_filter(
    org_id: str, user_id: str | None, source_type: str | None
) -> tuple[str, list[Any]]:
    where, params = ["u.organization_id = ?"], [org_id]
    if user_id:
        where.append("se.user_id = ?")
        params.append(user_id)
    if source_type in SOURCE_TYPES:
        where.append("se.source_type = ?")
        params.append(source_type)
    return " AND ".join(where), params


def score_events(
    conn: sqlite3.Connection,
    org_id: str,
    *,
    user_id: str | None = None,
    source_type: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[sqlite3.Row]:
    where, params = _event_filter(org_id, user_id, source_type)
    return conn.execute(
        f"""SELECT se.id, se.user_id, u.full_name, se.points, se.source_type, se.source_id,
                   se.rule_code, rv.version AS rule_version, se.occurred_at, se.reason,
                   se.corrects_event_id, se.explain_json, rev.id AS reversed_by
            FROM score_events se
            JOIN users u ON u.id = se.user_id
            JOIN scoring_rule_versions rv ON rv.id = se.rule_version_id
            LEFT JOIN score_events rev ON rev.corrects_event_id = se.id
            WHERE {where}
            ORDER BY se.occurred_at DESC, se.created_at DESC, se.id
            LIMIT ? OFFSET ?""",  # noqa: S608 - `where` is built from constants only
        [*params, limit, offset],
    ).fetchall()


def count_score_events(
    conn: sqlite3.Connection,
    org_id: str,
    user_id: str | None = None,
    source_type: str | None = None,
) -> int:
    where, params = _event_filter(org_id, user_id, source_type)
    return conn.execute(
        f"""SELECT COUNT(*) AS n FROM score_events se
            JOIN users u ON u.id = se.user_id WHERE {where}""",  # noqa: S608
        params,
    ).fetchone()["n"]


def users(conn: sqlite3.Connection, org_id: str, q: str | None = None) -> list[sqlite3.Row]:
    params: list[Any] = [org_id]
    search = ""
    if q and q.strip():
        like = f"%{q.strip()}%"
        search = """AND (u.full_name LIKE ? OR EXISTS (
            SELECT 1 FROM sales_user_map m WHERE m.user_id = u.id
              AND m.organization_id = u.organization_id AND m.user_external_id LIKE ?))"""
        params += [like, like]
    return conn.execute(
        f"""SELECT u.id, u.full_name, u.role, u.is_active, o.name AS org_name,
                   COALESCE(w.balance, 0) AS balance,
                   (SELECT GROUP_CONCAT(m.user_external_id, ', ') FROM sales_user_map m
                     WHERE m.user_id = u.id AND m.organization_id = u.organization_id)
                     AS external_ids,
                   (SELECT COALESCE(SUM(r.amount), 0) FROM sales_records r
                     WHERE r.user_id = u.id AND r.status IN ('valid', 'scored')) AS sales_amount,
                   (SELECT COUNT(*) FROM sales_records r
                     WHERE r.user_id = u.id AND r.status IN ('valid', 'scored')) AS sales_valid
            FROM users u
            JOIN organizations o ON o.id = u.organization_id
            LEFT JOIN point_wallets w ON w.user_id = u.id
            WHERE u.organization_id = ? {search}
            ORDER BY CASE u.role WHEN 'visitor' THEN 0 WHEN 'operator' THEN 1 ELSE 2 END,
                     u.full_name""",  # noqa: S608
        params,
    ).fetchall()


def user_detail(conn: sqlite3.Connection, org_id: str, user_id: str) -> dict[str, Any] | None:
    """None for unknown users *and* for users of another organization."""
    rows = [row for row in users(conn, org_id) if row["id"] == user_id]
    if not rows:
        return None
    return {
        "user": rows[0],
        "events": score_events(conn, org_id, user_id=user_id, limit=50),
        "submissions": conn.execute(
            """SELECT s.id, s.status, s.created_at, m.title
               FROM submissions s JOIN missions m ON m.id = s.mission_id
               WHERE s.user_id = ? ORDER BY s.created_at DESC LIMIT 10""",
            (user_id,),
        ).fetchall(),
        "sales": conn.execute(
            """SELECT row_number, external_id, sale_date, amount, status, import_id
               FROM sales_records WHERE user_id = ? AND organization_id = ?
               ORDER BY created_at DESC, row_number LIMIT 10""",
            (user_id, org_id),
        ).fetchall(),
    }


def audit(
    conn: sqlite3.Connection, org_id: str, limit: int = 50, offset: int = 0
) -> list[sqlite3.Row]:
    return conn.execute(
        """SELECT a.id, a.action, a.entity_type, a.entity_id, a.detail_json, a.created_at,
                  u.full_name AS actor_name
           FROM audit_logs a JOIN users u ON u.id = a.actor_id
           WHERE u.organization_id = ?
           ORDER BY a.created_at DESC, a.id LIMIT ? OFFSET ?""",
        (org_id, limit, offset),
    ).fetchall()


def game_overview(conn: sqlite3.Connection, org_id: str) -> list[dict[str, Any]]:
    """Game XP/coins per visitor — a separate domain from the points ledger."""
    rows = conn.execute(
        """SELECT u.full_name, g.state_json,
                  (SELECT COUNT(*) FROM game_completions c WHERE c.user_id = u.id) AS completions
           FROM users u LEFT JOIN game_progress g ON g.user_id = u.id
           WHERE u.organization_id = ? AND u.role = 'visitor' AND u.is_active = 1""",
        (org_id,),
    ).fetchall()
    out = []
    for row in rows:
        state = json.loads(row["state_json"]) if row["state_json"] else {}
        out.append(
            {
                "name": row["full_name"],
                "xp": state.get("xp", 0),
                "coins": state.get("coins", 0),
                "completions": row["completions"],
            }
        )
    return sorted(out, key=lambda item: (-item["xp"], item["name"]))


def import_user_breakdown(conn: sqlite3.Connection, import_id: str) -> list[sqlite3.Row]:
    """Who received points from an import, and exactly how many (read from the ledger)."""
    return conn.execute(
        """SELECT u.id, u.full_name,
                  SUM(CASE WHEN se.corrects_event_id IS NULL THEN 1 ELSE 0 END) AS events,
                  SUM(CASE WHEN se.corrects_event_id IS NULL THEN se.points ELSE 0 END) AS awarded,
                  SUM(CASE WHEN se.corrects_event_id IS NOT NULL THEN se.points ELSE 0 END)
                    AS corrected,
                  SUM(se.points) AS net
           FROM score_events se JOIN users u ON u.id = se.user_id
           WHERE se.source_type = 'sales_record'
             AND (se.source_id IN (SELECT id FROM sales_records WHERE import_id = ?)
               OR se.corrects_event_id IN (
                    SELECT e.id FROM score_events e
                    JOIN sales_records r ON r.id = e.source_id
                    WHERE r.import_id = ?))
           GROUP BY u.id, u.full_name ORDER BY net DESC, u.full_name""",
        (import_id, import_id),
    ).fetchall()
