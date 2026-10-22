"""Configuration loading & startup validation.

Safe defaults: AI sending and live Meta sending are OFF unless explicitly
enabled. In `production`, enabling live Meta sending without credentials is a
startup error (fail fast, never silently degrade). Secrets are never printed.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field

from .domain.errors import ValidationError

_TRUE = {"1", "true", "yes", "on"}


def _flag(env: Mapping[str, str], key: str, default: bool = False) -> bool:
    raw = env.get(key)
    if raw is None:
        return default
    return raw.strip().lower() in _TRUE


@dataclass(frozen=True)
class Settings:
    env_name: str = "local"
    enabled_products: frozenset[str] = field(default_factory=lambda: frozenset({"damiish"}))
    ai_send_enabled: bool = False
    meta_live_send_enabled: bool = False
    database_url: str = ""
    meta_app_secret: str = field(default="", repr=False)
    meta_webhook_verify_token: str = field(default="", repr=False)
    meta_access_token: str = field(default="", repr=False)
    ai_provider_name: str = "fake"
    ai_provider_api_key: str = field(default="", repr=False)
    chatwoot_base_url: str = ""
    chatwoot_bot_token: str = field(default="", repr=False)
    chatwoot_webhook_secret: str = field(default="", repr=False)
    sqlite_path: str = "data/invar_comms.sqlite3"

    def validate(self) -> None:
        if self.env_name not in {"local", "test", "production"}:
            raise ValidationError(f"INVAR_ENV must be local|test|production, got {self.env_name!r}")
        if not self.enabled_products:
            raise ValidationError("INVAR_ENABLED_PRODUCTS must name at least one product")
        if self.meta_live_send_enabled and not self.ai_send_enabled:
            raise ValidationError(
                "Meta live sending requires INVAR_AI_SEND_ENABLED=true (explicit, separate switch)"
            )
        if self.meta_live_send_enabled and not (
            self.meta_app_secret and self.meta_webhook_verify_token and self.meta_access_token
        ):
            raise ValidationError(
                "Meta live sending requires app secret, webhook verify token and access token"
            )
        if self.env_name == "production" and self.ai_send_enabled and not self.database_url:
            raise ValidationError("production AI sending requires INVAR_DATABASE_URL (audit store)")

    def redacted_summary(self) -> str:
        def present(secret: str) -> str:
            return "set" if secret else "not set"

        return "\n".join(
            [
                f"env: {self.env_name}",
                f"enabled_products: {','.join(sorted(self.enabled_products))}",
                f"ai_send_enabled: {self.ai_send_enabled}",
                f"meta_live_send_enabled: {self.meta_live_send_enabled}",
                f"database_url: {present(self.database_url)}",
                f"meta_app_secret: {present(self.meta_app_secret)}",
                f"meta_webhook_verify_token: {present(self.meta_webhook_verify_token)}",
                f"meta_access_token: {present(self.meta_access_token)}",
                f"ai_provider_name: {self.ai_provider_name}",
                f"ai_provider_api_key: {present(self.ai_provider_api_key)}",
                f"chatwoot_base_url: {self.chatwoot_base_url or 'not set'}",
                f"chatwoot_bot_token: {present(self.chatwoot_bot_token)}",
                f"chatwoot_webhook_secret: {present(self.chatwoot_webhook_secret)}",
                f"sqlite_path: {self.sqlite_path}",
            ]
        )


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    source = os.environ if env is None else env
    products = frozenset(
        p.strip()
        for p in source.get("INVAR_ENABLED_PRODUCTS", "damiish").split(",")
        if p.strip()
    )
    settings = Settings(
        env_name=source.get("INVAR_ENV", "local").strip().lower(),
        enabled_products=products,
        ai_send_enabled=_flag(source, "INVAR_AI_SEND_ENABLED"),
        meta_live_send_enabled=_flag(source, "INVAR_META_LIVE_SEND_ENABLED"),
        database_url=source.get("INVAR_DATABASE_URL", ""),
        meta_app_secret=source.get("INVAR_META_APP_SECRET", ""),
        meta_webhook_verify_token=source.get("INVAR_META_WEBHOOK_VERIFY_TOKEN", ""),
        meta_access_token=source.get("INVAR_META_ACCESS_TOKEN", ""),
        ai_provider_name=source.get("INVAR_AI_PROVIDER_NAME", "fake"),
        ai_provider_api_key=source.get("INVAR_AI_PROVIDER_API_KEY", ""),
        chatwoot_base_url=source.get("INVAR_CHATWOOT_BASE_URL", "").rstrip("/"),
        chatwoot_bot_token=source.get("INVAR_CHATWOOT_BOT_TOKEN", ""),
        chatwoot_webhook_secret=source.get("INVAR_CHATWOOT_WEBHOOK_SECRET", ""),
        sqlite_path=source.get("INVAR_SQLITE_PATH", "data/invar_comms.sqlite3"),
    )
    settings.validate()
    return settings
