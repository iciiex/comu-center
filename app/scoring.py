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
from decimal import ROUND_FLOOR, Decimal


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


def _persist_award(
    conn: sqlite3.Connection,
    *,
    event_id: str,
    user_id: str,
    source_type: str,
    source_id: str,
    rule_code: str,
    rule_version_id: str,
    points: float,
    occurred_at: str,
    key: str,
    explain: dict,
) -> None:
    """Event + ledger + wallet projection + outbox row (caller owns the transaction)."""
    conn.execute(
        """
        INSERT INTO score_events
          (id, user_id, source_type, source_id, rule_code, rule_version_id,
           points, occurred_at, idempotency_key, corrects_event_id, reason,
           explain_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?, ?)
        """,
        (
            event_id,
            user_id,
            source_type,
            source_id,
            rule_code,
            rule_version_id,
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
        (str(uuid.uuid4()), user_id, event_id, points, occurred_at),
    )
    conn.execute(
        """INSERT INTO point_wallets (user_id, balance, updated_at)
           VALUES (?, ?, ?)
           ON CONFLICT(user_id) DO UPDATE
             SET balance = balance + excluded.balance,
                 updated_at = excluded.updated_at""",
        (user_id, points, occurred_at),
    )
    conn.execute(
        """INSERT INTO outbox_events
           (id, event_type, payload_json, created_at, published_at)
           VALUES (?, 'score.posted', ?, ?, NULL)""",
        (
            str(uuid.uuid4()),
            json.dumps(
                {"score_event_id": event_id, "user_id": user_id, "points": points},
                ensure_ascii=False,
            ),
            occurred_at,
        ),
    )


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
            _persist_award(
                conn,
                event_id=event_id,
                user_id=submission["user_id"],
                source_type="mission_submission",
                source_id=submission["id"],
                rule_code=mission["rule_code"],
                rule_version_id=rule["id"],
                points=points,
                occurred_at=occurred_at,
                key=key,
                explain=explain,
            )
    except sqlite3.IntegrityError:
        # Concurrent duplicate: the unique constraint won; return the winner.
        existing = _existing(conn, key)
        if existing is not None:
            return existing, False
        raise

    event = conn.execute("SELECT * FROM score_events WHERE id = ?", (event_id,)).fetchone()
    return event, True


SALES_RULE_CODE = "SALES_AMOUNT_SAMPLE"


def award_sales_record(
    conn: sqlite3.Connection, record: sqlite3.Row, actor_id: str | None = None
) -> tuple[sqlite3.Row | None, bool]:
    """Score one validated sales row.

    SAMPLE formula (OD-04 is OPEN): ``floor(amount / unit_size) * points`` of the
    active ``SALES_AMOUNT_SAMPLE`` rule version. Both numbers live in
    ``scoring_rule_versions``, never in code. Amounts below one unit award zero
    points and write nothing.
    """
    key = f"sales.record:{record['id']}"
    existing = _existing(conn, key)
    if existing is not None:
        return existing, False

    rule = find_rule_version(conn, SALES_RULE_CODE)
    if rule is None:
        raise ScoringError("NO_ACTIVE_RULE_VERSION")

    unit = Decimal(str(rule["unit_size"]))
    if not unit.is_finite() or unit <= 0:
        raise ScoringError("INVALID_UNIT_SIZE")
    amount = Decimal(str(record["amount"] or 0))
    units = int((amount / unit).to_integral_value(rounding=ROUND_FLOOR))
    points = units * int(rule["points"])
    if points <= 0:
        return None, False

    occurred_at = _now()
    explain = {
        "rule_code": SALES_RULE_CODE,
        "rule_version": rule["version"],
        "calculation_type": rule["calculation_type"],
        "conditions": {"event": "sales.record", "unit_size": str(unit)},
        "input": {
            "sales_record_id": record["id"],
            "external_id": record["external_id"],
            "amount": str(amount),
            "sale_date": record["sale_date"],
        },
        "output": {"units": units, "points": points},
        "is_sample": bool(rule["is_sample"]),
    }
    event_id = str(uuid.uuid4())
    _persist_award(
        conn,
        event_id=event_id,
        user_id=record["user_id"],
        source_type="sales_record",
        source_id=record["id"],
        rule_code=SALES_RULE_CODE,
        rule_version_id=rule["id"],
        points=points,
        occurred_at=occurred_at,
        key=key,
        explain=explain,
    )

    event = conn.execute("SELECT * FROM score_events WHERE id = ?", (event_id,)).fetchone()
    return event, True


def reversal_of(conn: sqlite3.Connection, event_id: str) -> sqlite3.Row | None:
    """Return the correction event that reverses ``event_id``, if any."""
    return conn.execute(
        "SELECT * FROM score_events WHERE corrects_event_id = ?", (event_id,)
    ).fetchone()


def reverse_event(
    conn: sqlite3.Connection,
    event: sqlite3.Row,
    actor_id: str | None,
    reason: str,
) -> tuple[sqlite3.Row, bool]:
    """Correct a score event with a new, negative event.

    History is never edited or deleted: the reversal points at the original via
    ``corrects_event_id`` and carries the negative points. Event, ledger entry,
    wallet projection, outbox row and audit row are written in one transaction.

    Raises ``ScoringError`` for: empty reason, reversing a reversal, reversing
    the same event twice.
    """
    if not reason or not reason.strip():
        raise ScoringError("REASON_REQUIRED")
    if event["corrects_event_id"]:
        raise ScoringError("CANNOT_REVERSE_CORRECTION")
    if float(event["points"]) <= 0:
        raise ScoringError("CANNOT_REVERSE_CORRECTION")
    if reversal_of(conn, event["id"]) is not None:
        raise ScoringError("ALREADY_REVERSED")

    key = f"score.reversed:{event['id']}"
    existing = _existing(conn, key)
    if existing is not None:
        raise ScoringError("ALREADY_REVERSED")

    version = conn.execute(
        "SELECT version FROM scoring_rule_versions WHERE id = ?",
        (event["rule_version_id"],),
    ).fetchone()
    points = -abs(float(event["points"]))
    occurred_at = _now()
    explain = {
        "rule_code": event["rule_code"],
        "rule_version": version["version"] if version else None,
        "calculation_type": "correction",
        "conditions": {"event": "score.reversed"},
        "input": {"corrects_event_id": event["id"], "original_points": event["points"]},
        "output": {"points": points},
        "reason": reason.strip(),
        "is_sample": False,
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
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    event["user_id"],
                    event["source_type"],
                    event["source_id"],
                    event["rule_code"],
                    event["rule_version_id"],
                    points,
                    occurred_at,
                    key,
                    event["id"],
                    reason.strip(),
                    json.dumps(explain, ensure_ascii=False),
                    occurred_at,
                ),
            )
            conn.execute(
                """INSERT INTO point_transactions
                   (id, user_id, score_event_id, amount, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (str(uuid.uuid4()), event["user_id"], event_id, points, occurred_at),
            )
            conn.execute(
                """INSERT INTO point_wallets (user_id, balance, updated_at)
                   VALUES (?, ?, ?)
                   ON CONFLICT(user_id) DO UPDATE
                     SET balance = balance + excluded.balance,
                         updated_at = excluded.updated_at""",
                (event["user_id"], points, occurred_at),
            )
            conn.execute(
                """INSERT INTO outbox_events
                   (id, event_type, payload_json, created_at, published_at)
                   VALUES (?, 'score.reversed', ?, ?, NULL)""",
                (
                    str(uuid.uuid4()),
                    json.dumps(
                        {
                            "score_event_id": event_id,
                            "corrects_event_id": event["id"],
                            "user_id": event["user_id"],
                            "points": points,
                        },
                        ensure_ascii=False,
                    ),
                    occurred_at,
                ),
            )
            conn.execute(
                """INSERT INTO audit_logs
                   (id, actor_id, action, entity_type, entity_id, detail_json, created_at)
                   VALUES (?, ?, 'score.reversed', 'score_event', ?, ?, ?)""",
                (
                    str(uuid.uuid4()),
                    actor_id,
                    event_id,
                    json.dumps(
                        {
                            "corrects_event_id": event["id"],
                            "points": points,
                            "reason": reason.strip(),
                        },
                        ensure_ascii=False,
                    ),
                    occurred_at,
                ),
            )
    except sqlite3.IntegrityError as exc:
        # Concurrent duplicate: the unique correction index won the race.
        if reversal_of(conn, event["id"]) is not None:
            raise ScoringError("ALREADY_REVERSED") from exc
        raise

    created = conn.execute("SELECT * FROM score_events WHERE id = ?", (event_id,)).fetchone()
    return created, True
