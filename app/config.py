"""Runtime configuration for the Kiloos Club prototype (MODE: P)."""

from __future__ import annotations

import hashlib
import hmac
import os
from dataclasses import dataclass, field
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
    tribal_gamification_enabled: bool = False
    demo_mode: str = "off"
    demo_operator_key: str = field(default="", repr=False)

    @property
    def play_enabled(self) -> bool:
        return self.env in {"dev", "test"} and self.demo_mode == "play"

    @property
    def legacy_demo_enabled(self) -> bool:
        return self.env in {"dev", "test"} and self.demo_mode == "legacy"

    @property
    def legacy_sessions_enabled(self) -> bool:
        return not self.play_enabled and (
            self.legacy_demo_enabled or self.secret != DEV_FALLBACK_KEY
        )

    @property
    def legacy_session_secret(self) -> str:
        # Discard cookies issued under the old passwordless scheme; demo credentials
        # cannot verify as ordinary (non-demo) sessions even with the same signing secret.
        scope = f"legacy-demo:{self.demo_operator_key}" if self.legacy_demo_enabled else "standard"
        return hmac.new(
            self.secret.encode(), f"kiloos-session-v2:{scope}".encode(), hashlib.sha256
        ).hexdigest()

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
            demo_mode=os.getenv("KILOOS_DEMO_MODE", "off").strip().lower(),
            demo_operator_key=os.getenv("KILOOS_DEMO_OPERATOR_KEY", ""),
            tribal_gamification_enabled=(
                os.getenv("KILOOS_TRIBAL_GAMIFICATION_ENABLED", "false").strip().lower()
                in {"1", "true", "yes", "on"}
            ),
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
        if self.demo_mode not in {"off", "play", "legacy"}:
            raise RuntimeError("KILOOS_DEMO_MODE must be off, play or legacy")
        if self.play_enabled or self.legacy_demo_enabled:
            if len(self.demo_operator_key.strip()) < 32 or self.demo_operator_key == self.secret:
                raise RuntimeError(
                    "Set a separate random KILOOS_DEMO_OPERATOR_KEY (32+ characters)"
                )
