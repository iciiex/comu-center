"""Scoring engine (prototype implementation of the contract in
`.agent/playbooks/scoring-and-rules.md`).

Guarantees exercised by tests:
  * append-only score events, one source → at most one event per rule version
  * idempotency key + unique constraints
  * event, ledger entry, wallet projection and outbox row in one transaction
  * every event carries an explain payload (rule, version, input, output)
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime


class ScoringError(Exception):
    """Raised when an event cannot be scored for a non-transient reason."""


def _now() -> str:
    return datetime.now(tz=UTC).isoformat(timespec="seconds")


def find_rule_version(
    conn: sqlite3.Connection, rule_code: str, at: str | None = None
) -> sqlite3.Row | None:
    at = at or _now()
    return conn.execute(
        """
        SELECT * FROM scoring_rule_versions
        WHERE rule_code = ?
          AND status = 'published'
          AND effective_from <= ?
          AND (effective_to IS NULL OR effective_to > ?)
        ORDER BY version DESC
        LIMIT 1
        """,
        (rule_code, at, at),
    ).fetchone()


def _existing(conn: sqlite3.Connection, key: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM score_events WHERE idempotency_key = ?", (key,)
    ).fetchone()


def award_mission_approval(
    conn: sqlite3.Connection, submission: sqlite3.Row, actor_id: str | None
) -> tuple[sqlite3.Row, bool]:
    """Create (or return) the score event for an approved submission.

    Returns (event, created). Safe to call twice: the second call returns the
    original event and creates no points.
    """
    key = f"mission.approved:{submission['id']}"
    existing = _existing(conn, key)
    if existing is not None:
        return existing, False

    mission = conn.execute(
        "SELECT * FROM missions WHERE id = ?", (submission["mission_id"],)
    ).fetchone()
    if mission is None:
        raise ScoringError("MISSION_NOT_FOUND")

    rule = find_rule_version(conn, mission["rule_code"])
    if rule is None:
        raise ScoringError("NO_ACTIVE_RULE_VERSION")

    points = rule["points"]
    occurred_at = _now()
    explain = {
        "rule_code": mission["rule_code"],
        "rule_version": rule["version"],
        "calculation_type": rule["calculation_type"],
        "conditions": {"mission_type": mission["mission_type"], "event": "mission.approved"},
        "input": {"submission_id": submission["id"], "mission_id": mission["id"]},
        "output": {"points": points},
        "is_sample": bool(rule["is_sample"]),
    }

    event_id = str(uuid.uuid4())
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO score_events
                  (id, user_id, source_type, source_id, rule_code, rule_version_id,
                   points, occurred_at, idempotency_key, corrects_event_id, reason,
                   explain_json, created_at)
                VALUES (?, ?, 'mission_submission', ?, ?, ?, ?, ?, ?, NULL, NULL, ?, ?)
                """,
                (
                    event_id,
                    submission["user_id"],
                    submission["id"],
                    mission["rule_code"],
                    rule["id"],
                    points,
                    occurred_at,
                    key,
                    json.dumps(explain, ensure_ascii=False),
                    occurred_at,
                ),
            )
            conn.execute(
                """INSERT INTO point_transactions
                   (id, user_id, score_event_id, amount, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (str(uuid.uuid4()), submission["user_id"], event_id, points, occurred_at),
            )
            conn.execute(
                """INSERT INTO point_wallets (user_id, balance, updated_at)
                   VALUES (?, ?, ?)
                   ON CONFLICT(user_id) DO UPDATE
                     SET balance = balance + excluded.balance,
                         updated_at = excluded.updated_at""",
                (submission["user_id"], points, occurred_at),
            )
            conn.execute(
                """INSERT INTO outbox_events
                   (id, event_type, payload_json, created_at, published_at)
                   VALUES (?, 'score.posted', ?, ?, NULL)""",
                (
                    str(uuid.uuid4()),
                    json.dumps(
                        {"score_event_id": event_id, "user_id": submission["user_id"],
                         "points": points},
                        ensure_ascii=False,
                    ),
                    occurred_at,
                ),
            )
    except sqlite3.IntegrityError:
        # Concurrent duplicate: the unique constraint won; return the winner.
        existing = _existing(conn, key)
        if existing is not None:
            return existing, False
        raise

    event = conn.execute("SELECT * FROM score_events WHERE id = ?", (event_id,)).fetchone()
    return event, True
