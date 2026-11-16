"""Sales import service: Upload -> Validate -> Preview -> Confirm (process).

Shared by the JSON API and the demo CLI so both follow exactly the same rules:
* upload never scores anything; it validates and stores the rows (status ``validated``);
* the file fingerprint and every external id are de-duplicated (no double counting);
* processing is an explicit, idempotent confirmation step (``repo.process_sales_import``).
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from decimal import Decimal
from typing import Any

from app import repo, sales

ERROR_LABELS = {
    "E_EXTERNAL_ID": "Missing row identifier",
    "E_USER_ID": "Missing sales representative code",
    "E_DUPLICATE_IN_FILE": "Duplicate identifier inside this file",
    "E_DUPLICATE_EXISTING": "Already imported in an earlier file",
    "E_USER_MAPPING": "Sales representative code not found in organization",
    "E_DATE": "Invalid sale date",
    "E_FUTURE_DATE": "Sale date is in the future",
    "E_QUANTITY": "Quantity must be greater than zero",
    "E_AMOUNT": "Amount must be zero or positive",
    "E_SKU": "Missing product (SKU) code",
    "E_BRAND": "Missing or unknown brand",
}


class ImportRejected(Exception):
    def __init__(self, status_code: int, code: str, message: str, existing_id: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.existing_id = existing_id


def stage_import(
    conn: sqlite3.Connection,
    user,
    filename: str,
    raw: bytes,
    *,
    max_bytes: int,
    max_rows: int,
) -> sqlite3.Row:
    """Validate and store an upload. Raises ``ImportRejected`` for file-level problems."""
    if not filename or not filename.lower().endswith(".xlsx"):
        raise ImportRejected(422, "INVALID_FILE_TYPE", "Only .xlsx workbooks are accepted.")
    if not raw:
        raise ImportRejected(422, "EMPTY_FILE", "The file is empty.")
    if len(raw) > max_bytes:
        raise ImportRejected(
            422, "FILE_TOO_LARGE", f"File exceeds {max_bytes // (1024 * 1024)} MB."
        )
    sha = hashlib.sha256(raw).hexdigest()
    duplicate = repo.sales_import_by_fingerprint(conn, user.organization_id, sha)
    if duplicate is not None:
        raise ImportRejected(
            409,
            "DUPLICATE_FILE",
            "This exact file was already uploaded; nothing was imported again.",
            existing_id=duplicate["id"],
        )
    try:
        parsed = sales.parse_workbook(raw, max_rows)
        target_rows = sales.parse_targets(raw, max_rows)
    except sales.SalesFileError as exc:
        raise ImportRejected(422, "INVALID_WORKBOOK", str(exc)) from exc

    user_map = repo.sales_user_map(conn, user.organization_id)
    brands = repo.organization_brands(conn, user.organization_id)
    validated = sales.validate_rows(
        parsed,
        user_map,
        existing_ids=repo.sales_external_ids(conn, user.organization_id),
        brands=brands,
    )
    targets = sales.validate_targets(target_rows, user_map, brands) if target_rows else None
    origin = sales.detect_origin(raw)
    try:
        row = repo.create_sales_import(
            conn,
            user.organization_id,
            user.id,
            filename[:160],
            sha,
            validated,
            origin=origin,
            targets=targets,
        )
    except sqlite3.IntegrityError as exc:
        raise ImportRejected(
            409, "CONCURRENT_IMPORT", "The file or one of its rows was imported concurrently."
        ) from exc
    repo.audit(
        conn,
        user.id,
        "sales.import.uploaded",
        "sales_import",
        row["id"],
        {"file": filename[:160], "rows": len(validated), "origin": origin},
    )
    conn.commit()
    return row


def _row_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "row_number": row["row_number"],
        "external_id": row["external_id"],
        "user_external_id": row["user_external_id"],
        "sale_date": row["sale_date"],
        "brand_code": row["brand_code"],
        "sku_code": row["sku_code"],
        "quantity": row["quantity"],
        "amount": row["amount"],
        "status": row["status"],
        "error_code": row["error_code"],
        "error": ERROR_LABELS.get(row["error_code"] or "", row["error_message"]),
    }


def summarize(conn: sqlite3.Connection, import_row: sqlite3.Row, *, row_limit: int = 60) -> dict:
    """Everything the preview/confirm screen needs, computed from stored rows."""
    import_id = import_row["id"]
    counts = repo.sales_record_counts(conn, import_id)
    accounted = sum(counts.values())
    scored_points = int(
        conn.execute(
            """SELECT COALESCE(SUM(points), 0) AS total FROM score_events
               WHERE source_type = 'sales_record'
                 AND source_id IN (SELECT id FROM sales_records WHERE import_id = ?)""",
            (import_id,),
        ).fetchone()["total"]
    )
    brand_rows = conn.execute(
        """SELECT COALESCE(brand_code, 'UNASSIGNED') AS brand, status,
                  SUM(amount) AS amount, SUM(quantity) AS quantity, COUNT(*) AS records
           FROM sales_records WHERE import_id = ? AND status IN ('valid', 'scored')
           GROUP BY brand, status ORDER BY brand""",
        (import_id,),
    ).fetchall()
    brands: dict[str, dict[str, Any]] = {}
    total_amount = Decimal(0)
    for br in brand_rows:
        item = brands.setdefault(
            br["brand"], {"brand": br["brand"], "amount": Decimal(0), "records": 0}
        )
        item["amount"] += Decimal(str(br["amount"] or 0))
        item["records"] += br["records"]
        total_amount += Decimal(str(br["amount"] or 0))
    problem_rows = conn.execute(
        """SELECT * FROM sales_records WHERE import_id = ? AND status IN ('invalid', 'duplicate')
           ORDER BY row_number LIMIT ?""",
        (import_id, row_limit),
    ).fetchall()
    sample_rows = conn.execute(
        """SELECT * FROM sales_records WHERE import_id = ? AND status IN ('valid', 'scored')
           ORDER BY row_number LIMIT ?""",
        (import_id, 15),
    ).fetchall()
    targets = json.loads(import_row["targets_json"]) if import_row["targets_json"] else []
    stats = {"valid": 0, "invalid": 0}
    for t in targets:
        stats[t["status"]] = stats.get(t["status"], 0) + 1
    status = import_row["status"]
    return {
        "id": import_id,
        "file_name": import_row["file_name"],
        "status": status,
        "data_origin": import_row["data_origin"],
        "is_sample": import_row["data_origin"] == "sample",
        "uploaded_by": import_row["uploaded_by_name"]
        if "uploaded_by_name" in import_row.keys()
        else None,
        "created_at": import_row["created_at"],
        "finished_at": import_row["finished_at"],
        "can_process": status in {"validated", "failed"} and counts["valid"] > 0,
        "counts": {
            "total": import_row["row_count"],
            "valid": counts["valid"] + counts["scored"],
            "pending": counts["valid"],
            "processed": counts["scored"],
            "rejected": counts["invalid"],
            "duplicates": counts["duplicate"],
        },
        "totals": {
            "amount": int(total_amount),
            "records": sum(b["records"] for b in brands.values()),
        },
        "brands": [
            {"brand": b["brand"], "amount": int(b["amount"]), "records": b["records"]}
            for b in brands.values()
        ],
        "targets": {"rows": len(targets), "valid": stats["valid"], "invalid": stats["invalid"]},
        "target_issues": [t for t in targets if t["status"] != "valid"][:20],
        "reconciliation": {
            "rows_ok": accounted == import_row["row_count"],
            "points_ok": scored_points == int(import_row["points_sum"]),
            "scored_points": scored_points,
            "points_sum": int(import_row["points_sum"]),
        },
        "problem_rows": [_row_dict(r) for r in problem_rows],
        "sample_rows": [_row_dict(r) for r in sample_rows],
    }


def list_imports(conn: sqlite3.Connection, org_id: str) -> list[dict[str, Any]]:
    out = []
    for row in repo.list_sales_imports(conn, org_id):
        counts = repo.sales_record_counts(conn, row["id"])
        out.append(
            {
                "id": row["id"],
                "file_name": row["file_name"],
                "status": row["status"],
                "data_origin": row["data_origin"],
                "is_sample": row["data_origin"] == "sample",
                "created_at": row["created_at"],
                "uploaded_by": row["uploaded_by_name"],
                "counts": {
                    "total": row["row_count"],
                    "processed": counts["scored"],
                    "pending": counts["valid"],
                    "rejected": counts["invalid"],
                    "duplicates": counts["duplicate"],
                },
            }
        )
    return out
