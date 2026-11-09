"""Data access for missions, submissions, wallet and leaderboard.

All org-scoped queries take the caller's organization explicitly: permission ×
organization scope is enforced here, not in templates.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

from app.scoring import ScoringError, award_mission_approval, reverse_event


class DomainError(Exception):
    """Business-rule violation with a stable code for the UI/API."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def now_iso() -> str:
    return datetime.now(tz=UTC).isoformat(timespec="seconds")


def _new_id() -> str:
    return str(uuid.uuid4())


def audit(
    conn: sqlite3.Connection,
    actor_id: str | None,
    action: str,
    entity_type: str,
    entity_id: str,
    detail: dict[str, Any] | None = None,
) -> None:
    conn.execute(
        """INSERT INTO audit_logs
           (id, actor_id, action, entity_type, entity_id, detail_json, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (_new_id(), actor_id, action, entity_type, entity_id,
         json.dumps(detail or {}, ensure_ascii=False), now_iso()),
    )


# --------------------------------------------------------------------------- missions


def list_active_missions(conn: sqlite3.Connection, user) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT m.*,
               (SELECT COUNT(*) FROM submissions s
                 WHERE s.mission_id = m.id AND s.user_id = ?) AS my_count
        FROM missions m
        WHERE m.organization_id = ?
          AND m.status = 'active'
          AND m.starts_at <= ?
          AND m.ends_at >= ?
        ORDER BY m.ends_at ASC, m.title ASC
        """,
        (user.id, user.organization_id, now_iso(), now_iso()),
    ).fetchall()


def get_mission_for_user(conn: sqlite3.Connection, mission_id: str, user) -> sqlite3.Row | None:
    return conn.execute(
        """
        SELECT * FROM missions
        WHERE id = ? AND organization_id = ? AND status = 'active'
          AND starts_at <= ? AND ends_at >= ?
        """,
        (mission_id, user.organization_id, now_iso(), now_iso()),
    ).fetchone()


def mission_by_id(conn: sqlite3.Connection, mission_id: str, org_id: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM missions WHERE id = ? AND organization_id = ?", (mission_id, org_id)
    ).fetchone()


def count_user_submissions(conn: sqlite3.Connection, user_id: str, mission_id: str) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM submissions WHERE user_id = ? AND mission_id = ?",
        (user_id, mission_id),
    ).fetchone()
    return int(row["n"])


# ----------------------------------------------------------------------- submissions


def create_submission(
    conn: sqlite3.Connection,
    mission: sqlite3.Row,
    user,
    request_id: str,
    note: str,
    evidence: dict[str, Any] | None,
) -> tuple[sqlite3.Row, bool]:
    """Create a submission once per request_id. Returns (submission, created)."""
    existing = conn.execute(
        "SELECT * FROM submissions WHERE user_id = ? AND request_id = ?",
        (user.id, request_id),
    ).fetchone()
    if existing is not None:
        return existing, False

    if count_user_submissions(conn, user.id, mission["id"]) >= mission["max_per_user"]:
        raise DomainError("MAX_ATTEMPTS_REACHED", "سقف تعداد انجام این مأموریت تکمیل شده است.")
    if evidence is None:
        raise DomainError("EVIDENCE_REQUIRED", "برای این مأموریت ثبت تصویر شاهد الزامی است.")

    submission_id = _new_id()
    status = "submitted" if mission["requires_review"] else "approved"
    created_at = now_iso()
    try:
        with conn:
            conn.execute(
                """INSERT INTO submissions
                   (id, mission_id, user_id, status, note, request_id, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (submission_id, mission["id"], user.id, status, note.strip()[:500],
                 request_id, created_at),
            )
            conn.execute(
                """INSERT INTO submission_evidences
                   (id, submission_id, file_name, content_type, storage_path, sha256, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    _new_id(),
                    submission_id,
                    evidence["file_name"],
                    evidence["content_type"],
                    evidence["storage_path"],
                    evidence["sha256"],
                    created_at,
                ),
            )
            audit(conn, user.id, "submission.created", "submission", submission_id,
                  {"mission_id": mission["id"]})
    except sqlite3.IntegrityError:
        duplicate = conn.execute(
            "SELECT * FROM submissions WHERE user_id = ? AND request_id = ?",
            (user.id, request_id),
        ).fetchone()
        if duplicate is not None:
            return duplicate, False
        raise

    submission = conn.execute(
        "SELECT * FROM submissions WHERE id = ?", (submission_id,)
    ).fetchone()
    if not mission["requires_review"]:
        award_mission_approval(conn, submission, actor_id=None)
    return submission, True


def submission_detail(conn: sqlite3.Connection, submission_id: str) -> sqlite3.Row | None:
    return conn.execute(
        """
        SELECT s.*, m.title AS mission_title, m.points AS mission_points,
               m.organization_id AS organization_id, u.full_name AS user_name
        FROM submissions s
        JOIN missions m ON m.id = s.mission_id
        JOIN users u ON u.id = s.user_id
        WHERE s.id = ?
        """,
        (submission_id,),
    ).fetchone()


def submission_evidences(conn: sqlite3.Connection, submission_id: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM submission_evidences WHERE submission_id = ? ORDER BY created_at",
        (submission_id,),
    ).fetchall()


def list_user_submissions(
    conn: sqlite3.Connection, user_id: str, mission_id: str | None = None
) -> list[sqlite3.Row]:
    if mission_id:
        return conn.execute(
            """SELECT s.*, m.title AS mission_title FROM submissions s
               JOIN missions m ON m.id = s.mission_id
               WHERE s.user_id = ? AND s.mission_id = ?
               ORDER BY s.created_at DESC""",
            (user_id, mission_id),
        ).fetchall()
    return conn.execute(
        """SELECT s.*, m.title AS mission_title FROM submissions s
           JOIN missions m ON m.id = s.mission_id
           WHERE s.user_id = ? ORDER BY s.created_at DESC LIMIT 20""",
        (user_id,),
    ).fetchall()


_QUEUE_WHERE = """
    FROM submissions s
    JOIN missions m ON m.id = s.mission_id
    JOIN users u ON u.id = s.user_id
    WHERE m.organization_id = ? AND s.status = ?
"""


def list_queue(
    conn: sqlite3.Connection,
    org_id: str,
    status: str = "submitted",
    *,
    limit: int | None = None,
    offset: int = 0,
) -> list[sqlite3.Row]:
    """Review queue, oldest first (stable order for pagination)."""
    select = """
        SELECT s.*, m.title AS mission_title, u.full_name AS user_name,
               (SELECT COUNT(*) FROM submission_evidences e
                 WHERE e.submission_id = s.id) AS evidence_count
    """
    order = " ORDER BY s.created_at ASC, s.id ASC"
    if limit is None:
        return conn.execute(select + _QUEUE_WHERE + order, (org_id, status)).fetchall()
    return conn.execute(
        select + _QUEUE_WHERE + order + " LIMIT ? OFFSET ?",
        (org_id, status, limit, offset),
    ).fetchall()


def count_queue(conn: sqlite3.Connection, org_id: str, status: str = "submitted") -> int:
    row = conn.execute("SELECT COUNT(*) AS n" + _QUEUE_WHERE, (org_id, status)).fetchone()
    return int(row["n"])


def review_submission(
    conn: sqlite3.Connection,
    submission: sqlite3.Row,
    actor,
    decision: str,
    reason: str = "",
) -> tuple[sqlite3.Row, bool]:
    """Approve or reject. Approval may create a score event (idempotent)."""
    if submission["status"] != "submitted":
        raise DomainError("ALREADY_REVIEWED", "این درخواست قبلاً بررسی شده است.")
    if decision not in {"approve", "reject"}:
        raise DomainError("INVALID_DECISION", "تصمیم نامعتبر است.")
    if decision == "reject" and not reason.strip():
        raise DomainError("REASON_REQUIRED", "برای رد، ثبت دلیل الزامی است.")

    new_status = "approved" if decision == "approve" else "rejected"
    with conn:
        cursor = conn.execute(
            """UPDATE submissions
               SET status = ?, reviewed_at = ?, reviewed_by = ?, rejection_reason = ?
               WHERE id = ? AND status = 'submitted'""",
            (new_status, now_iso(), actor.id, reason.strip() or None, submission["id"]),
        )
        if cursor.rowcount != 1:
            # Another reviewer won the race; rolling back keeps state consistent.
            raise DomainError("ALREADY_REVIEWED", "این درخواست قبلاً بررسی شده است.")
        audit(conn, actor.id, f"submission.{new_status}", "submission", submission["id"],
              {"reason": reason.strip()[:300]})

    updated = conn.execute(
        "SELECT * FROM submissions WHERE id = ?", (submission["id"],)
    ).fetchone()
    created = False
    if new_status == "approved":
        _, created = award_mission_approval(conn, updated, actor_id=actor.id)
    return updated, created


def score_event_for_source(conn: sqlite3.Connection, submission_id: str) -> sqlite3.Row | None:
    """The *award* event for a submission (never a correction event)."""
    return conn.execute(
        """SELECT * FROM score_events
           WHERE source_type = 'mission_submission' AND source_id = ?
             AND corrects_event_id IS NULL
           ORDER BY created_at LIMIT 1""",
        (submission_id,),
    ).fetchone()


def score_event_detail(conn: sqlite3.Connection, event_id: str) -> sqlite3.Row | None:
    """Score event plus the org/submission context needed for authorization."""
    return conn.execute(
        """SELECT se.*, s.id AS submission_id, s.status AS submission_status,
                  s.user_id AS owner_id, m.organization_id, m.title AS mission_title,
                  u.full_name AS user_name
           FROM score_events se
           LEFT JOIN submissions s ON s.id = se.source_id
           LEFT JOIN missions m ON m.id = s.mission_id
           LEFT JOIN users u ON u.id = se.user_id
           WHERE se.id = ?""",
        (event_id,),
    ).fetchone()


def reversal_for(conn: sqlite3.Connection, event_id: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM score_events WHERE corrects_event_id = ?", (event_id,)
    ).fetchone()


def reverse_score_event(
    conn: sqlite3.Connection, event: sqlite3.Row, actor, reason: str
) -> tuple[sqlite3.Row, bool]:
    """Correct an event with a negative event; maps scoring codes to domain codes."""
    try:
        return reverse_event(conn, event, actor.id, reason)
    except ScoringError as exc:
        code = str(exc)
        messages = {
            "REASON_REQUIRED": "برای اصلاح امتیاز، ثبت دلیل الزامی است.",
            "ALREADY_REVERSED": "این امتیاز قبلاً اصلاح شده است.",
            "CANNOT_REVERSE_CORRECTION": "رویداد اصلاحی خودش قابل اصلاح نیست.",
        }
        raise DomainError(code, messages.get(code, "امکان اصلاح این امتیاز وجود ندارد.")) from exc


# ---------------------------------------------------------------------- wallet / board


def wallet_balance(conn: sqlite3.Connection, user_id: str) -> int:
    row = conn.execute(
        "SELECT balance FROM point_wallets WHERE user_id = ?", (user_id,)
    ).fetchone()
    return int(row["balance"]) if row else 0


def score_history(conn: sqlite3.Connection, user_id: str, limit: int = 30) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT se.*, m.title AS mission_title,
               CASE WHEN se.corrects_event_id IS NULL THEN 'award' ELSE 'correction' END AS kind
        FROM score_events se
        LEFT JOIN submissions s ON s.id = se.source_id
        LEFT JOIN missions m ON m.id = s.mission_id
        WHERE se.user_id = ?
        ORDER BY se.occurred_at DESC
        LIMIT ?
        """,
        (user_id, limit),
    ).fetchall()


def active_competition(conn: sqlite3.Connection, org_id: str) -> sqlite3.Row | None:
    return conn.execute(
        """
        SELECT * FROM competitions
        WHERE organization_id = ? AND starts_at <= ? AND ends_at >= ?
        ORDER BY starts_at DESC LIMIT 1
        """,
        (org_id, now_iso(), now_iso()),
    ).fetchone()


def leaderboard(conn: sqlite3.Connection, user, limit: int = 50) -> tuple[list[dict], int | None]:
    competition = active_competition(conn, user.organization_id)
    start = competition["starts_at"] if competition else "0000-01-01T00:00:00+00:00"
    end = competition["ends_at"] if competition else "9999-12-31T23:59:59+00:00"

    rows = conn.execute(
        """
        SELECT u.id, u.full_name,
               COALESCE(SUM(se.points), 0) AS total,
               MIN(se.occurred_at) AS first_score_at
        FROM users u
        LEFT JOIN score_events se
               ON se.user_id = u.id AND se.occurred_at >= ? AND se.occurred_at <= ?
        WHERE u.organization_id = ? AND u.role = 'visitor' AND u.is_active = 1
        GROUP BY u.id
        ORDER BY total DESC, first_score_at ASC, u.full_name ASC
        LIMIT ?
        """,
        (start, end, user.organization_id, limit),
    ).fetchall()

    board: list[dict] = []
    my_rank: int | None = None
    for index, row in enumerate(rows, start=1):
        item = {
            "rank": index,
            "user_id": row["id"],
            "full_name": row["full_name"],
            "total": int(row["total"]),
            "is_me": row["id"] == user.id,
        }
        if item["is_me"]:
            my_rank = index
        board.append(item)
    return board, my_rank


# ------------------------------------------------------------------------- admin missions


def list_missions_admin(conn: sqlite3.Connection, org_id: str) -> list[sqlite3.Row]:
    return conn.execute(
        """SELECT * FROM missions WHERE organization_id = ?
           ORDER BY CASE status WHEN 'active' THEN 0 WHEN 'draft' THEN 1 ELSE 2 END,
                    starts_at DESC""",
        (org_id,),
    ).fetchall()


def _parse_day(value: str, *, end_of_day: bool = False) -> str:
    try:
        day = date.fromisoformat(value)
    except ValueError as exc:
        raise DomainError("INVALID_DATE", "تاریخ نامعتبر است.") from exc
    moment = datetime(day.year, day.month, day.day, tzinfo=UTC)
    if end_of_day:
        moment = moment + timedelta(days=1) - timedelta(seconds=1)
    return moment.isoformat(timespec="seconds")


def _validate_mission_form(form: dict[str, Any]) -> dict[str, Any]:
    title = str(form.get("title", "")).strip()
    description = str(form.get("description", "")).strip()
    if len(title) < 3:
        raise DomainError("TITLE_REQUIRED", "عنوان مأموریت را کامل کنید.")
    if len(description) < 5:
        raise DomainError("DESCRIPTION_REQUIRED", "توضیحات مأموریت را کامل کنید.")
    try:
        points = int(form.get("points", "0"))
    except (TypeError, ValueError) as exc:
        raise DomainError("INVALID_POINTS", "امتیاز باید عدد باشد.") from exc
    if points < 0 or points > 10_000:
        raise DomainError("INVALID_POINTS", "امتیاز باید بین ۰ و ۱۰٬۰۰۰ باشد.")
    try:
        max_per_user = int(form.get("max_per_user", "1"))
    except (TypeError, ValueError) as exc:
        raise DomainError("INVALID_MAX", "سقف تعداد انجام نامعتبر است.") from exc
    if max_per_user < 1 or max_per_user > 50:
        raise DomainError("INVALID_MAX", "سقف تعداد انجام باید بین ۱ و ۵۰ باشد.")

    starts_at = _parse_day(str(form.get("starts_on", "")))
    ends_at = _parse_day(str(form.get("ends_on", "")), end_of_day=True)
    if ends_at <= starts_at:
        raise DomainError("INVALID_WINDOW", "پایان بازه باید بعد از شروع باشد.")

    return {
        "title": title,
        "description": description,
        "points": points,
        "max_per_user": max_per_user,
        "starts_at": starts_at,
        "ends_at": ends_at,
    }


def create_mission(conn: sqlite3.Connection, org_id: str, form: dict[str, Any], actor) -> str:
    data = _validate_mission_form(form)
    mission_id = _new_id()
    rule_code = f"MISSION_{mission_id[:8].upper()}"
    with conn:
        conn.execute(
            """INSERT INTO missions
               (id, organization_id, title, description, mission_type, points, starts_at,
                ends_at, max_per_user, requires_review, status, rule_code, created_at)
               VALUES (?, ?, ?, ?, 'photo_submission', ?, ?, ?, ?, 1, 'draft', ?, ?)""",
            (mission_id, org_id, data["title"], data["description"], data["points"],
             data["starts_at"], data["ends_at"], data["max_per_user"], rule_code, now_iso()),
        )
        conn.execute(
            """INSERT INTO scoring_rule_versions
               (id, rule_code, version, calculation_type, points, effective_from,
                effective_to, status, is_sample)
               VALUES (?, ?, 1, 'fixed', ?, ?, NULL, 'published', 1)""",
            (_new_id(), rule_code, data["points"], data["starts_at"]),
        )
        audit(conn, actor.id, "mission.created", "mission", mission_id,
              {"points": data["points"], "rule_code": rule_code})
    return mission_id


def update_mission(
    conn: sqlite3.Connection, mission: sqlite3.Row, form: dict[str, Any], actor
) -> bool:
    """Update a mission; a points change publishes a new rule version.

    Returns True when a new rule version was published.
    """
    data = _validate_mission_form(form)
    new_version = False
    with conn:
        if data["points"] != mission["points"]:
            moment = now_iso()
            conn.execute(
                """UPDATE scoring_rule_versions
                   SET status = 'retired', effective_to = ?
                   WHERE rule_code = ? AND status = 'published' AND effective_to IS NULL""",
                (moment, mission["rule_code"]),
            )
            row = conn.execute(
                """SELECT COALESCE(MAX(version), 0) AS v FROM scoring_rule_versions
                   WHERE rule_code = ?""",
                (mission["rule_code"],),
            ).fetchone()
            conn.execute(
                """INSERT INTO scoring_rule_versions
                   (id, rule_code, version, calculation_type, points, effective_from,
                    effective_to, status, is_sample)
                   VALUES (?, ?, ?, 'fixed', ?, ?, NULL, 'published', 1)""",
                (_new_id(), mission["rule_code"], int(row["v"]) + 1, data["points"], moment),
            )
            new_version = True

        conn.execute(
            """UPDATE missions
               SET title = ?, description = ?, points = ?, starts_at = ?, ends_at = ?,
                   max_per_user = ?
               WHERE id = ?""",
            (data["title"], data["description"], data["points"], data["starts_at"],
             data["ends_at"], data["max_per_user"], mission["id"]),
        )
        audit(conn, actor.id, "mission.updated", "mission", mission["id"],
              {"points": data["points"], "new_rule_version": new_version})
    return new_version


def publish_mission(conn: sqlite3.Connection, mission: sqlite3.Row, actor) -> None:
    if mission["status"] != "draft":
        raise DomainError("NOT_DRAFT", "فقط مأموریت پیش‌نویس قابل انتشار است.")
    with conn:
        conn.execute("UPDATE missions SET status = 'active' WHERE id = ?", (mission["id"],))
        audit(conn, actor.id, "mission.published", "mission", mission["id"])


def archive_mission(conn: sqlite3.Connection, mission: sqlite3.Row, actor) -> None:
    with conn:
        conn.execute("UPDATE missions SET status = 'archived' WHERE id = ?", (mission["id"],))
        audit(conn, actor.id, "mission.archived", "mission", mission["id"])


def evidence(conn: sqlite3.Connection, evidence_id: str) -> sqlite3.Row | None:
    return conn.execute(
        """SELECT e.*, s.user_id AS owner_id, m.organization_id
           FROM submission_evidences e
           JOIN submissions s ON s.id = e.submission_id
           JOIN missions m ON m.id = s.mission_id
           WHERE e.id = ?""",
        (evidence_id,),
    ).fetchone()
