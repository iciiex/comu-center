"""Scoring-engine invariants, independent of HTTP."""

from __future__ import annotations

import sqlite3

from app.config import Settings
from app.scoring import award_mission_approval, find_rule_version


def test_seeded_approval_created_one_event(db: sqlite3.Connection) -> None:
    events = db.execute("SELECT * FROM score_events").fetchall()
    assert len(events) == 1
    assert int(events[0]["points"]) == 15
    assert events[0]["idempotency_key"].startswith("mission.approved:")


def test_award_is_idempotent(db: sqlite3.Connection) -> None:
    submission = db.execute(
        "SELECT * FROM submissions WHERE status = 'approved' LIMIT 1"
    ).fetchone()
    first, created_first = award_mission_approval(db, submission, actor_id=None)
    second, created_second = award_mission_approval(db, submission, actor_id=None)

    assert created_first is False  # seed already scored it
    assert created_second is False
    assert first["id"] == second["id"]
    assert db.execute("SELECT COUNT(*) FROM score_events").fetchone()[0] == 1


def test_event_has_traceable_explain(db: sqlite3.Connection) -> None:
    event = db.execute("SELECT * FROM score_events LIMIT 1").fetchone()
    explain = event["explain_json"]
    assert '"rule_code"' in explain
    assert '"rule_version"' in explain
    assert '"is_sample": true' in explain


def test_wallet_matches_ledger(db: sqlite3.Connection) -> None:
    ledger_total = db.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM point_transactions"
    ).fetchone()[0]
    wallet_total = db.execute(
        "SELECT COALESCE(SUM(balance), 0) FROM point_wallets"
    ).fetchone()[0]
    assert int(ledger_total) == int(wallet_total) == 15


def test_active_rule_version_selection_after_retirement(
    db: sqlite3.Connection, settings: Settings
) -> None:
    import uuid

    rule_code = "TEST_RULE"
    db.execute(
        """INSERT INTO scoring_rule_versions
           (id, rule_code, version, calculation_type, points, effective_from,
            effective_to, status, is_sample)
           VALUES (?, ?, 1, 'fixed', 5, '2020-01-01T00:00:00+00:00',
                   '2026-01-01T00:00:00+00:00', 'retired', 1)""",
        (str(uuid.uuid4()), rule_code),
    )
    db.execute(
        """INSERT INTO scoring_rule_versions
           (id, rule_code, version, calculation_type, points, effective_from,
            effective_to, status, is_sample)
           VALUES (?, ?, 2, 'fixed', 25, '2026-01-01T00:00:00+00:00',
                   NULL, 'published', 1)""",
        (str(uuid.uuid4()), rule_code),
    )
    db.commit()

    active = find_rule_version(db, rule_code, "2026-11-09T10:00:00+00:00")
    assert active is not None
    assert active["version"] == 2
    assert int(active["points"]) == 25
