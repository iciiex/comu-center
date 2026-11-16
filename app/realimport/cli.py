"""Command line for the spike (no PII in the output - aggregates only).

    python -m app.realimport.cli import <workbook.xlsx>   upload -> validate -> confirm -> run all rules -> summary

The workbook is only ever read. It is copied once into the spike storage directory under its
SHA-256 (the original, e.g. a ``:ro`` mount, is never opened for writing).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from app import db as appdb
from app.config import Settings
from app.realimport import calc, decisions, pipeline, reconcile


def run_import(path: Path, settings: Settings) -> dict:
    appdb.init_db(settings.db_path, settings.evidence_dir)
    conn = appdb.connect(settings.db_path)
    try:
        conn.executescript("PRAGMA journal_mode=WAL;")
        decisions.seed_decisions(conn)
        calc.seed_rule_sets(conn)
        admin = conn.execute("SELECT id FROM users WHERE role = 'admin' ORDER BY rowid LIMIT 1").fetchone()
        user_id = admin["id"] if admin else None
        wb_row, wb_replayed = pipeline.upload_workbook(conn, settings, user_id, path.name, path.read_bytes())
        batch, b_replayed = pipeline.create_batch(conn, settings, user_id, wb_row["id"], None)
        batch, v_replayed = pipeline.stage_batch(conn, settings, user_id, batch["id"])
        if not v_replayed:
            reconcile.refresh_import_checks(conn, batch["id"])
        batch, c_replayed = pipeline.confirm_batch(conn, user_id, batch["id"])
        runs = []
        for rule in conn.execute("SELECT * FROM ri_rule_sets ORDER BY id").fetchall():
            run, replayed = calc.run_calculation(conn, user_id, batch["id"], rule["id"])
            if not replayed:
                reconcile.refresh_run_checks(conn, run["id"])
            runs.append({**calc.run_dict(conn, run), "replayed": replayed})
        return {
            "workbook": {"sha256": wb_row["sha256"], "origin": wb_row["data_origin"], "replayed": wb_replayed},
            "batch": {"id": batch["id"], "status": batch["status"], "replayed": all([b_replayed, v_replayed, c_replayed]),
                      "counts": json.loads(batch["counts_json"])},
            "runs": runs,
            "reconciliation": [{k: c[k] for k in ("check_code", "status", "reference_value", "prototype_value", "abs_variance", "pct_variance")}
                               for c in reconcile.list_checks(conn, batch["id"])],
        }
    finally:
        conn.close()


def main(argv: list[str]) -> int:
    if len(argv) != 3 or argv[1] != "import":
        print(__doc__)
        return 2
    settings = Settings.from_env()
    if not settings.real_import_enabled:
        print("KILOOS_REAL_IMPORT=1 is required.", file=sys.stderr)
        return 2
    print(json.dumps(run_import(Path(argv[2]), settings), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
