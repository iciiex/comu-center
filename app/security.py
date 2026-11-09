"""Signed session cookie + role helpers.

This is a *prototype* auth layer: demo login, no OTP/SMS (OD-01 is OPEN).
The signing and role checks are real so the flow can be hardened, not faked.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import sqlite3
from dataclasses import dataclass

from fastapi import Request, Response

COOKIE_NAME = "kiloos_session"
STAFF_ROLES = {"operator", "admin"}


@dataclass(frozen=True)
class CurrentUser:
    id: str
    organization_id: str
    full_name: str
    role: str
    is_active: bool

    @property
    def is_staff(self) -> bool:
        return self.role in STAFF_ROLES

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


def _sign(value: str, secret: str) -> str:
    digest = hmac.new(secret.encode(), value.encode(), hashlib.sha256).hexdigest()
    return f"{value}.{digest}"


def _unsign(token: str, secret: str) -> str | None:
    value, _, digest = token.rpartition(".")
    if not value or not digest:
        return None
    expected = hmac.new(secret.encode(), value.encode(), hashlib.sha256).hexdigest()
    return value if hmac.compare_digest(digest, expected) else None


def set_session(response: Response, user_id: str, secret: str) -> None:
    token = base64.urlsafe_b64encode(_sign(user_id, secret).encode()).decode()
    response.set_cookie(
        COOKIE_NAME,
        token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 12,
    )


def clear_session(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME)


def current_user(request: Request, conn: sqlite3.Connection) -> CurrentUser | None:
    raw = request.cookies.get(COOKIE_NAME)
    if not raw:
        return None
    try:
        decoded = base64.urlsafe_b64decode(raw.encode()).decode()
    except (ValueError, UnicodeDecodeError):
        return None
    user_id = _unsign(decoded, request.app.state.settings.secret)
    if not user_id:
        return None
    row = conn.execute(
        "SELECT id, organization_id, full_name, role, is_active FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    if row is None or not row["is_active"]:
        return None
    return CurrentUser(
        id=row["id"],
        organization_id=row["organization_id"],
        full_name=row["full_name"],
        role=row["role"],
        is_active=bool(row["is_active"]),
    )
