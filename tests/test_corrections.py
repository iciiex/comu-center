"""Score corrections: reversal events, permissions, and projections."""

from __future__ import annotations

import sqlite3

from fastapi.testclient import TestClient

from app.config import Settings
from app.seed import PNG_1PX
from tests.conftest import ADMIN, OPERATOR, VISITOR, login, post, row_id

MISSION_ONE = "ثبت تصویر یخچال فروشگاه"


def awarded_submission(
    client: TestClient, settings: Settings, request_id: str = "corr-1"
) -> tuple[str, str]:
    """Create a submission, approve it, and return (submission_id, event_id) as admin."""
    login(client, settings, VISITOR)
    mission_id = row_id(settings, "SELECT id FROM missions WHERE title = ?", (MISSION_ONE,))
    post(
        client,
        settings,
        f"/missions/{mission_id}/submissions",
        data={"request_id": request_id, "note": "نمونه برای اصلاح"},
        files={"evidence": ("evidence.png", PNG_1PX, "image/png")},
    )
    submission_id = row_id(
        settings, "SELECT id FROM submissions WHERE request_id = ?", (request_id,)
    )
    post(client, settings, "/logout")

    login(client, settings, OPERATOR)
    post(
        client,
        settings,
        f"/admin/submissions/{submission_id}/review",
        data={"decision": "approve", "reason": ""},
    )
    post(client, settings, "/logout")

    login(client, settings, ADMIN)
    event_id = row_id(
        settings,
        """SELECT id FROM score_events
           WHERE source_id = ? AND corrects_event_id IS NULL""",
        (submission_id,),
    )
    return submission_id, event_id


def test_reversal_creates_negative_event_and_fixes_projections(
    client: TestClient, settings: Settings, db: sqlite3.Connection
) -> None:
    submission_id, event_id = awarded_submission(client, settings)

    page = client.get(f"/submissions/{submission_id}")
    assert "اصلاح امتیاز" in page.text

    response = post(
        client,
        settings,
        f"/admin/score-events/{event_id}/reverse",
        data={"reason": "تصویر تکراری بود و مأموریت دوباره انجام نشده است."},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"].startswith(f"/submissions/{submission_id}?reversed=1")

    events = db.execute(
        "SELECT * FROM score_events WHERE source_id = ? ORDER BY created_at", (submission_id,)
    ).fetchall()
    assert len(events) == 2
    award, correction = events
    assert int(award["points"]) == 10
    assert correction["corrects_event_id"] == event_id
    assert int(correction["points"]) == -10
    assert correction["idempotency_key"] == f"score.reversed:{event_id}"
    assert correction["rule_code"] == award["rule_code"]
    assert correction["rule_version_id"] == award["rule_version_id"]
    assert "تکراری" in correction["reason"]

    ledger = db.execute(
        "SELECT SUM(amount) AS total FROM point_transactions WHERE user_id = ("
        "SELECT id FROM users WHERE mobile = ?)",
        (VISITOR,),
    ).fetchone()
    assert int(ledger["total"]) == 0
    wallet = db.execute(
        "SELECT balance FROM point_wallets WHERE user_id = ("
        "SELECT id FROM users WHERE mobile = ?)",
        (VISITOR,),
    ).fetchone()
    assert int(wallet["balance"]) == 0
    assert (
        db.execute(
            "SELECT COUNT(*) FROM outbox_events WHERE event_type = 'score.reversed'"
        ).fetchone()[0]
        == 1
    )
    assert (
        db.execute(
            "SELECT COUNT(*) FROM audit_logs WHERE action = 'score.reversed'"
        ).fetchone()[0]
        == 1
    )

    after = client.get(f"/submissions/{submission_id}")
    assert "این امتیاز اصلاح شده است" in after.text
    assert f"/admin/score-events/{event_id}/reverse" not in after.text

    post(client, settings, "/logout")
    login(client, settings, VISITOR)
    history = client.get("/score")
    assert "اصلاح" in history.text
    assert "تکراری" in history.text
    assert int(history.text.count("اصلاح")) >= 2


def test_second_reversal_is_rejected(
    client: TestClient, settings: Settings
) -> None:
    _submission_id, event_id = awarded_submission(client, settings, request_id="corr-2")
    first = post(
        client,
        settings,
        f"/admin/score-events/{event_id}/reverse",
        data={"reason": "ثبت اشتباه امتیاز"},
    )
    assert first.status_code == 200  # followed redirect to the submission page

    second = post(
        client,
        settings,
        f"/admin/score-events/{event_id}/reverse",
        data={"reason": "تلاش دوباره"},
    )
    assert second.status_code == 409
    assert "قبلاً اصلاح شده" in second.text


def test_reason_is_required(client: TestClient, settings: Settings) -> None:
    _submission_id, event_id = awarded_submission(client, settings, request_id="corr-3")
    response = post(
        client,
        settings,
        f"/admin/score-events/{event_id}/reverse",
        data={"reason": "   "},
    )
    assert response.status_code == 409
    assert "دلیل" in response.text


def test_only_admin_can_reverse(client: TestClient, settings: Settings) -> None:
    _submission_id, event_id = awarded_submission(client, settings, request_id="corr-4")

    post(client, settings, "/logout")
    login(client, settings, OPERATOR)
    operator = post(
        client,
        settings,
        f"/admin/score-events/{event_id}/reverse",
        data={"reason": "تلاش اپراتور"},
    )
    assert operator.status_code == 403

    post(client, settings, "/logout")
    login(client, settings, VISITOR)
    visitor = post(
        client,
        settings,
        f"/admin/score-events/{event_id}/reverse",
        data={"reason": "تلاش ویزیتور"},
    )
    assert visitor.status_code == 403


def test_reversal_requires_csrf(client: TestClient, settings: Settings) -> None:
    _submission_id, event_id = awarded_submission(client, settings, request_id="corr-5")
    response = client.post(
        f"/admin/score-events/{event_id}/reverse", data={"reason": "بدون csrf"}
    )
    assert response.status_code == 403


def test_a_correction_cannot_be_reversed(
    client: TestClient, settings: Settings, db: sqlite3.Connection
) -> None:
    _submission_id, event_id = awarded_submission(client, settings, request_id="corr-6")
    post(
        client,
        settings,
        f"/admin/score-events/{event_id}/reverse",
        data={"reason": "اصلاح اول"},
    )
    correction_id = db.execute(
        "SELECT id FROM score_events WHERE corrects_event_id = ?", (event_id,)
    ).fetchone()["id"]

    response = post(
        client,
        settings,
        f"/admin/score-events/{correction_id}/reverse",
        data={"reason": "اصلاح معکوس"},
    )
    assert response.status_code == 409
    assert "قابل اصلاح نیست" in response.text


def test_missing_event_returns_404(client: TestClient, settings: Settings) -> None:
    login(client, settings, ADMIN)
    response = post(
        client,
        settings,
        "/admin/score-events/00000000-0000-0000-0000-000000000000/reverse",
        data={"reason": "ناموجود"},
    )
    assert response.status_code == 404


def test_other_organization_event_is_forbidden(
    client: TestClient, settings: Settings, db: sqlite3.Connection
) -> None:
    _submission_id, event_id = awarded_submission(client, settings, request_id="corr-7")
    db.execute(
        "INSERT INTO organizations (id, name, created_at) VALUES (?, ?, ?)",
        ("other-org", "سازمان دیگر", "2026-01-01T00:00:00+00:00"),
    )
    db.execute(
        """UPDATE missions SET organization_id = 'other-org'
           WHERE id = (SELECT mission_id FROM submissions
                       WHERE id = (SELECT source_id FROM score_events WHERE id = ?))""",
        (event_id,),
    )
    db.commit()

    response = post(
        client,
        settings,
        f"/admin/score-events/{event_id}/reverse",
        data={"reason": "خارج از سازمان"},
    )
    assert response.status_code == 403


def test_leaderboard_reflects_the_correction(
    client: TestClient, settings: Settings, db: sqlite3.Connection
) -> None:
    _submission_id, event_id = awarded_submission(client, settings, request_id="corr-8")
    before = db.execute(
        """SELECT COALESCE(SUM(points), 0) AS total FROM score_events
           WHERE user_id = (SELECT id FROM users WHERE mobile = ?)""",
        (VISITOR,),
    ).fetchone()["total"]
    assert int(before) == 10

    post(
        client,
        settings,
        f"/admin/score-events/{event_id}/reverse",
        data={"reason": "اصلاح برای لیدربورد"},
    )
    after = db.execute(
        """SELECT COALESCE(SUM(points), 0) AS total FROM score_events
           WHERE user_id = (SELECT id FROM users WHERE mobile = ?)""",
        (VISITOR,),
    ).fetchone()["total"]
    assert int(after) == 0

    board = client.get("/leaderboard")
    assert board.status_code == 200
    assert "امتیاز منفی" not in board.text  # negative totals are shown, not hidden
