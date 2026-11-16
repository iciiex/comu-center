"""Kiloos management-demo profile: hierarchy seed, SAMPLE workbook, reset/load CLI.

Everything generated here is SYNTHETIC and tagged ``sample``. It is shaped like the workbook the
business described (brands EFES / MATADOR, branches, supervisors, representatives, targets,
periods) but contains NO real Kiloos sales, employees or customers, and it is NOT evidence that
any business formula is verified. The real operational workbook replaces it through the same
import pipeline (see ``sales.HEADER_ALIASES``).

CLI (inside the container or a venv)::

    python -m app.kiloos_demo reset          # wipe DB, re-seed hierarchy + rules (deterministic)
    python -m app.kiloos_demo load-sample    # upload + process the SAMPLE workbook as admin
    python -m app.kiloos_demo workbook --out var/kiloos-sample-sales.xlsx
"""

from __future__ import annotations

import argparse
import io
import random
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

NAMESPACE = uuid.UUID("6d1b3a52-0a47-4d2e-9a64-5f2a8f1c0b11")
PERIOD = "2026-11"

BRANDS = [("EFES", "EFES (sample)"), ("MATADOR", "Matador (sample)")]
BRANCHES = [("BR-TEH", "Tehran Branch (sample)"), ("BR-ISF", "Isfahan Branch (sample)")]

# (employee_code, full_name, mobile, role, position, title, branch, supervisor_code, manager_code)
# Names are fictional. The first five mobiles belong to the base prototype users.
PEOPLE = [
    ("MGT-01", "کیوان صادقی", "09120000100", "operator", "management", "Head of Sales", None, None, None),
    ("BM-01", "پرستو نوری", "09120000101", "operator", "branch_manager", "Branch Manager", "BR-TEH", None, None),
    ("BM-02", "بهرام فرهادی", "09120000102", "operator", "branch_manager", "Branch Manager", "BR-ISF", None, None),
    ("SUP-01", "حسین کریمی", "09120000004", "operator", "supervisor", "Supervisor", "BR-TEH", None, "BM-01"),
    ("SUP-02", "لیلا مرادی", "09120000103", "operator", "supervisor", "Supervisor", "BR-TEH", None, "BM-01"),
    ("SUP-03", "رضا اکبری", "09120000104", "operator", "supervisor", "Supervisor", "BR-ISF", None, "BM-02"),
    ("VIS-001", "سارا محمدی", "09120000001", "visitor", "rep", "Sales Representative", "BR-TEH", "SUP-01", "BM-01"),
    ("VIS-002", "امیر رضایی", "09120000002", "visitor", "rep", "Sales Representative", "BR-TEH", "SUP-01", "BM-01"),
    ("VIS-004", "دانیال کیانی", "09120000105", "visitor", "rep", "Sales Representative", "BR-TEH", "SUP-01", "BM-01"),
    ("VIS-003", "مریم کاظمی", "09120000003", "visitor", "rep", "Sales Representative", "BR-TEH", "SUP-02", "BM-01"),
    ("VIS-005", "الهام صالحی", "09120000106", "visitor", "rep", "Sales Representative", "BR-TEH", "SUP-02", "BM-01"),
    ("VIS-006", "پویا عباسی", "09120000107", "visitor", "rep", "Sales Representative", "BR-ISF", "SUP-03", "BM-02"),
    ("VIS-007", "ندا فرهمند", "09120000108", "visitor", "rep", "Sales Representative", "BR-ISF", "SUP-03", "BM-02"),
    ("VIS-008", "سینا یگانه", "09120000109", "visitor", "rep", "Sales Representative", "BR-ISF", "SUP-03", "BM-02"),
]

# Target attainment per rep for the SAMPLE workbook (fraction of monthly target, all brands).
# The mission gate is 80% (PROPOSED), so some reps are eligible and some deliberately are not.
ATTAINMENT = {
    "VIS-001": 1.12,
    "VIS-002": 0.92,
    "VIS-003": 0.68,
    "VIS-004": 0.85,
    "VIS-005": 0.55,
    "VIS-006": 1.03,
    "VIS-007": 0.76,
    "VIS-008": 0.88,
}
# Monthly target per brand (Rials) for each rep: (EFES, MATADOR). Synthetic.
TARGETS = {
    "VIS-001": (260_000_000, 180_000_000),
    "VIS-002": (240_000_000, 170_000_000),
    "VIS-003": (230_000_000, 150_000_000),
    "VIS-004": (210_000_000, 160_000_000),
    "VIS-005": (200_000_000, 140_000_000),
    "VIS-006": (250_000_000, 170_000_000),
    "VIS-007": (220_000_000, 150_000_000),
    "VIS-008": (225_000_000, 155_000_000),
}
SKUS = {"EFES": ["EFS-330", "EFS-500", "EFS-PACK"], "MATADOR": ["MTD-250", "MTD-1L", "MTD-PACK"]}


def _uid(code: str) -> str:
    return str(uuid.uuid5(NAMESPACE, code))


def _iso() -> str:
    return datetime.now(tz=UTC).isoformat(timespec="seconds")


def seed_kiloos(conn: sqlite3.Connection) -> None:
    """Add the sample hierarchy on top of the base prototype seed (deterministic)."""
    org = conn.execute("SELECT id FROM organizations ORDER BY created_at LIMIT 1").fetchone()
    if org is None:
        raise RuntimeError("base seed must run before the Kiloos profile")
    org_id = org["id"]
    now = _iso()
    for code, name in BRANDS:
        conn.execute(
            "INSERT OR IGNORE INTO brands (organization_id, code, name, data_origin) "
            "VALUES (?, ?, ?, 'sample')",
            (org_id, code, name),
        )
    for code, name in BRANCHES:
        conn.execute(
            "INSERT OR IGNORE INTO branches (organization_id, code, name, data_origin) "
            "VALUES (?, ?, ?, 'sample')",
            (org_id, code, name),
        )

    ids: dict[str, str] = {}
    for code, name, mobile, role, *_rest in PEOPLE:
        existing = conn.execute(
            "SELECT id FROM users WHERE organization_id = ? AND mobile = ?", (org_id, mobile)
        ).fetchone()
        if existing:
            ids[code] = existing["id"]
            continue
        ids[code] = _uid(code)
        conn.execute(
            """INSERT INTO users (id, organization_id, full_name, mobile, role, is_active, created_at)
               VALUES (?, ?, ?, ?, ?, 1, ?)""",
            (ids[code], org_id, name, mobile, role, now),
        )

    head = ids["MGT-01"]
    for code, _name, _mobile, _role, position, title, branch, sup, mgr in PEOPLE:
        conn.execute(
            """INSERT OR REPLACE INTO employee_positions
               (user_id, organization_id, employee_code, position, title, branch_code,
                supervisor_id, branch_manager_id, head_id, data_origin)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'sample')""",
            (
                ids[code],
                org_id,
                code,
                position,
                title,
                branch,
                ids[sup] if sup else None,
                ids[mgr] if mgr else (ids[code] if position == "branch_manager" else None),
                None if position == "management" else head,
            ),
        )
        if position == "rep":
            conn.execute(
                """INSERT OR IGNORE INTO sales_user_map
                   (organization_id, user_external_id, user_id, created_at) VALUES (?, ?, ?, ?)""",
                (org_id, code, ids[code], now),
            )
            _seed_game_profile(conn, ids[code], _name)


AVATARS = ["fox", "bear", "cat", "bunny", "panda", "frog"]


def _seed_game_profile(conn: sqlite3.Connection, user_id: str, full_name: str) -> None:
    """Pre-onboard a demo representative (no XP, no history) so the demo opens in the arena."""
    from app import game

    if conn.execute("SELECT 1 FROM game_progress WHERE user_id = ?", (user_id,)).fetchone():
        return
    state = game._initial_progress(full_name)
    state["player"].update(
        name=full_name[:24], avatar=AVATARS[sum(map(ord, user_id)) % len(AVATARS)], onboarded=True
    )
    game._save(conn, user_id, state)


# ----------------------------------------------------------------------------- workbook
def _split(total: int, parts: int, rng: random.Random) -> list[int]:
    weights = [rng.uniform(0.6, 1.6) for _ in range(parts)]
    scale = total / sum(weights)
    amounts = [int(round(w * scale, -3)) for w in weights]
    amounts[-1] += total - sum(amounts)
    return amounts


def sample_rows() -> tuple[list[list], list[list]]:
    """Deterministic SAMPLE rows: (sales rows, target rows). Seeded RNG, no clock dependence."""
    rng = random.Random(20261116)
    sales: list[list] = []
    counter = 0
    for code, (efes_t, mat_t) in TARGETS.items():
        for brand, target in (("EFES", efes_t), ("MATADOR", mat_t)):
            goal = int(target * ATTAINMENT[code])
            count = 10 if brand == "EFES" else 8
            for amount in _split(goal, count, rng):
                counter += 1
                day = rng.randint(1, 15)
                qty = max(1, amount // rng.choice((380_000, 420_000, 460_000)))
                sales.append(
                    [
                        f"SMP-{counter:04d}",
                        code,
                        f"2026-11-{day:02d}",
                        rng.choice(SKUS[brand]),
                        qty,
                        amount,
                        brand,
                        "BR-TEH" if code in {"VIS-001", "VIS-002", "VIS-003", "VIS-004", "VIS-005"} else "BR-ISF",
                        f"CUST-{rng.randint(100, 460):04d}",
                    ]
                )
    clean = len(sales)
    # Deliberate problems to demonstrate validation + reconciliation (all labelled SAMPLE).
    sales += [
        [sales[3][0], *sales[3][1:]],  # duplicate inside the file
        [sales[40][0], *sales[40][1:]],  # duplicate inside the file
        [sales[77][0], *sales[77][1:]],  # duplicate inside the file
        ["SMP-BAD-01", "VIS-999", "2026-11-05", "EFS-330", 4, 1_500_000, "EFES", "BR-TEH", "CUST-0999"],
        ["SMP-BAD-02", "VIS-998", "2026-11-06", "MTD-1L", 2, 900_000, "MATADOR", "BR-ISF", "CUST-0998"],
        ["SMP-BAD-03", "VIS-001", "not-a-date", "EFS-500", 3, 1_200_000, "EFES", "BR-TEH", "CUST-0101"],
        ["SMP-BAD-04", "VIS-002", "2026-12-30", "EFS-500", 3, 1_200_000, "EFES", "BR-TEH", "CUST-0102"],
        ["SMP-BAD-05", "VIS-004", "2026-11-07", "MTD-250", -5, 1_000_000, "MATADOR", "BR-TEH", "CUST-0103"],
        ["SMP-BAD-06", "VIS-006", "2026-11-08", "", 3, 1_100_000, "EFES", "BR-ISF", "CUST-0104"],
        ["SMP-BAD-07", "VIS-007", "2026-11-09", "MTD-PACK", 3, 1_100_000, "PEPSI", "BR-ISF", "CUST-0105"],
        ["", "VIS-008", "2026-11-10", "EFS-330", 3, 1_100_000, "EFES", "BR-ISF", "CUST-0106"],
    ]
    assert len(sales) == clean + 11
    targets = [
        [code, brand, PERIOD, amt]
        for code, (efes_t, mat_t) in TARGETS.items()
        for brand, amt in (("EFES", efes_t), ("MATADOR", mat_t))
    ]
    targets += [
        ["VIS-999", "EFES", PERIOD, 100_000_000],  # unknown rep
        ["VIS-001", "EFES", PERIOD, 270_000_000],  # duplicate key in file
    ]
    return sales, targets


def _workbook(sales: list[list], targets: list[list], note: str) -> bytes:
    from openpyxl import Workbook

    from app.realimport.xlsxfix import deterministic_xlsx

    wb = Workbook()
    ws = wb.active
    ws.title = "SalesData"
    ws.append(
        [
            "external_id",
            "user_external_id",
            "sale_date",
            "sku_code",
            "quantity",
            "amount",
            "brand_code",
            "branch_code",
            "customer_external_id",
        ]
    )
    for row in sales:
        ws.append(row)
    ws.freeze_panes = "A2"
    tg = wb.create_sheet("Targets")
    tg.append(["user_external_id", "brand_code", "period", "target_amount"])
    for row in targets:
        tg.append(row)
    readme = wb.create_sheet("SAMPLE_README")
    readme.append(["SAMPLE DATA - synthetic, generated by app.kiloos_demo."])
    readme.append(["Not real Kiloos sales. No business formula in this file is verified."])
    readme.append([note])
    buffer = io.BytesIO()
    wb.save(buffer)
    return deterministic_xlsx(buffer.getvalue())  # identical bytes on every call (spike fix)


def sample_workbook_bytes() -> bytes:
    sales, targets = sample_rows()
    return _workbook(sales, targets, "Main sample workbook: 2026-11, EFES + Matador, 2 branches.")


def overlap_workbook_bytes() -> bytes:
    """A second SAMPLE file: re-sends 10 earlier rows (cross-import duplicates) + 5 new rows."""
    sales, _ = sample_rows()
    rows = [list(r) for r in sales[:10]]
    for index in range(5):
        rows.append(
            [f"SMP-LATE-{index + 1:02d}", "VIS-005", "2026-11-14", "MTD-250", 40, 18_000_000,
             "MATADOR", "BR-TEH", "CUST-0201"]
        )
    return _workbook(rows, [], "Overlap sample: shows cross-import duplicate protection.")


# --------------------------------------------------------------------------------- CLI
def _settings():
    from app.config import Settings

    settings = Settings.from_env()
    settings.validate()
    return settings


def reset(settings=None) -> Path:
    """Delete the SQLite file and rebuild the deterministic demo (base seed + Kiloos profile)."""
    import os

    from app import db

    settings = settings or _settings()
    for suffix in ("", "-wal", "-shm"):
        path = Path(str(settings.db_path) + suffix)
        if path.exists():
            path.unlink()
    os.environ["KILOOS_DEMO_PROFILE"] = "kiloos"
    db.init_db(settings.db_path, settings.evidence_dir)
    return settings.db_path


def load_sample(settings=None, *, overlap: bool = False) -> dict:
    """Upload + process the SAMPLE workbook as the seeded admin (same code path as the API)."""
    from app import db, imports, repo
    from app.security import CurrentUser

    settings = settings or _settings()
    conn = db.connect(settings.db_path)
    try:
        row = conn.execute(
            "SELECT id, organization_id, full_name, role FROM users WHERE role = 'admin' LIMIT 1"
        ).fetchone()
        admin = CurrentUser(
            id=row["id"],
            organization_id=row["organization_id"],
            full_name=row["full_name"],
            role=row["role"],
            is_active=True,
        )
        raw = overlap_workbook_bytes() if overlap else sample_workbook_bytes()
        name = "kiloos-sample-sales-overlap.xlsx" if overlap else "kiloos-sample-sales.xlsx"
        import_row = imports.stage_import(
            conn,
            admin,
            name,
            raw,
            max_bytes=settings.sales_max_bytes,
            max_rows=settings.sales_max_rows,
        )
        result = repo.process_sales_import(conn, import_row, admin)
        return {"import_id": import_row["id"], **result}
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.kiloos_demo")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("reset", help="wipe and re-seed the demo database")
    loader = sub.add_parser("load-sample", help="upload + process the SAMPLE workbook")
    loader.add_argument("--overlap", action="store_true", help="use the overlap SAMPLE workbook")
    wb = sub.add_parser("workbook", help="write the SAMPLE workbook(s) to disk")
    wb.add_argument("--out", type=Path, default=Path("var/kiloos-sample-sales.xlsx"))
    args = parser.parse_args(argv)

    if args.cmd == "reset":
        print(f"demo database rebuilt: {reset()}")
    elif args.cmd == "load-sample":
        print(load_sample(overlap=args.overlap))
    else:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_bytes(sample_workbook_bytes())
        overlap = args.out.with_name(args.out.stem + "-overlap.xlsx")
        overlap.write_bytes(overlap_workbook_bytes())
        print(f"wrote {args.out} and {overlap} (SAMPLE data)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
