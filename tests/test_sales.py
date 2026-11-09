"""Sales import (EP-07): validation, dedupe, idempotent scoring, permissions."""

from __future__ import annotations

import io
import re
import sqlite3

from fastapi.testclient import TestClient
from openpyxl import Workbook

from app.config import Settings
from tests.conftest import ADMIN, OPERATOR, VISITOR, login, post

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
HEADERS = ["external_id", "user_external_id", "sale_date", "sku_code", "quantity", "amount"]
MAPPED_USER = "VIS-001"  # سارا محمدی in the seeded mapping (SAMPLE)


def workbook_bytes(rows: list[list], headers: list[str] | None = None) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(headers or HEADERS)
    for row in rows:
        sheet.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def upload(
    client: TestClient,
    settings: Settings,
    content: bytes,
    filename: str = "sales.xlsx",
    follow_redirects: bool = True,
):
    return post(
        client,
        settings,
        "/admin/sales",
        files={"file": (filename, content, XLSX_MIME)},
        follow_redirects=follow_redirects,
    )


def test_upload_validates_without_scoring(
    client: TestClient, settings: Settings, db: sqlite3.Connection
) -> None:
    login(client, settings, ADMIN)
    content = workbook_bytes(
        [
            ["S-1", MAPPED_USER, "2026-11-01", "SKU-1", 2, 5_000_000],
            ["S-1", MAPPED_USER, "2026-11-01", "SKU-1", 2, 5_000_000],  # duplicate in file
            ["S-3", "VIS-999", "2026-11-01", "SKU-3", 1, 1_000_000],  # unmapped user
        ]
    )
    response = upload(client, settings, content)
    assert response.status_code == 200
    assert "اعتبارسنجی‌شده" in response.text

    import_row = db.execute("SELECT * FROM sales_imports").fetchone()
    assert import_row["status"] == "validated"
    assert (import_row["row_count"], import_row["valid_count"]) == (3, 1)
    assert (import_row["duplicate_count"], import_row["invalid_count"]) == (1, 1)
    assert db.execute("SELECT COUNT(*) FROM score_events").fetchone()[0] == 1  # seed only
    assert "SKU-1" in response.text or "S-1" in response.text


def test_process_creates_each_score_once(
    client: TestClient, settings: Settings, db: sqlite3.Connection
) -> None:
    login(client, settings, ADMIN)
    content = workbook_bytes(
        [
            ["S-10", MAPPED_USER, "2026-11-01", "SKU-1", 1, 2_500_000],
            ["S-11", MAPPED_USER, "2026-11-02", "SKU-2", 1, 1_000_000],
        ]
    )
    detail = upload(client, settings, content)
    assert detail.status_code == 200

    import_id = db.execute("SELECT id FROM sales_imports").fetchone()["id"]
    processed = post(
        client, settings, f"/admin/sales/{import_id}/process", data={}, follow_redirects=False
    )
    assert processed.status_code == 303
    assert processed.headers["location"].endswith("?processed=2")

    events = db.execute(
        "SELECT points, source_type FROM score_events WHERE source_type = 'sales_record'"
    ).fetchall()
    assert sorted(int(event["points"]) for event in events) == [1, 2]

    import_row = db.execute("SELECT * FROM sales_imports WHERE id = ?", (import_id,)).fetchone()
    assert import_row["status"] == "completed"
    assert int(import_row["points_sum"]) == 3
    assert import_row["created_count"] == 2

    wallet = db.execute(
        "SELECT balance FROM point_wallets WHERE user_id = ("
        "SELECT id FROM users WHERE mobile = ?)",
        (VISITOR,),
    ).fetchone()
    assert int(wallet["balance"]) == 3

    # Re-running the same import must not award points twice.
    again = post(
        client, settings, f"/admin/sales/{import_id}/process", data={}, follow_redirects=False
    )
    assert again.status_code == 303
    assert again.headers["location"].endswith("?processed=0")
    assert (
        db.execute(
            "SELECT COUNT(*) FROM score_events WHERE source_type = 'sales_record'"
        ).fetchone()[0]
        == 2
    )


def test_same_file_is_rejected_by_fingerprint(
    client: TestClient, settings: Settings
) -> None:
    login(client, settings, ADMIN)
    content = workbook_bytes([["S-20", MAPPED_USER, "2026-11-01", "SKU-1", 1, 2_000_000]])
    assert upload(client, settings, content).status_code == 200

    duplicate = upload(client, settings, content)
    assert duplicate.status_code == 409
    assert "قبلاً آپلود شده" in duplicate.text


def test_duplicate_external_id_across_imports_is_skipped(
    client: TestClient, settings: Settings, db: sqlite3.Connection
) -> None:
    login(client, settings, ADMIN)
    first = workbook_bytes([["S-30", MAPPED_USER, "2026-11-01", "SKU-1", 1, 1_000_000]])
    upload(client, settings, first)
    second = upload(
        client,
        settings,
        workbook_bytes([["S-30", MAPPED_USER, "2026-11-02", "SKU-1", 1, 9_000_000]]),
    )
    assert second.status_code == 200
    assert "این رکورد در import قبلی ثبت شده است" in second.text

    duplicates = db.execute(
        "SELECT COUNT(*) FROM sales_records WHERE external_id = 'S-30' AND status = 'duplicate'"
    ).fetchone()[0]
    assert duplicates == 1
    assert (
        db.execute(
            "SELECT error_code FROM sales_records WHERE status = 'duplicate'"
        ).fetchone()["error_code"]
        == "E_DUPLICATE_EXISTING"
    )


def test_missing_columns_reject_the_file(
    client: TestClient, settings: Settings, db: sqlite3.Connection
) -> None:
    login(client, settings, ADMIN)
    content = workbook_bytes(
        [["S-40", MAPPED_USER, "2026-11-01", "SKU-1", 1]],
        headers=["external_id", "user_external_id", "sale_date", "sku_code", "quantity"],
    )
    response = upload(client, settings, content)
    assert response.status_code == 422
    assert "amount" in response.text
    assert db.execute("SELECT COUNT(*) FROM sales_imports").fetchone()[0] == 0


def test_non_xlsx_is_rejected(client: TestClient, settings: Settings) -> None:
    login(client, settings, ADMIN)
    response = upload(client, settings, b"a,b\n1,2\n", filename="sales.csv")
    assert response.status_code == 422
    assert "xlsx" in response.text


def test_row_errors_do_not_block_valid_rows(
    client: TestClient, settings: Settings, db: sqlite3.Connection
) -> None:
    login(client, settings, ADMIN)
    content = workbook_bytes(
        [
            ["S-50", MAPPED_USER, "2099-01-01", "SKU-1", 1, 1_000_000],  # future date
            ["S-51", MAPPED_USER, "2026-11-01", "SKU-1", 0, 1_000_000],  # zero quantity
            ["S-52", MAPPED_USER, "2026-11-01", "SKU-1", 1, -5],  # negative amount
            ["S-53", MAPPED_USER, "2026-11-01", "SKU-1", 1, 2_000_000],  # fine
        ]
    )
    response = upload(client, settings, content)
    assert response.status_code == 200
    assert "E_FUTURE_DATE" not in response.text  # messages are shown, codes stay internal
    assert "تاریخ فروش در آینده است" in response.text

    import_row = db.execute("SELECT * FROM sales_imports").fetchone()
    assert import_row["valid_count"] == 1
    assert import_row["invalid_count"] == 3

    post(client, settings, f"/admin/sales/{import_row['id']}/process", data={})
    assert (
        db.execute(
            "SELECT COUNT(*) FROM score_events WHERE source_type = 'sales_record'"
        ).fetchone()[0]
        == 1
    )


def test_amount_below_one_unit_scores_nothing(
    client: TestClient, settings: Settings, db: sqlite3.Connection
) -> None:
    login(client, settings, ADMIN)
    upload(client, settings, workbook_bytes([["S-60", MAPPED_USER, "2026-11-01", "S", 1, 999_999]]))
    import_id = db.execute("SELECT id FROM sales_imports").fetchone()["id"]
    post(client, settings, f"/admin/sales/{import_id}/process", data={})

    assert (
        db.execute(
            "SELECT COUNT(*) FROM score_events WHERE source_type = 'sales_record'"
        ).fetchone()[0]
        == 0
    )
    row = db.execute("SELECT status FROM sales_records").fetchone()
    assert row["status"] == "scored"


def test_only_admin_can_use_sales_import(client: TestClient, settings: Settings) -> None:
    login(client, settings, VISITOR)
    assert client.get("/admin/sales").status_code == 403
    assert client.get("/admin/sales/new").status_code == 403

    post(client, settings, "/logout")
    login(client, settings, OPERATOR)
    assert client.get("/admin/sales").status_code == 403

    post(client, settings, "/logout")
    login(client, settings, ADMIN)
    assert client.get("/admin/sales").status_code == 200
    assert client.get("/admin/sales/new").status_code == 200


def test_upload_requires_csrf(client: TestClient, settings: Settings) -> None:
    login(client, settings, ADMIN)
    content = workbook_bytes([["S-70", MAPPED_USER, "2026-11-01", "SKU-1", 1, 1_000_000]])
    response = client.post(
        "/admin/sales",
        files={"file": ("sales.xlsx", content, XLSX_MIME)},
    )
    assert response.status_code == 403


def test_other_organization_import_is_not_visible(
    client: TestClient, settings: Settings, db: sqlite3.Connection
) -> None:
    login(client, settings, ADMIN)
    content = workbook_bytes([["S-80", MAPPED_USER, "2026-11-01", "SKU-1", 1, 1_000_000]])
    upload(client, settings, content)
    import_id = db.execute("SELECT id FROM sales_imports").fetchone()["id"]
    db.execute(
        """INSERT INTO organizations (id, name, created_at)
           VALUES ('other-org', 'دیگر', '2026-01-01T00:00:00+00:00')"""
    )
    db.execute("UPDATE sales_imports SET organization_id = 'other-org' WHERE id = ?", (import_id,))
    db.commit()

    assert client.get(f"/admin/sales/{import_id}").status_code == 404


def test_detail_page_shows_reconciliation(
    client: TestClient, settings: Settings
) -> None:
    login(client, settings, ADMIN)
    detail = upload(
        client,
        settings,
        workbook_bytes(
            [
                ["S-90", MAPPED_USER, "2026-11-01", "SKU-1", 1, 1_000_000],
                ["S-91", "VIS-999", "2026-11-01", "SKU-1", 1, 1_000_000],
            ]
        ),
    )
    assert "Reconciliation" in detail.text
    assert "تعداد ردیف‌ها می‌خواند" in detail.text
    import_id = re.search(r"/admin/sales/([0-9a-f-]{36})/process", detail.text)
    assert import_id is not None
