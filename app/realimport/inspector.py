"""Read-only workbook inspection: sheet inventory, role detection, header matching.

Never returns cell values from data rows - only sheet names, sizes, header labels (not personal
data) and which required columns were found.
"""

from __future__ import annotations

import io
from typing import Any

from openpyxl import load_workbook

from app.realimport import profile as P
from app.realimport.normalize import fold_text


class WorkbookError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 422):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def open_workbook(raw: bytes):
    try:
        return load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    except Exception as exc:  # noqa: BLE001 - openpyxl raises many types for corrupt files
        raise WorkbookError("INVALID_WORKBOOK", "The file is not a readable .xlsx workbook.") from exc


def find_sheet(wb, wanted: str | None):
    """Sheet by name, tolerant to spaces and Arabic/Persian letter variants."""
    if not wanted:
        return None
    key = fold_text(wanted)
    for ws in wb.worksheets:
        if fold_text(ws.title) == key:
            return ws
    return None


def header_row_cells(ws, row: int = 1) -> list[Any]:
    for i, cells in enumerate(ws.iter_rows(min_row=row, max_row=row, values_only=True), start=row):
        if i == row:
            return list(cells)
    return []


def _fields_for(role: str):
    return {
        "sales_primary": (P.SALES_FIELDS, P.SALES_REQUIRED, 1),
        "sales_derived": (P.SALES_FIELDS, P.SALES_REQUIRED, 1),
        "roster": (P.ROSTER_FIELDS, P.ROSTER_REQUIRED, 1),
        "box_conversion": (P.FACTOR_FIELDS, ("col_a", "col_b", "factor"), 1),
        "branch_groups": (P.BRANCH_GROUP_FIELDS, ("branch", "group1"), 1),
        "customer_groups": (P.CUSTOMER_GROUP_FIELDS, ("customer_group", "main_group"), 1),
        "manager_efes": (P.MANAGER_FIELDS, ("brand", "branch", "line", "target"), P.MANAGER_HEADER_ROW),
    }.get(role)


def inspect_workbook(raw: bytes, config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Sheet inventory + role detection. ``problems`` lists blocking issues for the chosen sheets."""
    cfg = P.normalise_config(config)
    wb = open_workbook(raw)
    try:
        sheets = []
        for ws in wb.worksheets:
            sheets.append(
                {
                    "name": ws.title,
                    "state": getattr(ws, "sheet_state", "visible"),
                    "rows": ws.max_row,
                    "columns": ws.max_column,
                }
            )
        names = {fold_text(s["name"]) for s in sheets}
        roles: dict[str, Any] = {}
        problems: list[str] = []
        for role, sheet_name in cfg["sheets"].items():
            ws = find_sheet(wb, sheet_name)
            spec = _fields_for(role)
            entry: dict[str, Any] = {"sheet": sheet_name, "found": ws is not None, "columns_found": [], "columns_missing": []}
            if ws is not None and spec is not None:
                fields, required, header_row = spec
                matched = P.match_headers(header_row_cells(ws, header_row), fields)
                entry["header_row"] = header_row
                entry["columns_found"] = sorted(matched)
                entry["columns_missing"] = [f for f in required if f not in matched]
            roles[role] = entry
            if ws is None and role in ("sales_primary",):
                problems.append(f"Required sheet '{sheet_name}' ({role}) was not found.")
            elif entry["columns_missing"] and role in ("sales_primary", "sales_derived", "roster"):
                problems.append(f"Sheet '{sheet_name}' is missing columns: {', '.join(entry['columns_missing'])}.")
        origin = "synthetic" if fold_text(P.SYNTHETIC_MARKER_SHEET) in names else "real"
        return {"sheets": sheets, "roles": roles, "problems": problems, "data_origin": origin, "sheet_count": len(sheets)}
    finally:
        wb.close()
