"""Admin demo panel (read-only views), import breakdown and hosted-demo login protection."""

from __future__ import annotations

import sqlite3
import uuid
from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from tests.conftest import ADMIN, OPERATOR, VISITOR, login, post
from tests.test_sales import MAPPED_USER, upload, workbook_bytes

STAFF_CODE = "demo-staff-code-for-tests-only"


def _count(db: sqlite3.Connection, sql: str) -> int:
    return db.execute(sql).fetchone()[0]


def test_dashboard_numbers_come_from_the_database(
    client: TestClient, settings: Settings, db: sqlite3.Connection
) -> None:
    login(client, settings, ADMIN)
    sheet = workbook_bytes([["D-1", MAPPED_USER, "2026-11-01", "SKU", 1, 7_000_000]])
    upload(client, settings, sheet)
    import_id = db.execute("SELECT id FROM sales_imports").fetchone()[0]
    post(client, settings, f"/admin/sales/{import_id}/process")

    response = client.get("/admin")
    assert response.status_code == 200
    wallet_total = db.execute("SELECT SUM(balance) FROM point_wallets").fetchone()[0]
    ledger_total = db.execute("SELECT SUM(points) FROM score_events").fetchone()[0]
    assert wallet_total == ledger_total
    users_total = _count(db, "SELECT COUNT(*) FROM users")
    sales_amount = db.execute(
        "SELECT SUM(amount) FROM sales_records WHERE status IN ('valid','scored')"
    ).fetchone()[0]
    assert "نمونه" in response.text
    from app.jalali import to_persian_digits

    assert to_persian_digits(str(users_total)) in response.text
    assert to_persian_digits(f"{sales_amount:,.0f}") in response.text
    assert to_persian_digits(str(wallet_total)) in response.text


def test_admin_pages_require_admin(client: TestClient, settings: Settings) -> None:
    paths = ["/admin", "/admin/users", "/admin/points", "/admin/game", "/admin/activity",
             "/admin/leaderboard"]
    for path in paths:  # anonymous -> login redirect
        assert client.get(path, follow_redirects=False).status_code in {302, 303, 401}
    login(client, settings, OPERATOR)
    for path in paths:
        assert client.get(path).status_code == 403
    login(client, settings, VISITOR)
    for path in paths:
        assert client.get(path).status_code == 403


def test_user_pages_are_organization_scoped(
    client: TestClient, settings: Settings, db: sqlite3.Connection
) -> None:
    org_b, admin_b, visitor_b = (str(uuid.uuid4()) for _ in range(3))
    now = datetime.now(tz=UTC).isoformat(timespec="seconds")
    db.execute("INSERT INTO organizations (id, name, created_at) VALUES (?, 'Org B', ?)",
               (org_b, now))
    for uid, name, mobile, role in (
        (admin_b, "ادمین ب", "09129990001", "admin"),
        (visitor_b, "ویزیتور ب", "09129990002", "visitor"),
    ):
        db.execute(
            """INSERT INTO users (id, organization_id, full_name, mobile, role, is_active,
               created_at) VALUES (?, ?, ?, ?, ?, 1, ?)""",
            (uid, org_b, name, mobile, role, now),
        )
    db.commit()

    login(client, settings, ADMIN)  # org A admin
    assert client.get(f"/admin/users/{visitor_b}").status_code == 404
    listing = client.get("/admin/users").text
    assert "ویزیتور ب" not in listing and "سارا محمدی" in listing
    assert "ویزیتور ب" not in client.get("/admin/points").text
    assert "ویزیتور ب" not in client.get("/admin/leaderboard").text

    login(client, settings, "09129990001")  # org B admin
    assert "سارا محمدی" not in client.get("/admin/users").text
    assert client.get("/admin/users/" + visitor_b).status_code == 200


def test_user_search_by_name_and_external_id(client: TestClient, settings: Settings) -> None:
    login(client, settings, ADMIN)
    assert "سارا محمدی" in client.get("/admin/users", params={"q": "سارا"}).text
    by_ext = client.get("/admin/users", params={"q": MAPPED_USER}).text
    assert "سارا محمدی" in by_ext and "امیر رضایی" not in by_ext


def test_import_breakdown_matches_ledger_and_reprocess_adds_nothing(
    client: TestClient, settings: Settings, db: sqlite3.Connection
) -> None:
    login(client, settings, ADMIN)
    content = workbook_bytes(
        [
            ["R-1", MAPPED_USER, "2026-11-01", "SKU", 1, 3_000_000],
            ["R-2", MAPPED_USER, "2026-11-02", "SKU", 1, 2_000_000],
            ["R-3", "VIS-999", "2026-11-02", "SKU", 1, 2_000_000],  # invalid
        ]
    )
    upload(client, settings, content)
    import_id = db.execute("SELECT id FROM sales_imports").fetchone()[0]
    before = _count(db, "SELECT COUNT(*) FROM score_events")
    detail = client.get(f"/admin/sales/{import_id}")
    assert "امتیاز مورد انتظار" in detail.text

    post(client, settings, f"/admin/sales/{import_id}/process")
    after_first = _count(db, "SELECT COUNT(*) FROM score_events")
    assert after_first - before == 2
    post(client, settings, f"/admin/sales/{import_id}/process")
    assert _count(db, "SELECT COUNT(*) FROM score_events") == after_first  # no double award

    from app import admin_queries

    breakdown = admin_queries.import_user_breakdown(db, import_id)
    assert len(breakdown) == 1 and breakdown[0]["events"] == 2 and breakdown[0]["awarded"] == 5
    import_row = db.execute("SELECT points_sum FROM sales_imports").fetchone()
    assert import_row["points_sum"] == breakdown[0]["net"] == 5
    page = client.get(f"/admin/sales/{import_id}")
    assert "دریافت‌کنندگان امتیاز" in page.text and "سارا محمدی" in page.text

    # same file again is refused (fingerprint), never re-scored
    again = upload(client, settings, content)
    assert again.status_code == 409
    assert _count(db, "SELECT COUNT(*) FROM score_events") == after_first


def test_points_page_filters_and_labels_corrections(
    client: TestClient, settings: Settings, db: sqlite3.Connection
) -> None:
    login(client, settings, ADMIN)
    page = client.get("/admin/points", params={"source": "mission_submission"})
    assert page.status_code == 200 and "MISSION_SAMPLE" in page.text
    sales_only = client.get("/admin/points", params={"source": "sales_record"})
    assert "MISSION_SAMPLE" not in sales_only.text


# ------------------------------------------------------------------ hosted demo env
@pytest.fixture
def demo_client(settings: Settings) -> Iterator[TestClient]:
    hosted = replace(settings, env="demo", demo_staff_code=STAFF_CODE)
    with TestClient(create_app(hosted)) as test_client:
        yield test_client


def _user_id(settings: Settings, mobile: str) -> str:
    conn = sqlite3.connect(settings.db_path)
    try:
        return conn.execute("SELECT id FROM users WHERE mobile = ?", (mobile,)).fetchone()[0]
    finally:
        conn.close()


def test_demo_env_visitor_login_is_secure_and_staff_needs_code(
    demo_client: TestClient, settings: Settings
) -> None:
    visitor, admin = _user_id(settings, VISITOR), _user_id(settings, ADMIN)

    ok = demo_client.post("/demo-login", data={"user_id": visitor}, follow_redirects=False)
    assert ok.status_code == 303
    assert "secure" in ok.headers["set-cookie"].lower()

    for data in ({"user_id": admin}, {"user_id": admin, "access_code": "wrong"}):
        denied = demo_client.post("/demo-login", data=data, follow_redirects=False)
        assert denied.status_code == 403
        assert "set-cookie" not in denied.headers

    allowed = demo_client.post(
        "/demo-login", data={"user_id": admin, "access_code": STAFF_CODE}, follow_redirects=False
    )
    assert allowed.status_code == 303 and allowed.headers["location"].startswith("/admin")


def test_demo_env_staff_login_disabled_without_configured_code(settings: Settings) -> None:
    hosted = replace(settings, env="demo", demo_staff_code="")
    with TestClient(create_app(hosted)) as c:
        admin = _user_id(settings, ADMIN)
        assert c.post("/demo-login", data={"user_id": admin, "access_code": ""}).status_code == 403
        login_page = c.get("/login").text
        assert "مدیر سیستم" not in login_page and "ورود کارکنان" not in login_page


def test_demo_env_login_page_lists_only_visitors_in_picker(
    demo_client: TestClient,
) -> None:
    page = demo_client.get("/login").text
    picker = page.split("<details")[0]
    assert "مدیر سیستم" not in picker and "اپراتور" not in picker
    assert "DEMO" in page


def test_demo_env_game_login_is_visitor_only(demo_client: TestClient, settings: Settings) -> None:
    users = demo_client.get("/api/v1/game/demo-users")
    assert users.status_code == 200 and users.json()["users"]
    admin = _user_id(settings, ADMIN)
    assert demo_client.post("/api/v1/game/demo-login", json={"user_id": admin}).status_code == 404
    visitor = _user_id(settings, VISITOR)
    login_response = demo_client.post("/api/v1/game/demo-login", json={"user_id": visitor})
    assert login_response.status_code == 200
    assert "secure" in login_response.headers["set-cookie"].lower()
    assert login_response.headers["X-CSRF-Token"]


def test_prod_like_env_still_blocks_game_demo_login(settings: Settings) -> None:
    other = replace(settings, env="staging")
    with TestClient(create_app(other)) as c:
        assert c.get("/api/v1/game/demo-users").status_code == 404
