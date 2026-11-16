"""Business Decision Register (BD-xx): every unresolved business question with its current
assumption, impact, status and required approver. Seeded from ``decisions.seed.json``; the API
exposes it read-only so no screen can mark a business decision approved."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from app.db import now_iso

SEED_FILE = Path(__file__).with_name("decisions.seed.json")


def seed_decisions(conn: sqlite3.Connection) -> int:
    """Insert missing decisions; never overwrite an existing row (its status may have been updated)."""
    added = 0
    for item in json.loads(SEED_FILE.read_text(encoding="utf-8")):
        cur = conn.execute(
            """INSERT OR IGNORE INTO ri_business_decisions (id, question, assumption, impact, status, approver, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (item["id"], item["question"], item["assumption"], item["impact"], item["status"], item["approver"], now_iso()),
        )
        added += cur.rowcount
    conn.commit()
    return added


def list_decisions(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return [dict(r) for r in conn.execute("SELECT * FROM ri_business_decisions ORDER BY id")]
