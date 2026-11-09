"""Signed session token + CSRF helpers.

This is a *prototype* auth layer: demo login, no OTP/SMS (OD-01 is OPEN).
Signing, expiry and role checks are real so the flow can be hardened, not faked.

Session transport (see docs/engineering/api-spec.md § Auth):
- preferred: HttpOnly cookie ``kiloos_session``;
- fallback: the same signed token as ``?s=`` query parameter, because embedded
  previews block third-party cookies. The fallback is demo-only (D-002): a URL
  leaks into history/logs, so production must use first-party hosting or OTP.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import sqlite3
import time
from dataclasses import dataclass

from fastapi import Request, Response

COOKIE_NAME = "kiloos_session"
STAFF_ROLES = {"operator", "admin"}
SESSION_TTL_SECONDS = 12 * 60 * 60
MAX_CLOCK_SKEW_SECONDS = 300


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


def make_token(
    user_id: str,
    secret: str,
    *,
    ttl_seconds: int = SESSION_TTL_SECONDS,
    now: float | None = None,
) -> str:
    """Return a URL-safe token: base64url("<user_id>.<issued_at>.<hmac>")."""
    issued = int(now if now is not None else time.time())
    payload = _sign(f"{user_id}.{issued}", secret)
    # strip padding: "=" makes some clients quote the cookie value
    return base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")


def read_token(
    token: str | None,
    secret: str,
    *,
    ttl_seconds: int = SESSION_TTL_SECONDS,
    now: float | None = None,
) -> str | None:
    """Verify signature and expiry; return the user id or ``None``."""
    if not token:
        return None
    padded = token + "=" * (-len(token) % 4)
    try:
        decoded = base64.urlsafe_b64decode(padded.encode()).decode()
    except (ValueError, UnicodeDecodeError):
        return None
    payload = _unsign(decoded, secret)
    if not payload:
        return None
    user_id, _, issued = payload.rpartition(".")
    if not user_id or not issued.isdigit():
        return None
    stamp = int(issued)
    current = int(now if now is not None else time.time())
    if stamp - current > MAX_CLOCK_SKEW_SECONDS:
        return None
    if current - stamp > ttl_seconds:
        return None
    return user_id


def session_token(request: Request) -> str | None:
    """Effective session token: ``?s=`` first (iframe fallback), then cookie."""
    candidate = request.query_params.get("s")
    secret = request.app.state.settings.secret
    ttl = request.app.state.settings.session_ttl_seconds
    if candidate and read_token(candidate, secret, ttl_seconds=ttl):
        return candidate
    raw = request.cookies.get(COOKIE_NAME)
    return raw or None


def csrf_for(token: str, secret: str) -> str:
    """Derive a CSRF token from the session token (works without cookies)."""
    return hmac.new(secret.encode(), f"csrf:{token}".encode(), hashlib.sha256).hexdigest()


def csrf_token(request: Request) -> str:
    token = session_token(request)
    if not token:
        return ""
    return csrf_for(token, request.app.state.settings.secret)


def set_session(response: Response, user_id: str, secret: str, token: str | None = None) -> str:
    """Set the cookie and return the token (reused for the ``?s=`` fallback)."""
    token = token or make_token(user_id, secret)
    response.set_cookie(
        COOKIE_NAME,
        token,
        httponly=True,
        samesite="lax",
        max_age=SESSION_TTL_SECONDS,
    )
    return token


def clear_session(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME)


def current_user(request: Request, conn: sqlite3.Connection) -> CurrentUser | None:
    settings = request.app.state.settings
    token = request.cookies.get(COOKIE_NAME)
    from_url = False
    candidate = request.query_params.get("s")
    ttl = settings.session_ttl_seconds
    if candidate and read_token(candidate, settings.secret, ttl_seconds=ttl):
        token, from_url = candidate, True

    user_id = read_token(token, settings.secret, ttl_seconds=settings.session_ttl_seconds)
    if not user_id:
        return None

    request.state.session_token = token
    request.state.session_in_url = from_url
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
