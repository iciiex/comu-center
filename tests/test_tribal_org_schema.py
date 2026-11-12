from __future__ import annotations

import sqlite3
import uuid

import pytest


def _id() -> str:
    return str(uuid.uuid4())


def test_org_tree_and_membership_are_generic_and_tenant_scoped(db: sqlite3.Connection) -> None:
    org_id, user_id = db.execute(
        "SELECT organization_id, id FROM users LIMIT 1"
    ).fetchone()
    now = "2026-11-12T12:00:00+00:00"
    root_type, child_type = _id(), _id()
    db.executemany(
        """INSERT INTO org_unit_types
           (id, organization_id, code, label, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        [
            (root_type, org_id, "zone", "Zone", now),
            (child_type, org_id, "team", "Team", now),
        ],
    )
    db.execute(
        """INSERT INTO org_unit_type_parent_types
           (organization_id, child_type_id, parent_type_id) VALUES (?, ?, ?)""",
        (org_id, child_type, root_type),
    )
    root, child = _id(), _id()
    db.execute(
        """INSERT INTO org_units
           (id, organization_id, type_id, name, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (root, org_id, root_type, "North", now, now),
    )
    db.execute(
        """INSERT INTO org_units
           (id, organization_id, type_id, parent_id, name, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (child, org_id, child_type, root, "Team A", now, now),
    )
    db.execute(
        """INSERT INTO org_memberships
           (id, organization_id, user_id, unit_id, valid_from, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (_id(), org_id, user_id, child, now, now),
    )
    db.commit()

    assert db.execute(
        "SELECT parent_id FROM org_units WHERE id = ?", (child,)
    ).fetchone()[0] == root
    assert db.execute(
        "SELECT COUNT(*) FROM org_memberships WHERE unit_id = ?", (child,)
    ).fetchone()[0] == 1


def test_org_membership_cannot_cross_organization_boundary(db: sqlite3.Connection) -> None:
    db.execute("PRAGMA foreign_keys = ON")
    org_id, user_id = db.execute(
        "SELECT organization_id, id FROM users LIMIT 1"
    ).fetchone()
    now = "2026-11-12T12:00:00+00:00"
    type_id, unit_id = _id(), _id()
    db.execute(
        """INSERT INTO org_unit_types
           (id, organization_id, code, label, created_at) VALUES (?, ?, ?, ?, ?)""",
        (type_id, org_id, _id(), "Unit", now),
    )
    db.execute(
        """INSERT INTO org_units
           (id, organization_id, type_id, name, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (unit_id, org_id, type_id, "Unit", now, now),
    )
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            """INSERT INTO org_memberships
               (id, organization_id, user_id, unit_id, valid_from, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (_id(), "different-org", user_id, unit_id, now, now),
        )
