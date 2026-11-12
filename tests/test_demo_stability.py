"""Regression tests for the MS-01 demo stability slice (A1, A2, A4, A6).

These tests replay the documented demo path and the defects that were reproduced
by hand on 2026-11-11. They intentionally assert on persistence, not only HTML.
"""

from __future__ import annotations

import io
import re
import sqlite3
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from openpyxl import load_workbook

from app.config import Settings
from app.sample_sales import sample_workbook_bytes
from tests.conftest import ADMIN, OPERATOR, OTHER_VISITOR, VISITOR, login, post, row_id
from tests.test_flow import MISSION_ONE, submit
from tests.test_sales import upload


def _day(offset: int) -> str:
    return (datetime.now(tz=UTC) + timedelta(days=offset)).date().isoformat()


def _mission_form(title: str, starts_on: str, ends_on: str, points: int = 10) -> dict:
    return {
        "title": title,
        "description": "مأموریت بازتولید نقص A1 در مسیر دمو.",
        "points": str(points),
        "max_per_user": "1",
        "starts_on": starts_on,
        "ends_on": ends_on,
    }


def test_approval_rolls_back_when_no_rule_version_is_effective(
    client: TestClient, settings: Settings, db: sqlite3.Connection
) -> None:
    login(client, settings, VISITOR)
    assert submit(client, settings, MISSION_ONE, request_id="a1-no-rule").status_code == 200
    submission_id = row_id(
        settings, "SELECT id FROM submissions WHERE request_id = ?", ("a1-no-rule",)
    )
    rule_code = row_id(
        settings,
        "SELECT m.rule_code FROM missions m JOIN submissions s ON s.mission_id = m.id "
        "WHERE s.id = ?",
        (submission_id,),
    )
    # Simulate the configuration error that used to leave `approved` without a score.
    db.execute(
        "UPDATE scoring_rule_versions SET status = 'retired' WHERE rule_code = ?",
        (rule_code,),
    )
    db.commit()

    post(client, settings, "/logout")
    login(client, settings, OPERATOR)
    response = post(
        client,
        settings,
        f"/admin/submissions/{submission_id}/review",
        data={"decision": "approve", "reason": ""},
    )
    assert response.status_code == 409
    assert "قانون امتیاز فعالی" in response.text
    assert "تأیید انجام نشد" in response.text

    row = db.execute("SELECT * FROM submissions WHERE id = ?", (submission_id,)).fetchone()
    assert row["status"] == "submitted"
    assert row["reviewed_at"] is None
    assert row["reviewed_by"] is None
    assert db.execute(
        "SELECT COUNT(*) FROM score_events WHERE source_id = ?", (submission_id,)
    ).fetchone()[0] == 0
    assert db.execute(
        "SELECT COUNT(*) FROM audit_logs WHERE action = 'submission.approved' "
        "AND entity_id = ?",
        (submission_id,),
    ).fetchone()[0] == 0
    assert db.execute(
        "SELECT COUNT(*) FROM point_transactions pt "
        "JOIN score_events se ON se.id = pt.score_event_id WHERE se.source_id = ?",
        (submission_id,),
    ).fetchone()[0] == 0


def test_moving_future_start_back_keeps_approval_and_score_atomic(
    client: TestClient, settings: Settings, db: sqlite3.Connection
) -> None:
    title = "مأموریت تاریخ آینده (بازتولید A1)"
    login(client, settings, ADMIN)
    created = post(
        client,
        settings,
        "/admin/missions/new",
        data=_mission_form(title, _day(5), _day(12)),
    )
    assert created.status_code == 200
    mission_id = row_id(settings, "SELECT id FROM missions WHERE title = ?", (title,))
    assert post(
        client, settings, f"/admin/missions/{mission_id}/publish"
    ).status_code == 200

    moved = post(
        client,
        settings,
        f"/admin/missions/{mission_id}",
        data=_mission_form(title, _day(-1), _day(12)),
    )
    assert moved.status_code == 200
    rule_code = row_id(settings, "SELECT rule_code FROM missions WHERE id = ?", (mission_id,))
    active_rule = db.execute(
        "SELECT * FROM scoring_rule_versions WHERE rule_code = ? AND status = 'published' "
        "AND effective_from <= ? ORDER BY version DESC LIMIT 1",
        (rule_code, datetime.now(tz=UTC).isoformat(timespec="seconds")),
    ).fetchone()
    assert active_rule is not None
    assert int(active_rule["points"]) == 10

    post(client, settings, "/logout")
    login(client, settings, VISITOR)
    assert submit(client, settings, title, request_id="a1-moved").status_code == 200
    submission_id = row_id(
        settings, "SELECT id FROM submissions WHERE request_id = ?", ("a1-moved",)
    )
    post(client, settings, "/logout")
    login(client, settings, OPERATOR)
    approved = post(
        client,
        settings,
        f"/admin/submissions/{submission_id}/review",
        data={"decision": "approve", "reason": ""},
    )
    assert approved.status_code == 200

    assert db.execute(
        "SELECT status FROM submissions WHERE id = ?", (submission_id,)
    ).fetchone()[0] == "approved"
    events = db.execute(
        "SELECT * FROM score_events WHERE source_id = ?", (submission_id,)
    ).fetchall()
    assert len(events) == 1
    assert int(events[0]["points"]) == 10
    assert db.execute(
        "SELECT COUNT(*) FROM audit_logs WHERE action = 'submission.approved' "
        "AND entity_id = ?",
        (submission_id,),
    ).fetchone()[0] == 1
    wallet = db.execute(
        "SELECT balance FROM point_wallets WHERE user_id = (SELECT id FROM users WHERE mobile = ?)",
        (VISITOR,),
    ).fetchone()
    assert int(wallet["balance"]) == 10


def test_publish_after_moving_draft_start_back_has_an_effective_rule(
    client: TestClient, settings: Settings, db: sqlite3.Connection
) -> None:
    title = "مأموریت پیش‌نویس تاریخ آینده (A1)"
    login(client, settings, ADMIN)
    assert post(
        client,
        settings,
        "/admin/missions/new",
        data=_mission_form(title, _day(5), _day(12)),
    ).status_code == 200
    mission_id = row_id(settings, "SELECT id FROM missions WHERE title = ?", (title,))
    assert post(
        client,
        settings,
        f"/admin/missions/{mission_id}",
        data=_mission_form(title, _day(-1), _day(12)),
    ).status_code == 200
    assert post(
        client, settings, f"/admin/missions/{mission_id}/publish"
    ).status_code == 200

    post(client, settings, "/logout")
    login(client, settings, VISITOR)
    assert submit(client, settings, title, request_id="a1-draft").status_code == 200
    submission_id = row_id(
        settings, "SELECT id FROM submissions WHERE request_id = ?", ("a1-draft",)
    )
    post(client, settings, "/logout")
    login(client, settings, OPERATOR)
    assert post(
        client,
        settings,
        f"/admin/submissions/{submission_id}/review",
        data={"decision": "approve", "reason": ""},
    ).status_code == 200
    assert db.execute(
        "SELECT COUNT(*) FROM score_events WHERE source_id = ?", (submission_id,)
    ).fetchone()[0] == 1


def test_operator_navigation_hides_sales_import_link(
    client: TestClient, settings: Settings
) -> None:
    login(client, settings, OPERATOR)
    operator_page = client.get("/admin/submissions")
    assert operator_page.status_code == 200
    assert 'href="/admin/sales"' not in operator_page.text
    assert client.get("/admin/sales").status_code == 403

    post(client, settings, "/logout")
    login(client, settings, ADMIN)
    admin_page = client.get("/admin/submissions")
    assert admin_page.status_code == 200
    assert 'href="/admin/sales"' in admin_page.text


def test_submission_badge_shows_recorded_points_after_mission_points_change(
    client: TestClient, settings: Settings
) -> None:
    login(client, settings, VISITOR)
    assert submit(client, settings, MISSION_ONE, request_id="a6-badge").status_code == 200
    submission_id = row_id(
        settings, "SELECT id FROM submissions WHERE request_id = ?", ("a6-badge",)
    )
    post(client, settings, "/logout")
    login(client, settings, OPERATOR)
    assert post(
        client,
        settings,
        f"/admin/submissions/{submission_id}/review",
        data={"decision": "approve", "reason": ""},
    ).status_code == 200

    mission_id = row_id(settings, "SELECT id FROM missions WHERE title = ?", (MISSION_ONE,))
    post(client, settings, "/logout")
    login(client, settings, ADMIN)
    assert post(
        client,
        settings,
        f"/admin/missions/{mission_id}",
        data={
            "title": MISSION_ONE,
            "description": "توضیح مأموریت پس از تغییر امتیاز.",
            "points": "15",
            "max_per_user": "1",
            "starts_on": _day(-2),
            "ends_on": _day(30),
        },
    ).status_code == 200

    review = client.get(f"/admin/submissions/{submission_id}")
    assert review.status_code == 200
    assert "۱۰ امتیاز ثبت‌شده" in review.text
    assert "۱۵ امتیاز ثبت‌شده" not in review.text

    post(client, settings, "/logout")
    login(client, settings, VISITOR)
    detail = client.get(f"/submissions/{submission_id}")
    assert detail.status_code == 200
    assert "۱۰ امتیاز ثبت‌شده" in detail.text
    assert "۱۵ امتیاز ثبت‌شده" not in detail.text


def test_sales_list_uses_pending_valid_count_after_zero_point_processing(
    client: TestClient, settings: Settings
) -> None:
    login(client, settings, ADMIN)
    detail = upload(
        client,
        settings,
        sample_workbook_bytes(),
        filename="sales-sample.xlsx",
    )
    assert detail.status_code == 200
    import_id = re.search(r"/admin/sales/([0-9a-f-]{36})/process", detail.text)
    assert import_id is not None
    processed = post(
        client, settings, f"/admin/sales/{import_id.group(1)}/process"
    )
    assert processed.status_code == 200
    assert "تکراری نمی‌سازد" in processed.text
    assert "تکرارینمی" not in processed.text

    listing = client.get("/admin/sales")
    assert listing.status_code == 200
    text = re.sub(r"\s+", " ", listing.text)
    assert "۶ کل · ۰ معتبر" in text
    assert "۴ معتبر" not in text


def test_sales_list_counts_sub_unit_row_as_not_pending_after_processing(
    client: TestClient, settings: Settings
) -> None:
    from tests.test_sales import MAPPED_USER, workbook_bytes

    login(client, settings, ADMIN)
    detail = upload(
        client,
        settings,
        workbook_bytes([["A6-SUB", MAPPED_USER, _day(-1), "SKU-1", 1, 500_000]]),
    )
    assert detail.status_code == 200
    import_id = re.search(r"/admin/sales/([0-9a-f-]{36})/process", detail.text)
    assert import_id is not None
    assert post(
        client, settings, f"/admin/sales/{import_id.group(1)}/process"
    ).status_code == 200
    listing = client.get("/admin/sales")
    text = re.sub(r"\s+", " ", listing.text)
    assert "۱ کل · ۰ معتبر" in text
    assert "۱ معتبر" not in text


def test_sample_sales_workbook_download_is_admin_only(
    client: TestClient, settings: Settings
) -> None:
    anonymous = client.get("/admin/sales/sample", follow_redirects=False)
    assert anonymous.status_code == 303
    assert anonymous.headers["location"] == "/login"

    login(client, settings, VISITOR)
    assert client.get("/admin/sales/sample").status_code == 403
    post(client, settings, "/logout")
    login(client, settings, OPERATOR)
    assert client.get("/admin/sales/sample").status_code == 403
    post(client, settings, "/logout")
    login(client, settings, ADMIN)
    page = client.get("/admin/sales/new")
    assert 'href="/admin/sales/sample"' in page.text
    response = client.get("/admin/sales/sample")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert "sales-sample.xlsx" in response.headers["content-disposition"]
    sheet = load_workbook(io.BytesIO(response.content), read_only=True).active
    rows = list(sheet.iter_rows(values_only=True))
    assert len(rows) == 7
    assert rows[1][0] == "S-1001"


def test_demo_script_main_path_and_optional_correction(
    client: TestClient, settings: Settings, db: sqlite3.Connection
) -> None:
    """Replay docs/delivery/demo-script.md §3 and the optional correction (§4)."""
    # پرده ۱ — سارا مأموریت را ارسال می‌کند.
    login(client, settings, VISITOR)
    home = client.get("/home")
    assert "۰" in home.text
    assert "رتبه در دوره: <b>۲</b>" in home.text
    assert "مأموریت فعال: <b>۲</b>" in home.text
    assert submit(client, settings, MISSION_ONE, request_id="demo-sara").status_code == 200
    submission_id = row_id(
        settings, "SELECT id FROM submissions WHERE request_id = ?", ("demo-sara",)
    )
    assert "در انتظار بررسی" in client.get(f"/submissions/{submission_id}").text

    # پرده ۲ — حسین تأیید می‌کند.
    post(client, settings, "/logout")
    login(client, settings, OPERATOR)
    assert "سارا محمدی" in client.get("/admin/submissions").text
    assert post(
        client,
        settings,
        f"/admin/submissions/{submission_id}/review",
        data={"decision": "approve", "reason": ""},
    ).status_code == 200

    # پرده ۳ — سارا امتیاز قابل توضیح را می‌بیند.
    post(client, settings, "/logout")
    login(client, settings, VISITOR)
    assert "۱۰" in client.get("/home").text
    mission_id = row_id(settings, "SELECT id FROM missions WHERE title = ?", (MISSION_ONE,))
    assert "مشاهده جزئیات" in client.get(f"/missions/{mission_id}").text
    detail = client.get(f"/submissions/{submission_id}")
    assert "+۱۰" in detail.text
    assert "MISSION_SAMPLE_01" in detail.text
    assert "نسخه ۱" in detail.text
    score = client.get("/score")
    assert "موجودی امتیاز" in score.text
    assert "+۱۰" in score.text
    board = client.get("/leaderboard")
    table = board.text.split("<tbody>", 1)[1].split("</tbody>", 1)[0]
    assert table.index("امیر رضایی") < table.index("سارا محمدی")
    assert table.index("سارا محمدی") < table.index("مریم کاظمی")

    # پرده ۴ — نگار امتیاز مأموریت را ۱۰ → ۱۵ می‌کند.
    post(client, settings, "/logout")
    login(client, settings, ADMIN)
    changed = post(
        client,
        settings,
        f"/admin/missions/{mission_id}",
        data={
            "title": MISSION_ONE,
            "description": "از یخچال محصولات، در وضعیت چیدمان استاندارد، عکس بگیرید و ارسال کنید.",
            "points": "15",
            "max_per_user": "1",
            "starts_on": _day(-2),
            "ends_on": _day(30),
        },
    )
    assert "نسخه جدید قانون امتیاز منتشر شد" in changed.text
    assert int(db.execute(
        "SELECT points FROM score_events WHERE source_id = ?", (submission_id,)
    ).fetchone()[0]) == 10

    # پرده ۵ — ورود فایل فروش نمونه و پردازش تکرارپذیر.
    detail = upload(client, settings, sample_workbook_bytes(), filename="sales-sample.xlsx")
    assert "اعتبارسنجی‌شده — آماده پردازش" in detail.text
    assert "۶" in detail.text and "۴" in detail.text
    import_id = re.search(r"/admin/sales/([0-9a-f-]{36})/process", detail.text)
    assert import_id is not None
    processed = post(client, settings, f"/admin/sales/{import_id.group(1)}/process")
    assert "۴ رخداد امتیاز جدید ثبت شد" in processed.text
    assert "تعداد ردیف‌ها می‌خواند" in processed.text
    assert "مجموع امتیاز رخدادها با مجموع ثبت‌شده برابر است (۱۵)" in processed.text
    again = post(client, settings, f"/admin/sales/{import_id.group(1)}/process")
    assert "۰ رخداد امتیاز جدید ثبت شد" in again.text

    # پرده ۶ — نتیجه برای سارا.
    post(client, settings, "/logout")
    login(client, settings, VISITOR)
    assert "۱۵" in client.get("/home").text
    score = client.get("/score")
    assert "+۱۰" in score.text and "+۴" in score.text and "+۱" in score.text
    assert "SALES_AMOUNT_SAMPLE" in score.text
    totals = {
        row["full_name"]: int(row["total"])
        for row in db.execute(
            """SELECT u.full_name, COALESCE(SUM(se.points), 0) AS total
               FROM users u LEFT JOIN score_events se ON se.user_id = u.id
               WHERE u.role = 'visitor' GROUP BY u.id"""
        )
    }
    assert totals == {"امیر رضایی": 17, "سارا محمدی": 15, "مریم کاظمی": 8}

    # بخش اختیاری — اصلاح امتیاز مأموریت سارا.
    post(client, settings, "/logout")
    login(client, settings, ADMIN)
    assert "اصلاح امتیاز" in client.get(f"/submissions/{submission_id}").text
    event_id = row_id(
        settings,
        "SELECT id FROM score_events WHERE source_id = ? AND corrects_event_id IS NULL",
        (submission_id,),
    )
    assert post(
        client,
        settings,
        f"/admin/score-events/{event_id}/reverse",
        data={"reason": "اصلاح نمونه در تمرین دمو"},
    ).status_code == 200
    post(client, settings, "/logout")
    login(client, settings, VISITOR)
    assert "۵" in client.get("/home").text
    assert "اصلاح" in client.get("/score").text
    corrected = {
        row["full_name"]: int(row["total"])
        for row in db.execute(
            """SELECT u.full_name, COALESCE(SUM(se.points), 0) AS total
               FROM users u LEFT JOIN score_events se ON se.user_id = u.id
               WHERE u.role = 'visitor' GROUP BY u.id"""
        )
    }
    assert corrected == {"امیر رضایی": 17, "سارا محمدی": 5, "مریم کاظمی": 8}


def test_admin_review_screen_can_correct_a_mission_score(
    client: TestClient, settings: Settings, db: sqlite3.Connection
) -> None:
    from tests.test_corrections import awarded_submission

    submission_id, event_id = awarded_submission(client, settings, request_id="a2-review")
    page = client.get(f"/admin/submissions/{submission_id}")
    assert page.status_code == 200
    assert "اصلاح امتیاز" in page.text
    assert f"/admin/score-events/{event_id}/reverse" in page.text
    response = post(
        client,
        settings,
        f"/admin/score-events/{event_id}/reverse",
        data={"reason": "اصلاح از صفحه بازبینی پنل"},
    )
    assert response.status_code == 200
    after = client.get(f"/admin/submissions/{submission_id}")
    assert "این امتیاز اصلاح شده است" in after.text
    assert db.execute(
        "SELECT COUNT(*) FROM score_events WHERE corrects_event_id = ?", (event_id,)
    ).fetchone()[0] == 1


def test_sales_score_can_be_corrected_from_import_detail(
    client: TestClient, settings: Settings, db: sqlite3.Connection
) -> None:
    login(client, settings, ADMIN)
    detail = upload(client, settings, sample_workbook_bytes(), filename="sales-sample.xlsx")
    import_id = re.search(r"/admin/sales/([0-9a-f-]{36})/process", detail.text).group(1)
    assert post(client, settings, f"/admin/sales/{import_id}/process").status_code == 200
    event = db.execute(
        """SELECT se.id, se.points, se.user_id FROM score_events se
           JOIN sales_records r ON r.id = se.source_id
           WHERE r.import_id = ? AND se.source_type = 'sales_record'
             AND se.corrects_event_id IS NULL ORDER BY r.row_number LIMIT 1""",
        (import_id,),
    ).fetchone()
    assert event is not None
    before = db.execute(
        "SELECT balance FROM point_wallets WHERE user_id = ?", (event["user_id"],)
    ).fetchone()["balance"]

    page = client.get(f"/admin/sales/{import_id}")
    assert "اصلاح امتیاز فروش" in page.text
    assert f"/admin/score-events/{event['id']}/reverse" in page.text
    response = post(
        client,
        settings,
        f"/admin/score-events/{event['id']}/reverse",
        data={"reason": "اصلاح نمونه امتیاز فروش"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"].startswith(f"/admin/sales/{import_id}?reversed=1")
    after = client.get(f"/admin/sales/{import_id}")
    assert "این امتیاز اصلاح شده است" in after.text
    assert "اصلاح نمونه امتیاز فروش" in after.text
    wallet = db.execute(
        "SELECT balance FROM point_wallets WHERE user_id = ?", (event["user_id"],)
    ).fetchone()["balance"]
    assert int(wallet) == int(before) - int(event["points"])
    correction = db.execute(
        "SELECT points FROM score_events WHERE corrects_event_id = ?", (event["id"],)
    ).fetchone()
    assert int(correction["points"]) == -int(event["points"])

    second = post(
        client,
        settings,
        f"/admin/score-events/{event['id']}/reverse",
        data={"reason": "تلاش دوباره"},
    )
    assert second.status_code == 409
    assert "قبلاً اصلاح شده" in second.text


def test_sales_score_correction_is_admin_only_and_org_scoped(
    client: TestClient, settings: Settings, db: sqlite3.Connection
) -> None:
    login(client, settings, ADMIN)
    detail = upload(client, settings, sample_workbook_bytes(), filename="sales-sample.xlsx")
    import_id = re.search(r"/admin/sales/([0-9a-f-]{36})/process", detail.text).group(1)
    assert post(client, settings, f"/admin/sales/{import_id}/process").status_code == 200
    event_id = row_id(
        settings,
        """SELECT se.id FROM score_events se JOIN sales_records r ON r.id = se.source_id
           WHERE r.import_id = ? AND se.corrects_event_id IS NULL LIMIT 1""",
        (import_id,),
    )
    post(client, settings, "/logout")
    login(client, settings, OPERATOR)
    assert post(
        client, settings, f"/admin/score-events/{event_id}/reverse", data={"reason": "اپراتور"}
    ).status_code == 403

    post(client, settings, "/logout")
    login(client, settings, ADMIN)
    db.execute(
        "INSERT INTO organizations (id, name, created_at) VALUES (?, ?, ?)",
        ("other-org", "سازمان دیگر", "2026-01-01T00:00:00+00:00"),
    )
    db.execute(
        "UPDATE users SET organization_id = 'other-org' WHERE id = ("
        "SELECT user_id FROM score_events WHERE id = ?)",
        (event_id,),
    )
    db.commit()
    assert post(
        client, settings, f"/admin/score-events/{event_id}/reverse", data={"reason": "خارج سازمان"}
    ).status_code == 403


def test_demo_optional_new_rule_version_awards_fifteen_at_approval(
    client: TestClient, settings: Settings, db: sqlite3.Connection
) -> None:
    login(client, settings, ADMIN)
    mission_id = row_id(settings, "SELECT id FROM missions WHERE title = ?", (MISSION_ONE,))
    assert post(
        client,
        settings,
        f"/admin/missions/{mission_id}",
        data={
            "title": MISSION_ONE,
            "description": "از یخچال محصولات، در وضعیت چیدمان استاندارد، عکس بگیرید و ارسال کنید.",
            "points": "15",
            "max_per_user": "1",
            "starts_on": _day(-2),
            "ends_on": _day(30),
        },
    ).status_code == 200
    post(client, settings, "/logout")
    login(client, settings, OTHER_VISITOR)
    assert submit(client, settings, MISSION_ONE, request_id="demo-amir-v2").status_code == 200
    submission_id = row_id(
        settings, "SELECT id FROM submissions WHERE request_id = ?", ("demo-amir-v2",)
    )
    post(client, settings, "/logout")
    login(client, settings, OPERATOR)
    assert post(
        client,
        settings,
        f"/admin/submissions/{submission_id}/review",
        data={"decision": "approve", "reason": ""},
    ).status_code == 200
    event = db.execute(
        "SELECT se.points, srv.version FROM score_events se "
        "JOIN scoring_rule_versions srv ON srv.id = se.rule_version_id "
        "WHERE se.source_id = ?",
        (submission_id,),
    ).fetchone()
    assert int(event["points"]) == 15
    assert int(event["version"]) == 2
    wallet = db.execute(
        "SELECT balance FROM point_wallets WHERE user_id = (SELECT id FROM users WHERE mobile = ?)",
        (OTHER_VISITOR,),
    ).fetchone()
    assert int(wallet["balance"]) == 30
