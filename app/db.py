"""SQLite access for the prototype.

One connection per request keeps the code simple; PostgreSQL + a real pool is a
post-prototype decision (see docs/architecture/decisions/0001-*.md).
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from app.config import REPO_ROOT

MIGRATIONS_DIR = REPO_ROOT / "db" / "migrations"


def now_iso() -> str:
    return datetime.now(tz=UTC).isoformat(timespec="seconds")


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=5.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def apply_migrations(conn: sqlite3.Connection) -> list[str]:
    """Run each ``db/migrations/NNNN_*.sql`` exactly once, in filename order.

    ``schema_migrations`` records what has run. The first version of the
    prototype ran every file on every boot; migration 0003 needs a real
    ``ALTER TABLE``, so this tiny runner replaced that. Still not Alembic:
    no downgrades, no checksums (see docs/architecture/database-erd.md).
    """
    conn.execute(
        """CREATE TABLE IF NOT EXISTS schema_migrations (
               name       TEXT PRIMARY KEY,
               applied_at TEXT NOT NULL
           )"""
    )
    done = {row["name"] for row in conn.execute("SELECT name FROM schema_migrations")}
    applied: list[str] = []
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if path.name in done:
            continue
        conn.executescript(path.read_text(encoding="utf-8"))
        conn.execute(
            "INSERT INTO schema_migrations (name, applied_at) VALUES (?, ?)",
            (path.name, now_iso()),
        )
        conn.commit()
        applied.append(path.name)
    return applied


def init_db(db_path: Path, evidence_dir: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    conn = connect(db_path)
    try:
        apply_migrations(conn)
        empty = conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"] == 0
        if empty:
            from app.seed import seed_demo

            seed_demo(conn, evidence_dir=evidence_dir)
            conn.commit()
    finally:
        conn.close()
