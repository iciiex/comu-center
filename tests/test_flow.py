"""End-to-end behaviour of the prototype demo path."""

from __future__ import annotations

import sqlite3

from fastapi.testclient import TestClient

from app.config import Settings
from app.seed import PNG_1PX
from tests.conftest import ADMIN, OPERATOR, OTHER_VISITOR, VISITOR, login, row_id

MISSION_ONE = "ثبت تصویر یخچال فروشگاه"
MISSION_TWO = "چیدمان قفسه محصولات هدف"


def submit(client: TestClient, settings: Settings, mission_title: str, request_id: str = "req-1"):
    mission_id = row_id(settings, "SELECT id FROM missions WHERE title = ?", (mission_title,))
    return client.post(
        f"/missions/{mission_id}/submissions",
        data={"request_id": request_id, "note": "نمونه ارسال تست"},
        files={"evidence": ("evidence.png", PNG_1PX, "image/png")},
    )


def test_health_declares_prototype(client: TestClient) -> None:
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["mode"] == "P"
    assert body["demo_data"] is True


def test_login_page_lists_demo_users(client: TestClient) -> None:
    response = client.get("/login")
    assert response.status_code == 200
    assert "ورود به نسخه نمایشی" in response.text
    assert "مدیر سیستم" in response.text


def test_mission_window_and_status_filtering(
    client: TestClient, settings: Settings, db: sqlite3.Connection
) -> None:
    login(client, settings, VISITOR)
    response = client.get("/missions")
    assert response.status_code == 200
    assert MISSION_ONE in response.text
    assert MISSION_TWO in response.text
    assert "کمپین پایان‌یافته" not in response.text  # out of date window (BR-001)
    assert "کمپین زمستان" not in response.text  # draft

    expired_id = row_id(
        settings, "SELECT id FROM missions WHERE title = ?", ("کمپین پایان‌یافته (نمونه)",)
    )
    assert client.get(f"/missions/{expired_id}").status_code == 404


def test_full_flow_approval_scores_once(client: TestClient, settings: Settings) -> None:
    login(client, settings, VISITOR)
    response = submit(client, settings, MISSION_ONE)
    assert response.status_code == 200
    assert "در انتظار بررسی" in response.text

    client.post("/logout")
    login(client, settings, OPERATOR)
    queue = client.get("/admin/submissions")
    assert "سارا محمدی" in queue.text

    submission_id = row_id(
        settings,
        """SELECT s.id FROM submissions s JOIN users u ON u.id = s.user_id
           WHERE u.mobile = ? ORDER BY s.created_at DESC LIMIT 1""",
        (VISITOR,),
    )
    approved = client.post(
        f"/admin/submissions/{submission_id}/review", data={"decision": "approve", "reason": ""}
    )
    assert approved.status_code == 200

    # Second decision is rejected by the state machine — no second score event.
    again = client.post(
        f"/admin/submissions/{submission_id}/review", data={"decision": "approve", "reason": ""}
    )
    assert again.status_code == 409
    assert "قبلاً بررسی شده" in again.text

    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    try:
        events = conn.execute(
            "SELECT * FROM score_events WHERE source_id = ?", (submission_id,)
        ).fetchall()
        assert len(events) == 1
        assert int(events[0]["points"]) == 10
        balance = conn.execute(
            """SELECT w.balance FROM point_wallets w JOIN users u ON u.id = w.user_id
               WHERE u.mobile = ?""",
            (VISITOR,),
        ).fetchone()
        assert int(balance["balance"]) == 10
        outbox = conn.execute("SELECT COUNT(*) FROM outbox_events").fetchone()[0]
        assert outbox >= 2  # seeded + this approval
        audit = conn.execute(
            "SELECT COUNT(*) FROM audit_logs WHERE action = 'submission.approved'"
        ).fetchone()[0]
        assert audit == 1
    finally:
        conn.close()

    client.post("/logout")
    login(client, settings, VISITOR)
    score_page = client.get("/score")
    assert "۱۰" in score_page.text
    assert MISSION_ONE in score_page.text


def test_reject_requires_reason_and_awards_nothing(client: TestClient, settings: Settings) -> None:
    login(client, settings, VISITOR)
    submit(client, settings, MISSION_TWO, request_id="req-reject")
    submission_id = row_id(
        settings,
        "SELECT id FROM submissions WHERE request_id = ?",
        ("req-reject",),
    )

    client.post("/logout")
    login(client, settings, OPERATOR)
    missing_reason = client.post(
        f"/admin/submissions/{submission_id}/review", data={"decision": "reject", "reason": ""}
    )
    assert missing_reason.status_code == 409
    assert "دلیل" in missing_reason.text

    rejected = client.post(
        f"/admin/submissions/{submission_id}/review",
        data={"decision": "reject", "reason": "تصویر شاهد واضح نیست."},
    )
    assert rejected.status_code == 200

    conn = sqlite3.connect(settings.db_path)
    try:
        events = conn.execute(
            "SELECT COUNT(*) FROM score_events WHERE source_id = ?", (submission_id,)
        ).fetchone()[0]
        assert events == 0
    finally:
        conn.close()


def test_visitors_and_operators_have_no_admin_powers(
    client: TestClient, settings: Settings
) -> None:
    login(client, settings, VISITOR)
    assert client.get("/admin/submissions").status_code == 403

    client.post("/logout")
    login(client, settings, OPERATOR)
    assert client.get("/admin/submissions").status_code == 200
    assert client.get("/admin/missions/new").status_code == 403


def test_organization_scope_blocks_foreign_submission(
    client: TestClient, settings: Settings
) -> None:
    other_org = row_id(settings, "SELECT id FROM organizations LIMIT 1", ())
    foreign_submission = row_id(
        settings,
        "SELECT id FROM submissions WHERE user_id = (SELECT id FROM users WHERE mobile = ?)",
        (OTHER_VISITOR,),
    )
    assert other_org  # seeded single org, but the check below must still hold

    login(client, settings, VISITOR)
    response = client.get(f"/submissions/{foreign_submission}")
    assert response.status_code == 403
    assert "مجاز نیست" in response.text


def test_mission_edit_publishes_new_rule_version(
    client: TestClient, settings: Settings, db: sqlite3.Connection
) -> None:
    mission_id = row_id(settings, "SELECT id FROM missions WHERE title = ?", (MISSION_ONE,))

    login(client, settings, ADMIN)
    response = client.post(
        f"/admin/missions/{mission_id}",
        data={
            "title": MISSION_ONE,
            "description": "به‌روزرسانی توضیحات در نسخه آزمایشی.",
            "points": "20",
            "max_per_user": "1",
            "starts_on": "2026-01-01",
            "ends_on": "2027-01-01",
        },
    )
    assert response.status_code == 200
    assert "نسخه جدید قانون امتیاز" in response.text

    versions = db.execute(
        """SELECT version, points, status FROM scoring_rule_versions
           WHERE rule_code = (SELECT rule_code FROM missions WHERE id = ?)
           ORDER BY version""",
        (mission_id,),
    ).fetchall()
    assert [v["version"] for v in versions] == [1, 2]
    assert versions[0]["status"] == "retired"
    assert versions[1]["status"] == "published"
    assert int(versions[1]["points"]) == 20

    # Historical event (seeded, 15 points from mission two) is untouched.
    seeded_event = db.execute(
        "SELECT points, rule_version_id FROM score_events ORDER BY created_at LIMIT 1"
    ).fetchone()
    assert int(seeded_event["points"]) == 15


def test_mission_respects_max_per_user(client: TestClient, settings: Settings) -> None:
    login(client, settings, VISITOR)
    first = submit(client, settings, MISSION_ONE, request_id="req-a")
    assert first.status_code == 200

    second = submit(client, settings, MISSION_ONE, request_id="req-b")
    assert second.status_code == 409
    assert "سقف" in second.text


def test_duplicate_request_id_is_idempotent(client: TestClient, settings: Settings) -> None:
    login(client, settings, VISITOR)
    first = submit(client, settings, MISSION_ONE, request_id="same-request")
    assert first.status_code == 200
    second = submit(client, settings, MISSION_ONE, request_id="same-request")
    assert second.status_code == 200

    conn = sqlite3.connect(settings.db_path)
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM submissions WHERE request_id = 'same-request'"
        ).fetchone()[0]
    finally:
        conn.close()
    assert count == 1


def test_approve_redirect_keeps_queue_filter(client: TestClient, settings: Settings) -> None:
    login(client, settings, VISITOR)
    submit(client, settings, MISSION_ONE, request_id="req-redirect")
    submission_id = row_id(
        settings, "SELECT id FROM submissions WHERE request_id = ?", ("req-redirect",)
    )

    client.post("/logout")
    login(client, settings, OPERATOR)
    response = client.post(
        f"/admin/submissions/{submission_id}/review",
        data={"decision": "approve", "reason": ""},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/admin/submissions?status=submitted&ok=1"
