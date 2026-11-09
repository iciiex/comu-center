"""Runtime configuration for the Kiloos Club prototype (MODE: P)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEV_FALLBACK_KEY = "dev-only-change-me"


@dataclass(frozen=True)
class Settings:
    env: str
    db_path: Path
    evidence_dir: Path
    secret: str

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            env=os.getenv("KILOOS_ENV", "dev"),
            db_path=Path(os.getenv("KILOOS_DB", REPO_ROOT / "var" / "kiloos.db")),
            evidence_dir=Path(os.getenv("KILOOS_EVIDENCE_DIR", REPO_ROOT / "var" / "evidence")),
            secret=os.getenv("KILOOS_SECRET", DEV_FALLBACK_KEY),
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
