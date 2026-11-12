"""Generate a SAMPLE sales workbook for the demo (`python -m app.sample_sales`).

Every number and identifier here is fake data, shaped to exercise the import:
valid rows, a duplicate inside the file, and an unmapped visitor id. It is not a
business template — the real contract arrives with OD-03.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from app.config import REPO_ROOT

HEADERS = ["external_id", "user_external_id", "sale_date", "sku_code", "quantity", "amount"]

SAMPLE_ROWS = [
    ["S-1001", "VIS-001", "2026-11-01", "SKU-101", 3, 4_500_000],
    ["S-1002", "VIS-002", "2026-11-02", "SKU-102", 1, 2_750_000],
    ["S-1003", "VIS-003", "2026-11-02", "SKU-103", 5, 8_000_000],
    ["S-1004", "VIS-001", "2026-11-03", "SKU-101", 2, 1_200_000],
    ["S-1003", "VIS-003", "2026-11-02", "SKU-103", 5, 8_000_000],  # duplicate in file
    ["S-1005", "VIS-999", "2026-11-03", "SKU-104", 1, 900_000],  # unmapped visitor
]


def sample_workbook_bytes() -> bytes:
    """The same SAMPLE workbook as the CLI, for the admin download route."""
    import io

    from openpyxl import Workbook

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "sales-sample"
    sheet.append(HEADERS)
    for row in SAMPLE_ROWS:
        sheet.append(row)
    sheet.freeze_panes = "A2"
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def build_sample_workbook(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(sample_workbook_bytes())
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.sample_sales")
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "var" / "sales-sample.xlsx",
        help="output path (default: var/sales-sample.xlsx)",
    )
    args = parser.parse_args(argv)
    path = build_sample_workbook(args.out)
    print(f"sample workbook written: {path} ({len(SAMPLE_ROWS)} rows, SAMPLE data)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
