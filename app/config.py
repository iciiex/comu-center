"""Runtime configuration for the Kiloos Club prototype (MODE: P)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEV_FALLBACK_KEY = "dev-only-change-me"


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError as exc:  # pragma: no cover - configuration error path
        raise RuntimeError(f"{name} must be an integer, got {raw!r}") from exc
    if value <= 0:
        raise RuntimeError(f"{name} must be positive, got {value}")
    return value


@dataclass(frozen=True)
class Settings:
    env: str
    db_path: Path
    evidence_dir: Path
    secret: str
    session_ttl_seconds: int = 12 * 60 * 60
    login_rate_limit: int = 10
    login_rate_window: int = 60
    evidence_retention_days: int = 90
    queue_page_size: int = 20
    sales_max_bytes: int = 5 * 1024 * 1024
    sales_max_rows: int = 5000

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            env=os.getenv("KILOOS_ENV", "dev"),
            db_path=Path(os.getenv("KILOOS_DB", REPO_ROOT / "var" / "kiloos.db")),
            evidence_dir=Path(os.getenv("KILOOS_EVIDENCE_DIR", REPO_ROOT / "var" / "evidence")),
            secret=os.getenv("KILOOS_SECRET", DEV_FALLBACK_KEY),
            session_ttl_seconds=_int_env("KILOOS_SESSION_TTL", 12 * 60 * 60),
            login_rate_limit=_int_env("KILOOS_LOGIN_RATE_LIMIT", 10),
            login_rate_window=_int_env("KILOOS_LOGIN_RATE_WINDOW", 60),
            evidence_retention_days=_int_env("KILOOS_EVIDENCE_RETENTION_DAYS", 90),
            queue_page_size=_int_env("KILOOS_QUEUE_PAGE_SIZE", 20),
            sales_max_bytes=_int_env("KILOOS_SALES_MAX_BYTES", 5 * 1024 * 1024),
            sales_max_rows=_int_env("KILOOS_SALES_MAX_ROWS", 5000),
        )

    def validate(self) -> None:
        """Fail fast instead of running a demo with a production-looking config."""
        if self.env not in {"dev", "test"} and self.secret == DEV_FALLBACK_KEY:
            raise RuntimeError(
                "KILOOS_SECRET must be set outside dev/test "
                "(generate one with: python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
            )
        if len(self.secret) < 16:
            raise RuntimeError("KILOOS_SECRET is too short; use at least 32 random characters")
