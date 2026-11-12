"""Read-only Tribal organization queries over the generic org-unit foundation."""

from __future__ import annotations

import base64
import binascii
import sqlite3

from fastapi import HTTPException


def _decode_cursor(cursor: str | None) -> tuple[str, str] | None:
    if cursor is None:
        return None
    try:
        decoded = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)).decode("utf-8")
        name, unit_id = decoded.split("\n", 1)
    except (ValueError, UnicodeDecodeError, binascii.Error) as exc:
        raise HTTPException(status_code=400, detail="Invalid pagination cursor.") from exc
    if not unit_id:
        raise HTTPException(status_code=400, detail="Invalid pagination cursor.")
    return name, unit_id


def _encode_cursor(name: str, unit_id: str) -> str:
    value = f"{name}\n{unit_id}".encode()
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def list_units(
    conn: sqlite3.Connection,
    organization_id: str,
    *,
    parent_id: str | None,
    unit_type: str | None,
    query: str | None,
    limit: int,
    cursor: str | None,
) -> dict:
    """List active children in one organization using stable keyset pagination."""
    if parent_id is not None:
        parent = conn.execute(
            """SELECT 1 FROM org_units
               WHERE id = ? AND organization_id = ? AND status = 'active'""",
            (parent_id, organization_id),
        ).fetchone()
        if parent is None:
            raise HTTPException(status_code=404, detail="Organization unit not found.")

    clauses = ["u.organization_id = ?", "u.status = 'active'"]
    params: list[object] = [organization_id]
    if parent_id is None:
        clauses.append("u.parent_id IS NULL")
    else:
        clauses.append("u.parent_id = ?")
        params.append(parent_id)
    if unit_type:
        clauses.append("t.code = ?")
        params.append(unit_type)
    if query:
        clauses.append("u.name LIKE ? ESCAPE '\\'")
        escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        params.append(f"%{escaped}%")

    position = _decode_cursor(cursor)
    if position:
        clauses.append("(u.name COLLATE NOCASE > ? OR (u.name COLLATE NOCASE = ? AND u.id > ?))")
        params.extend((position[0], position[0], position[1]))

    # Dynamic SQL fragments above are fixed predicates; all client values remain bound params.
    rows = conn.execute(  # noqa: S608
        """SELECT u.id, u.parent_id, u.type_id, t.code AS type_code, t.label AS type_label,
                  u.name, u.flag_asset_key
           FROM org_units u
           JOIN org_unit_types t ON t.id = u.type_id AND t.organization_id = u.organization_id
           WHERE """ + " AND ".join(clauses) + " ORDER BY u.name COLLATE NOCASE, u.id LIMIT ?",  # noqa: S608
        (*params, limit + 1),
    ).fetchall()

    has_more = len(rows) > limit
    visible = rows[:limit]
    items = [
        {
            "id": row["id"],
            "parent_id": row["parent_id"],
            "type": {"code": row["type_code"], "label": row["type_label"]},
            "name": row["name"],
            "flag_asset_key": row["flag_asset_key"],
        }
        for row in visible
    ]
    next_cursor = (
        _encode_cursor(visible[-1]["name"], visible[-1]["id"]) if has_more and visible else None
    )
    return {"items": items, "next_cursor": next_cursor}


def get_unit(conn: sqlite3.Connection, organization_id: str, unit_id: str) -> dict:
    row = conn.execute(
        """SELECT u.id, u.parent_id, u.type_id, t.code AS type_code, t.label AS type_label,
                  u.name, u.flag_asset_key, u.valid_from, u.valid_to
           FROM org_units u
           JOIN org_unit_types t ON t.id = u.type_id AND t.organization_id = u.organization_id
           WHERE u.id = ? AND u.organization_id = ? AND u.status = 'active'""",
        (unit_id, organization_id),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Organization unit not found.")
    return {
        "id": row["id"],
        "parent_id": row["parent_id"],
        "type": {"id": row["type_id"], "code": row["type_code"], "label": row["type_label"]},
        "name": row["name"],
        "flag_asset_key": row["flag_asset_key"],
        "valid_from": row["valid_from"],
        "valid_to": row["valid_to"],
    }
