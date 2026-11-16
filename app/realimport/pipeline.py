"""Import pipeline: upload -> batch -> validate/stage -> preview -> confirm. All steps idempotent.

Layers written here: raw (ri_raw_rows), normalised dimensions + facts, organisational mapping
issues, branch-group schemes, targets and workbook reference figures. Source values are kept in
the raw layer; matching uses folded keys; the API only ever shows pseudonyms for people/customers.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

from app import repo
from app.config import Settings
from app.db import now_iso
from app.realimport import inspector
from app.realimport import profile as P
from app.realimport.inspector import WorkbookError
from app.realimport.normalize import (
    decimal_text,
    fold_text,
    is_error_cell,
    parse_decimal,
    source_text,
)
from app.realimport.pseudo import pseudonym

ERROR_LABELS = {
    "E_REQUIRED": "Required value is missing",
    "E_ERROR_CELL": "Excel error value (#N/A …) in a required cell",
    "E_PERIOD": "Month label does not match the configured period",
    "E_NET": "Net cartons missing or not numeric",
    "E_GROSS": "Gross cartons not numeric",
}
ISSUE_LABELS = {
    "visitor_not_in_roster": "Visitor key not found in the roster",
    "customer_group_unmapped": "Customer group missing from the CustomerGroup lookup",
    "customer_group_main_unmapped": "Customer group has an unknown main group label",
    "sku_factor_missing": "SKU has no carton factor",
    "factor_duplicate_code": "SKU code appears with different carton factors",
    "factor_header_swapped": "Factor sheet: code/name header labels are swapped (matched by content)",
    "branch_group_missing": "Branch missing from the branch-group lookup",
    "branch_spelling_variants": "Branch spelled with different Arabic/Persian letters (folded for matching)",
    "line_spelling_variants": "Sales line spelled in several ways (folded for matching)",
    "employee_code_missing": "Roster row without a usable personnel code",
    "shared_personnel_code": "One personnel code used by several visitor keys",
    "head_missing": "Roster rows without a head personnel code",
    "roster_duplicate_visitor": "Duplicate visitor key in the roster (first kept)",
    "seller_type_mismatch": "Seller type column disagrees with the visitor key suffix",
    "seller_type_case": "Seller type letter in lower case or unknown",
    "target_missing": "Manager row without a numeric target",
    "target_duplicate_entity": "Duplicate branch/line target row (first kept)",
    "target_other_period": "Manager sheet rows for another month skipped",
}


@dataclass
class Issues:
    items: dict[tuple[str, str], dict[str, Any]] = field(default_factory=dict)

    def add(self, issue_type: str, severity: str, entity_ref: str, **detail: Any) -> None:
        item = self.items.setdefault((issue_type, entity_ref), {"severity": severity, "detail": {"count": 0}})
        item["detail"]["count"] += 1
        for k, v in detail.items():
            item["detail"][k] = v

    def counts(self) -> dict[str, int]:
        out: dict[str, int] = defaultdict(int)
        for (t, _), _item in self.items.items():
            out[t] += 1
        return dict(out)


# ------------------------------------------------------------------------------ dimensions
class Dims:
    """Get-or-create for the shared dimensions, with an in-memory cache (28k rows -> few hundred keys)."""

    TABLES = {
        "branch": ("ri_branches", "norm_key"),
        "brand": ("ri_brands", "norm_key"),
        "line": ("ri_sales_lines", "norm_key"),
        "cgroup": ("ri_customer_groups", "norm_key"),
        "sku": ("ri_skus", "code"),
        "customer": ("ri_customers", "norm_key"),
        "employee": ("ri_employees", "person_key"),
    }

    def __init__(self, conn: sqlite3.Connection, key: str):
        self.conn, self.key = conn, key
        self.cache: dict[str, dict[str, int]] = {n: {} for n in self.TABLES}
        for name, (table, col) in self.TABLES.items():
            for r in conn.execute(f"SELECT id, {col} AS k FROM {table}"):  # noqa: S608 - fixed table names
                self.cache[name][r["k"]] = r["id"]
        self.variants: dict[tuple[str, str], set[str]] = defaultdict(set)

    def _get(self, name: str, norm: str, insert_sql: str, params: tuple) -> int:
        found = self.cache[name].get(norm)
        if found is not None:
            return found
        new_id = self.conn.execute(insert_sql, params).lastrowid
        self.cache[name][norm] = new_id
        return new_id

    def branch(self, source: str) -> int:
        norm = fold_text(source)
        self.variants[("ri_branches", norm)].add(source)
        return self._get("branch", norm, "INSERT INTO ri_branches (norm_key, source_value) VALUES (?, ?)", (norm, source))

    def brand(self, source: str) -> int:
        norm = fold_text(source)
        return self._get("brand", norm, "INSERT INTO ri_brands (norm_key, source_value) VALUES (?, ?)", (norm, source))

    def line(self, source: str) -> int:
        norm = P.line_code(source)
        self.variants[("ri_sales_lines", norm)].add(source)
        return self._get("line", norm, "INSERT INTO ri_sales_lines (norm_key, source_value) VALUES (?, ?)", (norm, source))

    def cgroup(self, source: str, main_group: str | None = None) -> int:
        norm = fold_text(source)
        found = self.cache["cgroup"].get(norm)
        if found is not None:
            if main_group:
                self.conn.execute("UPDATE ri_customer_groups SET main_group = ? WHERE id = ?", (main_group, found))
            return found
        return self._get(
            "cgroup", norm,
            "INSERT INTO ri_customer_groups (norm_key, source_value, main_group) VALUES (?, ?, ?)",
            (norm, source, main_group),
        )

    def sku(self, code: str, name: str | None = None) -> int:
        norm = fold_text(code).upper()
        return self._get("sku", norm, "INSERT INTO ri_skus (code, name_source) VALUES (?, ?)", (norm, name))

    def customer(self, source: str) -> int:
        norm = fold_text(source)
        return self._get(
            "customer", norm,
            "INSERT INTO ri_customers (norm_key, source_value, pseudonym) VALUES (?, ?, ?)",
            (norm, source, pseudonym("customer", norm, self.key)),
        )

    def employee(self, person_key: str, code: str) -> int:
        return self._get(
            "employee", person_key,
            "INSERT INTO ri_employees (person_key, personnel_code, pseudonym) VALUES (?, ?, ?)",
            (person_key, code, pseudonym("employee", person_key, self.key)),
        )

    def flush_variants(self, issues: Issues) -> None:
        for (table, norm), seen in self.variants.items():
            if len(seen) > 1:
                self.conn.execute(
                    f"UPDATE {table} SET variants_json = ? WHERE norm_key = ?",  # noqa: S608 - fixed table names
                    (json.dumps(sorted(seen), ensure_ascii=False), norm),
                )
                kind = "branch_spelling_variants" if table == "ri_branches" else "line_spelling_variants"
                issues.add(kind, "info", norm, variants=len(seen))


# ------------------------------------------------------------------------------ small helpers
def _jsonable(value: Any) -> Any:
    if isinstance(value, (int, float, str, bool)) or value is None:
        return value
    return str(value)


def _code_text(value: Any) -> str:
    """Personnel/branch-group codes: '' for blank/error, '1234567' for 1234567.0."""
    if value is None or is_error_cell(value):
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value).strip()


def _blank_code(text: str) -> bool:
    return fold_text(text) in {"", "0", "-", "n/a", "nan", "none"}


def _row_blank(cells) -> bool:
    return cells is None or all(c is None or (isinstance(c, str) and not c.strip()) for c in cells)


def _iter_rows(ws, header_row: int):
    for n, cells in enumerate(ws.iter_rows(min_row=header_row + 1, values_only=True), start=header_row + 1):
        if not _row_blank(cells):
            yield n, cells


def _cell(cells, cols: dict[str, int], name: str) -> Any:
    idx = cols.get(name)
    return cells[idx] if idx is not None and idx < len(cells) else None


def _sha(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()


# ------------------------------------------------------------------------------- upload/batch
def workbook_dir(settings: Settings) -> Path:
    return settings.real_import_dir or (settings.db_path.parent / "workbooks")


def upload_workbook(conn: sqlite3.Connection, settings: Settings, user_id: str | None, file_name: str, raw: bytes):
    """Store the workbook by hash (never modified afterwards). Same bytes -> same record."""
    if not file_name or not file_name.lower().endswith(".xlsx"):
        raise WorkbookError("INVALID_FILE_TYPE", "Only .xlsx workbooks are accepted.")
    if not raw:
        raise WorkbookError("EMPTY_FILE", "The file is empty.")
    if len(raw) > settings.real_import_max_bytes:
        raise WorkbookError("FILE_TOO_LARGE", f"File exceeds {settings.real_import_max_bytes // (1024 * 1024)} MB.", 413)
    sha = hashlib.sha256(raw).hexdigest()
    existing = conn.execute("SELECT * FROM ri_workbooks WHERE sha256 = ?", (sha,)).fetchone()
    if existing is not None:
        return existing, True
    inspection = inspector.inspect_workbook(raw)
    directory = workbook_dir(settings)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{sha}.xlsx"
    if not target.exists():
        tmp = target.with_suffix(".part")
        tmp.write_bytes(raw)
        tmp.replace(target)
    wb_id = str(uuid.uuid4())
    conn.execute(
        """INSERT INTO ri_workbooks (id, sha256, file_name, size_bytes, storage_path, inspection_json,
                                      data_origin, uploaded_by, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (wb_id, sha, file_name[:160], len(raw), target.name, json.dumps(inspection, ensure_ascii=False),
         inspection["data_origin"], user_id, now_iso()),
    )
    repo.audit(conn, user_id, "ri.workbook.uploaded", "ri_workbook", wb_id,
               {"sha256": sha, "bytes": len(raw), "sheets": inspection["sheet_count"], "origin": inspection["data_origin"]})
    conn.commit()
    return conn.execute("SELECT * FROM ri_workbooks WHERE id = ?", (wb_id,)).fetchone(), False


def _workbook_bytes(settings: Settings, wb_row: sqlite3.Row) -> bytes:
    raw = (workbook_dir(settings) / wb_row["storage_path"]).read_bytes()
    if hashlib.sha256(raw).hexdigest() != wb_row["sha256"]:
        raise WorkbookError("WORKBOOK_TAMPERED", "Stored workbook no longer matches its SHA-256.", 500)
    return raw


def create_batch(conn, settings, user_id, workbook_id: str, config: dict | None):
    wb_row = conn.execute("SELECT * FROM ri_workbooks WHERE id = ?", (workbook_id,)).fetchone()
    if wb_row is None:
        raise WorkbookError("WORKBOOK_NOT_FOUND", "Workbook not found.", 404)
    try:
        cfg = P.normalise_config(config)
    except (ValueError, KeyError, TypeError) as exc:
        raise WorkbookError("INVALID_CONFIG", str(exc)) from exc
    chash = P.config_hash(cfg)
    existing = conn.execute("SELECT * FROM ri_import_batches WHERE workbook_id = ? AND config_hash = ?",
                            (workbook_id, chash)).fetchone()
    if existing is not None:
        return existing, True
    inspection = inspector.inspect_workbook(_workbook_bytes(settings, wb_row), cfg)
    if inspection["problems"]:
        raise WorkbookError("WORKBOOK_STRUCTURE", " ".join(inspection["problems"]))
    batch_id = str(uuid.uuid4())
    conn.execute(
        """INSERT INTO ri_import_batches (id, workbook_id, period_year, period_month, config_json, config_hash,
                                          status, counts_json, data_origin, created_at)
           VALUES (?, ?, ?, ?, ?, ?, 'inspected', '{}', ?, ?)""",
        (batch_id, workbook_id, cfg["period"]["year"], cfg["period"]["month"],
         json.dumps(cfg, ensure_ascii=False), chash, wb_row["data_origin"], now_iso()),
    )
    repo.audit(conn, user_id, "ri.batch.created", "ri_batch", batch_id, {"config_hash": chash, "period": cfg["period"]})
    conn.commit()
    return conn.execute("SELECT * FROM ri_import_batches WHERE id = ?", (batch_id,)).fetchone(), False


def get_batch(conn, batch_id: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM ri_import_batches WHERE id = ?", (batch_id,)).fetchone()
    if row is None:
        raise WorkbookError("BATCH_NOT_FOUND", "Import batch not found.", 404)
    return row


# ------------------------------------------------------------------------------------ staging
def stage_batch(conn: sqlite3.Connection, settings: Settings, user_id: str | None, batch_id: str):
    """Validate + normalise + store. Re-running on validated/confirmed batches is a no-op (replayed)."""
    batch = get_batch(conn, batch_id)
    if batch["status"] in ("validated", "confirmed"):
        return batch, True
    wb_row = conn.execute("SELECT * FROM ri_workbooks WHERE id = ?", (batch["workbook_id"],)).fetchone()
    cfg = json.loads(batch["config_json"])
    raw = _workbook_bytes(settings, wb_row)
    try:
        _clear_staged(conn, batch_id)
        counts = _stage(conn, settings, batch, cfg, raw)
        conn.execute("UPDATE ri_import_batches SET status='validated', counts_json=?, validated_at=? WHERE id=?",
                     (json.dumps(counts, ensure_ascii=False), now_iso(), batch_id))
        repo.audit(conn, user_id, "ri.batch.validated", "ri_batch", batch_id,
                   {"rows": {k: v["rows_read"] for k, v in counts["sheets"].items()}, "issues": counts["issues"]})
        conn.commit()
    except Exception as exc:
        conn.rollback()
        message = exc.message if isinstance(exc, WorkbookError) else exc.__class__.__name__
        conn.execute("UPDATE ri_import_batches SET status='failed', counts_json=? WHERE id=?",
                     (json.dumps({"error": message}), batch_id))
        conn.commit()
        raise
    return get_batch(conn, batch_id), False


def _clear_staged(conn: sqlite3.Connection, batch_id: str) -> None:
    for sql in (
        "DELETE FROM ri_calc_result_inputs WHERE result_id IN (SELECT id FROM ri_calc_results WHERE batch_id = ?)",
        "DELETE FROM ri_calc_results WHERE batch_id = ?",
        "DELETE FROM ri_reconciliation_checks WHERE batch_id = ?",
        "DELETE FROM ri_calc_runs WHERE batch_id = ?",
        "DELETE FROM ri_sales_facts WHERE batch_id = ?",
        "DELETE FROM ri_raw_rows WHERE batch_id = ?",
        "DELETE FROM ri_visitor_assignments WHERE batch_id = ?",
        "DELETE FROM ri_mapping_issues WHERE batch_id = ?",
        "DELETE FROM ri_targets WHERE batch_id = ?",
        "DELETE FROM ri_workbook_references WHERE batch_id = ?",
        "DELETE FROM ri_branch_group_members WHERE scheme_id IN (SELECT id FROM ri_branch_group_schemes WHERE code LIKE ? || ':%')",
        "DELETE FROM ri_branch_group_schemes WHERE code LIKE ? || ':%'",
    ):
        conn.execute(sql, (batch_id,))


def _stage(conn, settings, batch, cfg, raw: bytes) -> dict[str, Any]:
    wb = inspector.open_workbook(raw)
    try:
        batch_id = batch["id"]
        issues = Issues()
        dims = Dims(conn, settings.pseudonym_key)
        month_name = fold_text(P.JALALI_MONTHS[cfg["period"]["month"] - 1])
        sheets = cfg["sheets"]
        counts: dict[str, Any] = {"sheets": {}}

        cg_lookup = _stage_customer_groups(wb, sheets.get("customer_groups"), dims, issues)
        factors = _stage_factors(wb, sheets.get("box_conversion"), issues)
        group_status = _stage_branch_groups(conn, wb, sheets.get("branch_groups"), batch_id, dims)
        roster, roster_counts = _stage_roster(conn, wb, sheets.get("roster"), batch_id, dims, issues, settings.pseudonym_key)
        counts["roster"] = roster_counts
        ctx = {"conn": conn, "dims": dims, "issues": issues, "batch_id": batch_id, "period": cfg["period"],
               "month_name": month_name, "roster": roster, "cg_lookup": cg_lookup, "factors": factors,
               "branch_groups": group_status, "key": settings.pseudonym_key}
        for role in ("sales_primary", "sales_derived"):
            ws = inspector.find_sheet(wb, sheets.get(role))
            if ws is None:
                continue
            counts["sheets"][role] = {"sheet": sheets[role], **_stage_sales_sheet(ctx, role, sheets[role], ws)}
        if "sales_primary" not in counts["sheets"]:
            raise WorkbookError("WORKBOOK_STRUCTURE", "Primary sales sheet is missing.")
        counts["targets"] = _stage_manager_targets(conn, wb, sheets.get("manager_efes"), batch_id, dims, issues, month_name)
        # sku factors (only when the code has exactly one distinct factor)
        for code, vals in factors.items():
            sku_id = dims.cache["sku"].get(code)
            if sku_id is not None and len(vals) == 1:
                conn.execute("UPDATE ri_skus SET carton_factor = ? WHERE id = ?", (decimal_text(next(iter(vals))), sku_id))
        dims.flush_variants(issues)
        for (itype, ref), item in issues.items.items():
            conn.execute(
                "INSERT INTO ri_mapping_issues (batch_id, issue_type, severity, entity_ref, detail_json) VALUES (?, ?, ?, ?, ?)",
                (batch_id, itype, item["severity"], ref, json.dumps(item["detail"], ensure_ascii=False)),
            )
        counts["issues"] = issues.counts()
        return counts
    finally:
        wb.close()


# -- lookups ---------------------------------------------------------------------------------
def _stage_customer_groups(wb, sheet_name, dims: Dims, issues: Issues) -> dict[str, str | None]:
    out: dict[str, str | None] = {}
    ws = inspector.find_sheet(wb, sheet_name)
    if ws is None:
        return out
    cols = P.match_headers(inspector.header_row_cells(ws, 1), P.CUSTOMER_GROUP_FIELDS)
    if "customer_group" not in cols or "main_group" not in cols:
        return out
    main_map = {fold_text(k): v for k, v in P.MAIN_GROUPS.items()}
    for _n, cells in _iter_rows(ws, 1):
        name = source_text(_cell(cells, cols, "customer_group"))
        label = fold_text(_cell(cells, cols, "main_group"))
        if not name:
            continue
        main = main_map.get(label)
        out[fold_text(name)] = main
        dims.cgroup(name, main)
        if main is None:
            issues.add("customer_group_main_unmapped", "warning", fold_text(name), main_label=source_text(_cell(cells, cols, "main_group")))
    return out


_CODE_RE = re.compile(r"^[A-Za-z]{2,}_[\w\-]+$")


def _stage_factors(wb, sheet_name, issues: Issues) -> dict[str, set[Decimal]]:
    out: dict[str, set[Decimal]] = defaultdict(set)
    ws = inspector.find_sheet(wb, sheet_name)
    if ws is None:
        return out
    cols = P.match_headers(inspector.header_row_cells(ws, 1), P.FACTOR_FIELDS)
    if not {"col_a", "col_b", "factor"} <= set(cols):
        return out
    swapped = 0
    for _n, cells in _iter_rows(ws, 1):
        a, b = source_text(_cell(cells, cols, "col_a")), source_text(_cell(cells, cols, "col_b"))
        code = a if _CODE_RE.match(a) else (b if _CODE_RE.match(b) else "")
        if not code:
            continue
        if code == b:
            swapped += 1
        factor = parse_decimal(_cell(cells, cols, "factor"))
        if factor is not None:
            out[fold_text(code).upper()].add(factor)
    if swapped:
        issues.add("factor_header_swapped", "info", "box_conversion", rows=swapped)
    for code, vals in out.items():
        if len(vals) > 1:
            issues.add("factor_duplicate_code", "warning", code, factors=sorted(decimal_text(v) for v in vals))
    return out


def _stage_branch_groups(conn, wb, sheet_name, batch_id, dims: Dims) -> dict[str, set[str]]:
    """Two lookup schemes from the sheet (the audit found four coexisting definitions; all UNCONFIRMED)."""
    covered: dict[str, set[str]] = {"group1": set(), "group2": set()}
    ws = inspector.find_sheet(wb, sheet_name)
    if ws is None:
        return covered
    cols = P.match_headers(inspector.header_row_cells(ws, 1), P.BRANCH_GROUP_FIELDS)
    if "branch" not in cols:
        return covered
    titles = {"group1": "Lookup column «گروه»", "group2": "Lookup column «گروه 2»"}
    scheme_ids = {}
    for key, title in titles.items():
        if key in cols:
            scheme_ids[key] = conn.execute(
                "INSERT INTO ri_branch_group_schemes (code, title, source) VALUES (?, ?, ?)",
                (f"{batch_id}:{key}", title, f"sheet:{sheet_name}"),
            ).lastrowid
    for _n, cells in _iter_rows(ws, 1):
        branch = source_text(_cell(cells, cols, "branch"))
        if not branch or is_error_cell(branch):
            continue
        branch_id = dims.branch(branch)
        for key, scheme_id in scheme_ids.items():
            group = _code_text(_cell(cells, cols, key))
            if group:
                conn.execute(
                    "INSERT OR REPLACE INTO ri_branch_group_members (scheme_id, branch_id, group_code) VALUES (?, ?, ?)",
                    (scheme_id, branch_id, group),
                )
                covered[key].add(fold_text(branch))
    return covered


# -- roster ----------------------------------------------------------------------------------
def _stage_roster(conn, wb, sheet_name, batch_id, dims: Dims, issues: Issues, key: str):
    roster: dict[str, int] = {}
    stats = {"rows": 0, "assignments": 0, "employees": 0, "employees_with_multiple_assignments": 0, "without_employee": 0}
    ws = inspector.find_sheet(wb, sheet_name)
    if ws is None:
        return roster, stats
    cols = P.match_headers(inspector.header_row_cells(ws, 1), P.ROSTER_FIELDS)
    missing = [f for f in P.ROSTER_REQUIRED if f not in cols]
    if missing:
        raise WorkbookError("WORKBOOK_STRUCTURE", f"Roster sheet is missing columns: {', '.join(missing)}.")
    per_employee: dict[int, list[str]] = defaultdict(list)
    head_missing: dict[str, int] = defaultdict(int)
    type_case = type_mismatch = 0
    for _n, cells in _iter_rows(ws, 1):
        stats["rows"] += 1
        vkey = source_text(_cell(cells, cols, "visitor"))
        branch = source_text(_cell(cells, cols, "branch"))
        if not vkey or is_error_cell(vkey) or not branch:
            continue
        vnorm = fold_text(vkey)
        vps = pseudonym("visitor", vnorm, key)
        if vnorm in roster:
            issues.add("roster_duplicate_visitor", "error", vps)
            continue
        branch_id = dims.branch(branch)
        bnorm = fold_text(branch)
        line_label = source_text(_cell(cells, cols, "sales_line"))
        line_id = dims.line(line_label) if line_label else None
        code = _code_text(_cell(cells, cols, "personnel_code"))
        employee_id = None
        if _blank_code(code):
            issues.add("employee_code_missing", "warning", vps)
            stats["without_employee"] += 1
        else:
            employee_id = dims.employee(f"{fold_text(code)}|{bnorm}", code)
        letter_key = vkey.rsplit("_", 1)[-1] if "_" in vkey else ""
        seller_norm = letter_key.upper() if letter_key.upper() in {"R", "W", "V", "H"} else None
        if letter_key and (letter_key != letter_key.upper() or seller_norm is None):
            type_case += 1
        type_letter = source_text(_cell(cells, cols, "type_letter"))
        if type_letter and letter_key and type_letter != letter_key:
            type_mismatch += 1
        sup, head = _code_text(_cell(cells, cols, "supervisor_code")), _code_text(_cell(cells, cols, "head_code"))
        if _blank_code(head):
            head_missing[bnorm] += 1
        st = parse_decimal(_cell(cells, cols, "st"))
        cur = conn.execute(
            """INSERT INTO ri_visitor_assignments
               (batch_id, visitor_key_source, visitor_key_norm, pseudonym, employee_id, branch_id, sales_line_id,
                seller_type_source, seller_type_norm, supervisor_code, head_code, is_active, hire_date_source)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (batch_id, vkey, vnorm, vps, employee_id, branch_id, line_id,
             source_text(_cell(cells, cols, "seller_type")) or None, seller_norm,
             None if _blank_code(sup) else sup, None if _blank_code(head) else head,
             None if st is None else int(st), source_text(_cell(cells, cols, "hire_date")) or None),
        )
        roster[vnorm] = cur.lastrowid
        stats["assignments"] += 1
        if employee_id is not None:
            per_employee[employee_id].append(seller_norm or "?")
    stats["employees"] = len(per_employee)
    for emp_id, types in per_employee.items():
        if len(types) > 1:
            stats["employees_with_multiple_assignments"] += 1
            ref = conn.execute("SELECT pseudonym FROM ri_employees WHERE id = ?", (emp_id,)).fetchone()["pseudonym"]
            issues.add("shared_personnel_code", "info" if set(types) == {"V"} else "warning", ref,
                       assignments=len(types), seller_types=sorted(set(types)))
    for bnorm, n in head_missing.items():
        issues.add("head_missing", "warning", f"branch:{bnorm}", rows=n)
    if type_case:
        issues.add("seller_type_case", "info", "roster", rows=type_case)
    if type_mismatch:
        issues.add("seller_type_mismatch", "info", "roster", rows=type_mismatch)
    return roster, stats


# -- sales -----------------------------------------------------------------------------------
def _stage_sales_sheet(ctx: dict[str, Any], role: str, sheet_name: str, ws) -> dict[str, Any]:
    conn, dims, issues, batch_id = ctx["conn"], ctx["dims"], ctx["issues"], ctx["batch_id"]
    header = inspector.header_row_cells(ws, 1)
    cols = P.match_headers(header, P.SALES_FIELDS)
    missing = [f for f in P.SALES_REQUIRED if f not in cols]
    if missing:
        raise WorkbookError("WORKBOOK_STRUCTURE", f"Sheet '{sheet_name}' is missing columns: {', '.join(missing)}.")
    labels = [source_text(c) for c in header]
    period = ctx["period"]

    parsed: list[dict[str, Any]] = []
    for n, cells in _iter_rows(ws, 1):
        raw_json = json.dumps({labels[i]: _jsonable(c) for i, c in enumerate(cells) if i < len(labels) and labels[i] and c is not None},
                              ensure_ascii=False, sort_keys=True)
        rec: dict[str, Any] = {"n": n, "raw_json": raw_json, "row_hash": hashlib.sha256(raw_json.encode()).hexdigest(), "errors": []}
        text = {f: source_text(_cell(cells, cols, f)) for f in P.BUSINESS_KEY_FIELDS}
        for f in P.BUSINESS_KEY_FIELDS:
            value = _cell(cells, cols, f)
            if is_error_cell(value):
                rec["errors"].append("E_ERROR_CELL")
            elif not text[f]:
                rec["errors"].append("E_REQUIRED")
        if not rec["errors"] and fold_text(text["month"]) != ctx["month_name"]:
            rec["errors"].append("E_PERIOD")
        net = parse_decimal(_cell(cells, cols, "net"))
        gross_cell = _cell(cells, cols, "gross")
        gross = parse_decimal(gross_cell)
        if net is None:
            rec["errors"].append("E_NET")
        if gross is None and gross_cell not in (None, ""):
            rec["errors"].append("E_GROSS")
        inv = parse_decimal(_cell(cells, cols, "invoice_count"))
        rec.update(text=text, net=net, gross=gross, invoice=None if inv is None else int(inv),
                   sku_name=source_text(_cell(cells, cols, "sku_name")) or None)
        if not rec["errors"]:
            rec["key"] = _sha(*[fold_text(text[f]) if f != "sales_line" else P.line_code(text[f]) for f in P.BUSINESS_KEY_FIELDS])
        parsed.append(rec)

    # raw layer
    conn.executemany(
        "INSERT INTO ri_raw_rows (batch_id, sheet, row_number, row_hash, raw_json) VALUES (?, ?, ?, ?, ?)",
        [(batch_id, sheet_name, r["n"], r["row_hash"], r["raw_json"]) for r in parsed],
    )
    raw_ids = {r["row_number"]: r["id"] for r in conn.execute(
        "SELECT id, row_number FROM ri_raw_rows WHERE batch_id = ? AND sheet = ?", (batch_id, sheet_name))}

    # duplicate business keys: deterministic ordinals independent of row order (audit §D: 5 keys)
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in parsed:
        if not r["errors"]:
            groups[r["key"]].append(r)
    for rows in groups.values():
        rows.sort(key=lambda r: (r["net"], r["gross"] if r["gross"] is not None else Decimal(0), r["invoice"] or 0, r["n"]))
        for i, r in enumerate(rows):
            r["ordinal"] = i

    stats: dict[str, Any] = {"rows_read": len(parsed), "valid": 0, "rejected": 0, "rejected_by_code": defaultdict(int),
                             "distinct_keys": len(groups), "duplicate_keys": 0, "duplicate_key_rows": 0}
    gross_sum, net_sum, invoice_sum = Decimal(0), Decimal(0), 0
    by_brand: dict[str, dict[str, Any]] = {}
    unmapped_visitors: dict[str, int] = defaultdict(int)
    for rows in groups.values():
        if len(rows) > 1:
            stats["duplicate_keys"] += 1
            stats["duplicate_key_rows"] += len(rows) - 1

    fact_rows = []
    for r in parsed:
        if r["errors"]:
            stats["rejected"] += 1
            for code in dict.fromkeys(r["errors"]):
                stats["rejected_by_code"][code] += 1
            fact_rows.append((batch_id, sheet_name, raw_ids[r["n"]], f"rej:{r['n']}", 0, period["year"], period["month"],
                              None, None, None, None, None, None, None, None,
                              decimal_text(r["gross"]), decimal_text(r["net"]), r["invoice"], "rejected",
                              json.dumps(list(dict.fromkeys(r["errors"])))))
            continue
        t = r["text"]
        vnorm = fold_text(t["visitor"])
        assignment_id = ctx["roster"].get(vnorm)
        if assignment_id is None and ctx["roster"]:
            unmapped_visitors[pseudonym("visitor", vnorm, ctx["key"])] += 1
        cg_norm = fold_text(t["customer_group"])
        if ctx["cg_lookup"] and cg_norm not in ctx["cg_lookup"]:
            issues.add("customer_group_unmapped", "warning", cg_norm)
        bnorm = fold_text(t["branch"])
        if ctx["branch_groups"]["group1"] and bnorm not in ctx["branch_groups"]["group1"]:
            issues.add("branch_group_missing", "warning", bnorm)
        sku_norm = fold_text(t["sku_code"]).upper()
        if ctx["factors"] and sku_norm not in ctx["factors"]:
            issues.add("sku_factor_missing", "warning", sku_norm)
        flags = ["duplicate_key"] if len(groups[r["key"]]) > 1 else []
        brand_id = dims.brand(t["brand"])
        fact_rows.append((
            batch_id, sheet_name, raw_ids[r["n"]], r["key"], r["ordinal"], period["year"], period["month"],
            dims.branch(t["branch"]), assignment_id, vnorm, dims.cgroup(t["customer_group"]), dims.line(t["sales_line"]),
            dims.customer(t["customer"]), brand_id, dims.sku(t["sku_code"], r["sku_name"]),
            decimal_text(r["gross"]), decimal_text(r["net"]), r["invoice"], "valid", json.dumps(flags),
        ))
        stats["valid"] += 1
        net_sum += r["net"]
        gross_sum += r["gross"] or Decimal(0)
        invoice_sum += r["invoice"] or 0
        b = by_brand.setdefault(fold_text(t["brand"]), {"rows": 0, "net": Decimal(0)})
        b["rows"] += 1
        b["net"] += r["net"]
    conn.executemany(
        """INSERT INTO ri_sales_facts
           (batch_id, source_sheet, raw_row_id, business_key_hash, dup_ordinal, period_year, period_month,
            branch_id, visitor_assignment_id, visitor_key_norm, customer_group_id, sales_line_id,
            customer_id, brand_id, sku_id, gross_cartons, net_cartons, invoice_count, status, issues_json)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        fact_rows,
    )
    for vref, n in unmapped_visitors.items():
        issues.add("visitor_not_in_roster", "warning", vref, rows=n)
    stats["rejected_by_code"] = dict(stats["rejected_by_code"])
    stats.update(gross_cartons=decimal_text(gross_sum), net_cartons=decimal_text(net_sum), invoice_count=invoice_sum,
                 by_brand={k: {"rows": v["rows"], "net": decimal_text(v["net"])} for k, v in by_brand.items()})
    return stats


# -- manager targets / workbook references ---------------------------------------------------
def _stage_manager_targets(conn, wb, sheet_name, batch_id, dims: Dims, issues: Issues, month_name: str) -> dict[str, Any]:
    stats = {"rows": 0, "targets": 0, "references": 0}
    ws = inspector.find_sheet(wb, sheet_name)
    if ws is None:
        return stats
    cols = P.match_headers(inspector.header_row_cells(ws, P.MANAGER_HEADER_ROW), P.MANAGER_FIELDS)
    if not {"brand", "branch", "line", "target"} <= set(cols):
        return stats
    seen: set[tuple[int, str]] = set()
    for n, cells in _iter_rows(ws, P.MANAGER_HEADER_ROW):
        branch = source_text(_cell(cells, cols, "branch"))
        brand_label = fold_text(_cell(cells, cols, "brand"))
        if not branch or not brand_label:
            continue
        stats["rows"] += 1
        if "month" in cols and fold_text(_cell(cells, cols, "month")) != month_name:
            issues.add("target_other_period", "info", "manager_sheet")
            continue
        brand_id = dims.brand(P.BRAND_ALIASES.get(brand_label, brand_label).upper() if brand_label in P.BRAND_ALIASES else brand_label)
        level_text = fold_text(_cell(cells, cols, "level"))
        org_level = {"": "branch_manager", "مدیر": "branch_manager", "مدیرکل": "general_manager"}.get(level_text, f"other:{level_text}")
        codes = P.line_group_codes(_cell(cells, cols, "line"))
        entity_key = f"{fold_text(branch)}|{'-'.join(sorted(codes))}"
        if (brand_id, entity_key) in seen:
            issues.add("target_duplicate_entity", "warning", entity_key)
            continue
        seen.add((brand_id, entity_key))
        target = parse_decimal(_cell(cells, cols, "target"))
        if target is None:
            issues.add("target_missing", "warning", entity_key)
            continue
        extra = {
            "steps": [decimal_text(parse_decimal(_cell(cells, cols, f"step{i}"))) for i in range(1, 5)],
            "relief": decimal_text(parse_decimal(_cell(cells, cols, "relief"))),
            "workbook_row": n,
        }
        conn.execute(
            """INSERT INTO ri_targets (batch_id, brand_id, org_level, entity_key, target_cartons, source, status, extra_json)
               VALUES (?, ?, ?, ?, ?, ?, 'UNCONFIRMED', ?)""",
            (batch_id, brand_id, org_level, entity_key, decimal_text(target), f"workbook_hardcoded:{sheet_name}", json.dumps(extra)),
        )
        stats["targets"] += 1
        brand_code = conn.execute("SELECT norm_key FROM ri_brands WHERE id = ?", (brand_id,)).fetchone()["norm_key"]
        for suffix, field_name, unit, desc in (
            ("sales", "definitive_sales", "cartons", "Workbook «فروش قطعی» (definitive sales)"),
            ("achievement", "achievement", "ratio", "Workbook «تحقق قطعی» (achievement)"),
            ("reward", "reward", "rials", "Workbook «مبلغ» (reward, as reported)"),
        ):
            value = parse_decimal(_cell(cells, cols, field_name))
            if value is not None:
                conn.execute(
                    """INSERT INTO ri_workbook_references (batch_id, ref_code, description, brand_code, org_level, value, unit, source_sheet)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (batch_id, f"mgr|{brand_code}|{entity_key}|{suffix}", desc, brand_code, org_level, decimal_text(value), unit, sheet_name),
                )
                stats["references"] += 1
    return stats


# ------------------------------------------------------------------------------- preview/confirm
def confirm_batch(conn: sqlite3.Connection, user_id: str | None, batch_id: str):
    batch = get_batch(conn, batch_id)
    if batch["status"] == "confirmed":
        return batch, True
    if batch["status"] != "validated":
        raise WorkbookError("BATCH_NOT_VALIDATED", "Validate the batch before confirming it.", 409)
    conn.execute("UPDATE ri_import_batches SET status='confirmed', confirmed_at=? WHERE id=?", (now_iso(), batch_id))
    repo.audit(conn, user_id, "ri.batch.confirmed", "ri_batch", batch_id, {"counts": json.loads(batch["counts_json"]).get("issues", {})})
    conn.commit()
    return get_batch(conn, batch_id), False


def batch_dict(conn: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
    wb = conn.execute("SELECT file_name, sha256, size_bytes FROM ri_workbooks WHERE id = ?", (row["workbook_id"],)).fetchone()
    return {
        "id": row["id"],
        "workbook": {"id": row["workbook_id"], "file_name": wb["file_name"], "sha256": wb["sha256"], "size_bytes": wb["size_bytes"]},
        "period": {"calendar": "jalali", "year": row["period_year"], "month": row["period_month"],
                   "label": P.JALALI_MONTHS[row["period_month"] - 1]},
        "config": json.loads(row["config_json"]),
        "status": row["status"],
        "data_origin": row["data_origin"],
        "counts": json.loads(row["counts_json"]),
        "created_at": row["created_at"],
        "validated_at": row["validated_at"],
        "confirmed_at": row["confirmed_at"],
    }


def preview(conn: sqlite3.Connection, settings: Settings, batch_id: str, *, limit: int = 15, reject_limit: int = 60) -> dict[str, Any]:
    batch = get_batch(conn, batch_id)
    out = batch_dict(conn, batch)
    if batch["status"] == "inspected":
        return {**out, "valid_rows": [], "rejected_rows": [], "issues": []}
    basis_sheet = json.loads(batch["config_json"])["sheets"][json.loads(batch["config_json"])["carton_basis"]]
    valid = conn.execute(
        """SELECT f.id, rr.row_number, f.source_sheet, b.source_value AS branch, l.norm_key AS line, br.norm_key AS brand,
                  s.code AS sku, c.pseudonym AS customer, f.visitor_key_norm, f.gross_cartons, f.net_cartons,
                  f.invoice_count, f.issues_json
           FROM ri_sales_facts f
           JOIN ri_raw_rows rr ON rr.id = f.raw_row_id
           LEFT JOIN ri_branches b ON b.id = f.branch_id LEFT JOIN ri_sales_lines l ON l.id = f.sales_line_id
           LEFT JOIN ri_brands br ON br.id = f.brand_id LEFT JOIN ri_skus s ON s.id = f.sku_id
           LEFT JOIN ri_customers c ON c.id = f.customer_id
           WHERE f.batch_id = ? AND f.source_sheet = ? AND f.status = 'valid' ORDER BY rr.row_number LIMIT ?""",
        (batch_id, basis_sheet, limit),
    ).fetchall()
    rejected = conn.execute(
        """SELECT rr.row_number, f.source_sheet, f.issues_json FROM ri_sales_facts f JOIN ri_raw_rows rr ON rr.id = f.raw_row_id
           WHERE f.batch_id = ? AND f.status = 'rejected' ORDER BY f.source_sheet, rr.row_number LIMIT ?""",
        (batch_id, reject_limit),
    ).fetchall()
    issues = conn.execute(
        """SELECT issue_type, severity, COUNT(*) AS entities FROM ri_mapping_issues WHERE batch_id = ?
           GROUP BY issue_type, severity ORDER BY severity DESC, issue_type""", (batch_id,)).fetchall()
    return {
        **out,
        "basis_sheet": basis_sheet,
        "valid_rows": [
            {"row_number": r["row_number"], "source_sheet": r["source_sheet"], "branch": r["branch"], "sales_line": r["line"],
             "brand": r["brand"], "sku": r["sku"], "customer": r["customer"],
             "visitor": pseudonym("visitor", r["visitor_key_norm"], settings.pseudonym_key),
             "gross_cartons": r["gross_cartons"], "net_cartons": r["net_cartons"], "invoice_count": r["invoice_count"],
             "flags": json.loads(r["issues_json"])}
            for r in valid
        ],
        "rejected_rows": [
            {"row_number": r["row_number"], "source_sheet": r["source_sheet"],
             "errors": [{"code": c, "label": ERROR_LABELS.get(c, c)} for c in json.loads(r["issues_json"])]}
            for r in rejected
        ],
        "issues": [{"type": r["issue_type"], "label": ISSUE_LABELS.get(r["issue_type"], r["issue_type"]),
                    "severity": r["severity"], "entities": r["entities"]} for r in issues],
    }
