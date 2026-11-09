"""Maintenance tasks for the prototype (run manually, no scheduler yet).

Evidence retention (D-003, PROPOSED): after ``KILOOS_EVIDENCE_RETENTION_DAYS``
the stored image is deleted and its row removed; an ``audit_logs`` entry keeps
the metadata (id, submission, sha256) so the decision stays traceable.
Policy values are sample defaults until the employer approves a retention rule.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app import db
from app.config import Settings


def purge_evidence(
    settings: Settings,
    *,
    retention_days: int | None = None,
    now: datetime | None = None,
    dry_run: bool = False,
) -> dict[str, int]:
    """Delete evidence older than the retention window; return counters."""
    days = retention_days if retention_days is not None else settings.evidence_retention_days
    if days <= 0:
        raise ValueError("retention days must be positive")
    moment = now or datetime.now(tz=UTC)
    cutoff = (moment - timedelta(days=days)).isoformat(timespec="seconds")

    conn = db.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """SELECT e.id, e.submission_id, e.storage_path, e.sha256, e.created_at
               FROM submission_evidences e
               WHERE e.created_at < ?
               ORDER BY e.created_at""",
            (cutoff,),
        ).fetchall()
        deleted = 0
        missing = 0
        for row in rows:
            path = (settings.evidence_dir / row["storage_path"]).resolve()
            if not str(path).startswith(str(Path(settings.evidence_dir).resolve())):
                missing += 1
                continue
            if path.is_file():
                if not dry_run:
                    path.unlink()
                deleted += 1
            else:
                missing += 1
            if dry_run:
                continue
            conn.execute("DELETE FROM submission_evidences WHERE id = ?", (row["id"],))
            _audit(conn, row)
        if not dry_run:
            conn.commit()
        return {"candidates": len(rows), "deleted": deleted, "missing": missing}
    finally:
        conn.close()


def _audit(conn: sqlite3.Connection, row: sqlite3.Row) -> None:
    conn.execute(
        """INSERT INTO audit_logs (id, actor_id, action, entity_type, entity_id,
                                   detail_json, created_at)
           VALUES (?, NULL, 'evidence.purged', 'submission_evidence', ?, ?, ?)""",
        (
            str(uuid.uuid4()),
            row["id"],
            json.dumps(
                {
                    "submission_id": row["submission_id"],
                    "sha256": row["sha256"],
                    "storage_path": row["storage_path"],
                    "evidence_created_at": row["created_at"],
                },
                ensure_ascii=False,
            ),
            db.now_iso(),
        ),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.maintenance")
    sub = parser.add_subparsers(dest="command", required=True)
    purge = sub.add_parser("purge-evidence", help="delete evidence older than the policy")
    purge.add_argument("--days", type=int, default=None, help="override retention window")
    purge.add_argument("--dry-run", action="store_true", help="report without deleting")
    args = parser.parse_args(argv)

    settings = Settings.from_env()
    settings.validate()
    if args.command == "purge-evidence":
        result = purge_evidence(settings, retention_days=args.days, dry_run=args.dry_run)
        prefix = "DRY-RUN " if args.dry_run else ""
        print(
            f"{prefix}evidence purge: candidates={result['candidates']} "
            f"deleted={result['deleted']} already-missing={result['missing']}"
        )
        return 0
    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
