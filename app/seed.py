"""Deterministic demo seed.

Every record is sample data (see the DEMO banner in the UI). Identifiers and
amounts are placeholders pending OD-04 / OD-05.
"""

from __future__ import annotations

import base64
import hashlib
import sqlite3
import uuid
from datetime import UTC, datetime, timedelta

# 1x1 transparent PNG — evidence placeholder for the seeded approved submission.
PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def _iso(delta: timedelta) -> str:
    return (datetime.now(tz=UTC) + delta).isoformat(timespec="seconds")


def _id() -> str:
    return str(uuid.uuid4())


def seed_demo(conn: sqlite3.Connection, evidence_dir=None) -> None:
    from pathlib import Path

    org_id = _id()
    conn.execute(
        "INSERT INTO organizations (id, name, created_at) VALUES (?, ?, ?)",
        (org_id, "گلرنگ — شبکه فروش مویرگی (نمونه)", _iso(timedelta())),
    )

    people = [
        ("سارا محمدی", "09120000001", "visitor"),
        ("امیر رضایی", "09120000002", "visitor"),
        ("مریم کاظمی", "09120000003", "visitor"),
        ("حسین کریمی", "09120000004", "operator"),
        ("نگار تهرانی", "09120000005", "admin"),
    ]
    user_ids: dict[str, str] = {}
    for full_name, mobile, role in people:
        user_id = _id()
        user_ids[mobile] = user_id
        conn.execute(
            """INSERT INTO users
               (id, organization_id, full_name, mobile, role, is_active, created_at)
               VALUES (?, ?, ?, ?, ?, 1, ?)""",
            (user_id, org_id, full_name, mobile, role, _iso(timedelta())),
        )

    missions = [
        {
            "title": "ثبت تصویر یخچال فروشگاه",
            "description": "از یخچال محصولات، در وضعیت چیدمان استاندارد، عکس بگیرید و ارسال کنید.",
            "points": 10,
            "starts": -1,
            "ends": 30,
            "max_per_user": 1,
            "status": "active",
        },
        {
            "title": "چیدمان قفسه محصولات هدف",
            "description": "قفسه محصولات هدف را طبق پلان‌وگرام بچینید و تصویر شاهد ثبت کنید.",
            "points": 15,
            "starts": -2,
            "ends": 20,
            "max_per_user": 2,
            "status": "active",
        },
        {
            "title": "کمپین پایان‌یافته (نمونه)",
            "description": (
                "این مأموریت برای نمایش فیلتر بازه زمانی است "
                "و نباید در لیست فعال دیده شود."
            ),
            "points": 5,
            "starts": -20,
            "ends": -10,
            "max_per_user": 1,
            "status": "active",
        },
        {
            "title": "کمپین زمستان (پیش‌نویس)",
            "description": "پیش‌نویس مدیریتی؛ تا انتشار نباید برای ویزیتور دیده شود.",
            "points": 20,
            "starts": -1,
            "ends": 40,
            "max_per_user": 1,
            "status": "draft",
        },
    ]

    mission_ids: list[str] = []
    for index, mission in enumerate(missions, start=1):
        mission_id = _id()
        mission_ids.append(mission_id)
        rule_code = f"MISSION_SAMPLE_{index:02d}"
        conn.execute(
            """INSERT INTO missions
               (id, organization_id, title, description, mission_type, points, starts_at,
                ends_at, max_per_user, requires_review, status, rule_code, created_at)
               VALUES (?, ?, ?, ?, 'photo_submission', ?, ?, ?, ?, 1, ?, ?, ?)""",
            (
                mission_id,
                org_id,
                mission["title"],
                mission["description"],
                mission["points"],
                _iso(timedelta(days=mission["starts"])),
                _iso(timedelta(days=mission["ends"])),
                mission["max_per_user"],
                mission["status"],
                rule_code,
                _iso(timedelta()),
            ),
        )
        conn.execute(
            """INSERT INTO scoring_rule_versions
               (id, rule_code, version, calculation_type, points, effective_from,
                effective_to, status, is_sample)
               VALUES (?, ?, 1, 'fixed', ?, ?, NULL, 'published', 1)""",
            (_id(), rule_code, mission["points"], _iso(timedelta(days=mission["starts"]))),
        )

    conn.execute(
        """INSERT INTO competitions (id, organization_id, title, starts_at, ends_at, is_sample)
           VALUES (?, ?, ?, ?, ?, 1)""",
        (
            _id(),
            org_id,
            "دوره آبان ۱۴۰۵ (نمونه)",
            _iso(timedelta(days=-7)),
            _iso(timedelta(days=7)),
        ),
    )

    # Sales-import SAMPLE contract: explicit visitor mapping + per-amount rule.
    # Both are placeholders until the employer approves OD-03 / OD-04.
    for external_id, mobile in (
        ("VIS-001", "09120000001"),
        ("VIS-002", "09120000002"),
        ("VIS-003", "09120000003"),
    ):
        conn.execute(
            """INSERT INTO sales_user_map
               (organization_id, user_external_id, user_id, created_at)
               VALUES (?, ?, ?, ?)""",
            (org_id, external_id, user_ids[mobile], _iso(timedelta())),
        )

    conn.execute(
        """INSERT INTO scoring_rule_versions
           (id, rule_code, version, calculation_type, points, unit_size,
            effective_from, effective_to, status, is_sample)
           VALUES (?, 'SALES_AMOUNT_SAMPLE', 1, 'per_unit_amount', 1, 1000000,
                   ?, NULL, 'published', 1)""",
        (_id(), _iso(timedelta(days=-30))),
    )

    # One approved submission so the leaderboard and wallet are demonstrable.
    if evidence_dir is not None:
        evidence_dir = Path(evidence_dir)
        evidence_dir.mkdir(parents=True, exist_ok=True)
        submission_id = _id()
        relative = f"{submission_id}.png"
        (evidence_dir / relative).write_bytes(PNG_1PX)
        conn.execute(
            """INSERT INTO submissions
               (id, mission_id, user_id, status, note, request_id, created_at,
                reviewed_at, reviewed_by)
               VALUES (?, ?, ?, 'approved', ?, ?, ?, ?, ?)""",
            (
                submission_id,
                mission_ids[1],
                user_ids["09120000002"],
                "نمونه داده نمایشی — تصویر یخچال",
                f"seed-{submission_id}",
                _iso(timedelta(hours=-30)),
                _iso(timedelta(hours=-28)),
                user_ids["09120000004"],
            ),
        )
        conn.execute(
            """INSERT INTO submission_evidences
               (id, submission_id, file_name, content_type, storage_path, sha256, created_at)
               VALUES (?, ?, ?, 'image/png', ?, ?, ?)""",
            (
                _id(),
                submission_id,
                "sample.png",
                relative,
                hashlib.sha256(PNG_1PX).hexdigest(),
                _iso(timedelta(hours=-30)),
            ),
        )

        from app.scoring import award_mission_approval

        submission = conn.execute(
            "SELECT * FROM submissions WHERE id = ?", (submission_id,)
        ).fetchone()
        award_mission_approval(conn, submission, actor_id=user_ids["09120000004"])


def main() -> None:
    """Rebuild an empty demo database (`make seed`)."""
    from app.config import Settings
    from app.db import init_db

    settings = Settings.from_env()
    settings.validate()
    init_db(settings.db_path, settings.evidence_dir)
    print(f"seeded {settings.db_path}")


if __name__ == "__main__":
    main()
