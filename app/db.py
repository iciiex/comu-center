"""SQLite access for the prototype.

One connection per request keeps the code simple; PostgreSQL + a real pool is a
post-prototype decision (see docs/architecture/decisions/0001-*.md).
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from app.config import REPO_ROOT

SCHEMA_PATH = REPO_ROOT / "db" / "migrations" / "0001_init.sql"


def now_iso() -> str:
    return datetime.now(tz=UTC).isoformat(timespec="seconds")


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=5.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Path, evidence_dir: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    conn = connect(db_path)
    try:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.commit()
        empty = conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"] == 0
        if empty:
            from app.seed import seed_demo

            seed_demo(conn, evidence_dir=evidence_dir)
            conn.commit()
    finally:
        conn.close()
