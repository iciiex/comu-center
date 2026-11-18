"""DB-backed missions for the Sales Quest Arena (API v2, D-009 PROPOSED).

The ``missions`` table is the single source of truth. This module maps a mission row plus the
visitor's own submissions into the game's ``Mission``/``MissionView`` shape, validates and stores
submissions through ``repo.create_submission`` (same review queue as the web flow) and keeps the
v2 draft/projection helpers. Rewards are granted by ``game_rewards`` at approval, never here.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from typing import Any

from app import db, game, repo
from app.game import GameError
from app.scoring import ScoringError

ANSWER_MAX = 1000
ANSWER_MIN = 2
EXPIRED_VISIBLE_DAYS = 30
# Catalog achievements that cannot be earned from DB missions (daily challenge / six-mission set).
UNAVAILABLE_ACHIEVEMENTS = {"daily_hero", "trailblazer"}


def _check_key(key: str) -> None:
    if not key or len(key) > 128:
        raise GameError(
            400, "IDEMPOTENCY_KEY_REQUIRED", "A valid Idempotency-Key header is required."
        )
    if any(ord(char) < 33 or ord(char) > 126 for char in key):
        raise GameError(
            400,
            "INVALID_IDEMPOTENCY_KEY",
            "Idempotency-Key must contain printable ASCII characters.",
        )


# ---------------------------------------------------------------------------- views


def _steps(row: sqlite3.Row) -> list[dict[str, Any]]:
    return [
        {
            "id": "answer",
            "type": "note",
            "label": "پاسخ شما",
            "question": "پاسخ یا گزارش خود را بنویسید",
            "helper": "پاسخ کوتاه و دقیق بنویسید.",
            "placeholder": "اینجا بنویسید…",
            "maxLength": ANSWER_MAX,
            "suggestions": [],
        },
        {
            "id": "evidence",
            "type": "evidence",
            "label": "تصویر شاهد",
            "question": "تصویر شاهد را ارسال کنید",
            "helper": "JPG، PNG یا WEBP — حداکثر ۴ مگابایت",
            "required": bool(row["requires_evidence"]),
        },
    ]


def _required_steps(row: sqlite3.Row) -> list[str]:
    return ["evidence"] if row["requires_evidence"] else ["answer"]


def _status(
    row: sqlite3.Row, subs: list[sqlite3.Row], draft: Any, now: str, remaining: int
) -> tuple[str, str | None]:
    """Return (status, blocked_reason). blocked_reason is set when the visitor cannot start."""
    latest = subs[0] if subs else None
    if any(s["status"] == "submitted" for s in subs):
        return "pending_review", "pending_review"
    expired = row["ends_at"] < now
    if latest and latest["status"] == "approved" and remaining <= 0:
        return "approved", "limit_reached"
    if expired:
        return "expired", "expired"
    blocked = "limit_reached" if remaining <= 0 else None
    if draft:
        return "in_progress", blocked
    if latest and latest["status"] == "approved":
        return "approved", blocked
    if latest and latest["status"] == "rejected":
        return "rejected", blocked
    return "available", blocked


def _view(
    row: sqlite3.Row, order: int, subs: list[sqlite3.Row], draft: Any, now: str
) -> dict[str, Any]:
    remaining = max(0, int(row["max_per_user"]) - len(subs))
    status, blocked = _status(row, subs, draft, now, remaining)
    steps = _steps(row)
    latest = subs[0] if subs else None
    title = row["title"]
    return {
        "id": row["id"],
        "order": order,
        "title": title,
        "shortTitle": title if len(title) <= 28 else title[:27] + "…",
        "description": row["description"],
        "instructions": row["instructions"] or "",
        "category": row["category"],
        "difficulty": row["difficulty"],
        "estimatedMinutes": int(row["estimated_minutes"]),
        "xpReward": int(row["game_xp"]),
        "coinReward": int(row["game_coins"]),
        "orgPoints": int(row["points"]),
        "requiresReview": bool(row["requires_review"]),
        "requiresEvidence": bool(row["requires_evidence"]),
        "maxPerUser": int(row["max_per_user"]),
        "remaining": remaining,
        "startsAt": row["starts_at"],
        "endsAt": row["ends_at"],
        "source": "server",
        "unlock": {},
        "completion": {"requiredSteps": _required_steps(row)},
        "steps": steps,
        "status": status,
        "canStart": blocked is None,
        "blockedReason": blocked,
        "completions": sum(1 for s in subs if s["status"] == "approved"),
        "bestRating": None,
        "lockReason": None,
        "draftProgress": (
            min(1, int(draft.get("stepIndex", 0)) / len(steps)) if draft else 0
        ),
        "isDaily": False,
        "dailyDone": False,
        "latestSubmission": (
            {
                "id": latest["id"],
                "status": latest["status"],
                "rejectionReason": latest["rejection_reason"],
                "submittedAt": latest["created_at"],
                "reviewedAt": latest["reviewed_at"],
            }
            if latest
            else None
        ),
    }


def _user_submissions(conn: sqlite3.Connection, user_id: str) -> dict[str, list[sqlite3.Row]]:
    grouped: dict[str, list[sqlite3.Row]] = {}
    rows = conn.execute(
        """SELECT id, mission_id, status, rejection_reason, created_at, reviewed_at, note
           FROM submissions WHERE user_id = ? ORDER BY created_at DESC, rowid DESC""",
        (user_id,),
    ).fetchall()
    for row in rows:
        grouped.setdefault(row["mission_id"], []).append(row)
    return grouped


def build_views(conn: sqlite3.Connection, user, progress: dict[str, Any]) -> list[dict[str, Any]]:
    now = db.now_iso()
    cutoff = (datetime.now(UTC) - timedelta(days=EXPIRED_VISIBLE_DAYS)).isoformat(
        timespec="seconds"
    )
    rows = conn.execute(
        """SELECT * FROM missions
           WHERE organization_id = ? AND status = 'active' AND starts_at <= ? AND ends_at >= ?
           ORDER BY ends_at ASC, title ASC""",
        (user.organization_id, now, cutoff),
    ).fetchall()
    subs = _user_submissions(conn, user.id)
    drafts = progress.get("drafts", {})
    return [
        _view(row, index + 1, subs.get(row["id"], []), drafts.get(row["id"]), now)
        for index, row in enumerate(rows)
    ]


def _visible_row(conn: sqlite3.Connection, user, mission_id: str) -> sqlite3.Row:
    row = conn.execute(
        """SELECT * FROM missions
           WHERE id = ? AND organization_id = ? AND status = 'active' AND starts_at <= ?""",
        (mission_id, user.organization_id, db.now_iso()),
    ).fetchone()
    if row is None:
        raise GameError(404, "MISSION_NOT_FOUND", "Mission was not found.")
    return row


def get_mission(conn: sqlite3.Connection, user, mission_id: str) -> dict[str, Any]:
    row = _visible_row(conn, user, mission_id)
    progress = game._initialize(conn, user.id, user.full_name)
    subs = _user_submissions(conn, user.id).get(row["id"], [])
    return _view(row, 1, subs, progress.get("drafts", {}).get(row["id"]), db.now_iso())


def projection(conn: sqlite3.Connection, user, progress: dict[str, Any]) -> dict[str, Any]:
    day_key = game._day_key(game._now())
    public = game._public_progress(progress)
    public["daily"] = None  # v2 has no daily challenge: nothing to render or promise
    return {
        "date_key": day_key,
        "progress": public,
        "missions": build_views(conn, user, progress),
        "special_missions": game._special_mission_views(progress, day_key),
    }


def bootstrap_v2(conn: sqlite3.Connection, user, csrf_value: str) -> dict[str, Any]:
    progress = game._initialize(conn, user.id, user.full_name)
    now = game._now()
    result = projection(conn, user, progress)
    result.update(
        {
            "api_version": "2",
            "content_version": game.catalog()["content_version"],
            "server_time": now.isoformat(),
            "csrf_token": csrf_value,
            "player": {"id": user.id, "account_name": user.full_name, "role": user.role},
            "game_config": game.catalog()["game_config"],
            "categories": game.catalog()["categories"],
            "difficulty": game.catalog()["difficulty"],
            "store": {
                "version": game.store_catalog()["version"],
                "is_demo": True,
                "currency": "game_coins",
            },
            "achievements_catalog": [
                {**a, "available": a["id"] not in UNAVAILABLE_ACHIEVEMENTS}
                for a in game.catalog()["achievements"]
            ],
        }
    )
    return result


def get_progress_v2(conn: sqlite3.Connection, user) -> dict[str, Any]:
    return projection(conn, user, game._initialize(conn, user.id, user.full_name))


def list_submissions(conn: sqlite3.Connection, user) -> dict[str, Any]:
    rows = conn.execute(
        """SELECT s.id, s.mission_id, s.status, s.rejection_reason, s.created_at, s.reviewed_at,
                  m.title
           FROM submissions s JOIN missions m ON m.id = s.mission_id
           WHERE s.user_id = ? AND s.source = 'game'
           ORDER BY s.created_at DESC, s.rowid DESC LIMIT 100""",
        (user.id,),
    ).fetchall()
    return {
        "items": [
            {
                "id": r["id"],
                "missionId": r["mission_id"],
                "missionTitle": r["title"],
                "status": r["status"],
                "rejectionReason": r["rejection_reason"],
                "submittedAt": r["created_at"],
                "reviewedAt": r["reviewed_at"],
            }
            for r in rows
        ]
    }


# ---------------------------------------------------------------------------- drafts


def save_draft(conn: sqlite3.Connection, user, mission_id: str, payload: Any) -> dict[str, Any]:
    row = _visible_row(conn, user, mission_id)
    steps = _steps(row)
    if not isinstance(payload, dict) or set(payload) - {"step_index", "answers"}:
        raise GameError(422, "INVALID_DRAFT", "Draft accepts only step_index and answers.")
    step_index = payload.get("step_index")
    if (
        isinstance(step_index, bool)
        or not isinstance(step_index, int)
        or not 0 <= step_index < len(steps)
    ):
        raise GameError(422, "INVALID_DRAFT", "step_index is outside the mission.")
    raw = payload.get("answers", {})
    if not isinstance(raw, dict):
        raise GameError(422, "INVALID_ANSWERS", "Answers must be a JSON object.")
    if set(raw) - {"answer"}:  # an image cannot live in a draft; it is sent at submission
        raise GameError(
            422, "UNKNOWN_ANSWER", "One or more answer fields are not part of this mission."
        )
    answers: dict[str, Any] = {}
    if "answer" in raw:
        if not isinstance(raw["answer"], str):
            raise GameError(422, "INVALID_ANSWER", "Answer must be text.")
        text = raw["answer"].strip()
        if len(text) > ANSWER_MAX:
            raise GameError(422, "INVALID_ANSWER", "Answer is too long.")
        if text:
            answers["answer"] = text
    now = db.now_iso()
    subs = _user_submissions(conn, user.id).get(mission_id, [])
    remaining = max(0, int(row["max_per_user"]) - len(subs))
    _, blocked = _status(row, subs, None, now, remaining)
    if blocked:
        raise GameError(409, "MISSION_NOT_STARTABLE", "This mission cannot be started now.")
    progress = game._initialize(conn, user.id, user.full_name)
    draft = progress.setdefault("drafts", {}).get(mission_id)
    progress["drafts"][mission_id] = {
        "missionId": mission_id,
        "stepIndex": step_index,
        "answers": answers,
        "startedAt": draft.get("startedAt") if draft else game._now().isoformat(),
    }
    game._save(conn, user.id, progress)
    return projection(conn, user, progress)


def discard_draft(conn: sqlite3.Connection, user, mission_id: str) -> dict[str, Any]:
    _visible_row(conn, user, mission_id)
    progress = game._initialize(conn, user.id, user.full_name)
    progress.setdefault("drafts", {}).pop(mission_id, None)
    game._save(conn, user.id, progress)
    return projection(conn, user, progress)


# ------------------------------------------------------------------------- submission


def _response(conn: sqlite3.Connection, user, submission: sqlite3.Row) -> dict[str, Any]:
    progress = game._initialize(conn, user.id, user.full_name)
    result = projection(conn, user, progress)
    mission = next((m for m in result["missions"] if m["id"] == submission["mission_id"]), None)
    result.update(
        {
            "submission": {
                "id": submission["id"],
                "missionId": submission["mission_id"],
                "status": submission["status"],
                "submittedAt": submission["created_at"],
            },
            "mission": mission,
        }
    )
    return result


def submit(
    conn: sqlite3.Connection,
    user,
    mission_id: str,
    answer: str,
    evidence: dict[str, Any] | None,
    key: str,
) -> tuple[dict[str, Any], bool]:
    """Create a game submission once per Idempotency-Key. Returns (response, replayed)."""
    _check_key(key)
    text = (answer or "").strip()
    if len(text) > ANSWER_MAX:
        raise GameError(422, "INVALID_ANSWER", "Answer is too long.")
    if conn.in_transaction:
        conn.commit()
    conn.execute("BEGIN IMMEDIATE")
    try:
        existing = conn.execute(
            "SELECT * FROM submissions WHERE user_id = ? AND request_id = ?", (user.id, key)
        ).fetchone()
        if existing:
            stored = conn.execute(
                "SELECT sha256 FROM submission_evidences WHERE submission_id = ?",
                (existing["id"],),
            ).fetchone()
            same = (
                existing["mission_id"] == mission_id
                and (existing["note"] or "") == text
                and (stored["sha256"] if stored else None)
                == (evidence["sha256"] if evidence else None)
            )
            if not same:
                raise GameError(
                    409,
                    "IDEMPOTENCY_KEY_REUSED",
                    "Idempotency-Key was already used with a different request.",
                )
            response = _response(conn, user, existing)
            conn.commit()
            return response, True

        row = _visible_row(conn, user, mission_id)
        if row["ends_at"] < db.now_iso():
            raise GameError(409, "MISSION_EXPIRED", "This mission has expired.")
        subs = _user_submissions(conn, user.id).get(mission_id, [])
        if any(s["status"] == "submitted" for s in subs):
            raise GameError(
                409, "SUBMISSION_PENDING", "A previous submission is still awaiting review."
            )
        if len(subs) >= int(row["max_per_user"]):
            raise GameError(409, "MAX_ATTEMPTS_REACHED", "The completion limit was reached.")
        if row["requires_evidence"] and evidence is None:
            raise GameError(422, "EVIDENCE_REQUIRED", "An evidence image is required.")
        if not row["requires_evidence"] and len(text) < ANSWER_MIN:
            raise GameError(422, "ANSWER_REQUIRED", "A text answer is required.")

        try:
            submission, _ = repo.create_submission(
                conn, row, user, request_id=key, note=text, evidence=evidence, source="game"
            )
        except repo.DomainError as exc:
            status = 409 if exc.code == "MAX_ATTEMPTS_REACHED" else 422
            raise GameError(status, exc.code, exc.message) from exc
        except ScoringError as exc:
            raise GameError(409, str(exc), "Scoring is not available for this mission.") from exc

        progress = game._initialize(conn, user.id, user.full_name)
        if progress.get("drafts", {}).pop(mission_id, None) is not None:
            game._save(conn, user.id, progress)
        response = _response(conn, user, submission)
        conn.commit()
        return response, False
    except Exception:
        conn.rollback()
        raise
