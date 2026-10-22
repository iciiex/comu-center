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
    http_host: str = "127.0.0.1"
    http_port: int = 8000
    # Format: "7=damiish:instagram:ig-acct-1,9=maygoosh:instagram:ig-acct-2"
    chatwoot_inbox_map: str = ""
    # OpenAI-compatible AI provider (Gemini/Groq/OpenRouter/Ollama)
    ai_api_base_url: str = ""
    ai_model: str = ""
    # Direct Meta integration: "17841400008460056=damiish,..."
    meta_account_map: str = ""
    meta_ig_account_id: str = ""
    meta_graph_base_url: str = "https://graph.instagram.com"
    meta_api_version: str = "v25.0"
    operator_token: str = field(default="", repr=False)

    def validate(self) -> None:
        if self.env_name not in {"local", "test", "production"}:
            raise ValidationError(f"INVAR_ENV must be local|test|production, got {self.env_name!r}")
        if not self.enabled_products:
            raise ValidationError("INVAR_ENABLED_PRODUCTS must name at least one product")
        if not 1 <= self.http_port <= 65535:
            raise ValidationError(f"INVAR_HTTP_PORT out of range: {self.http_port}")
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
        if self.meta_live_send_enabled and not self.meta_ig_account_id:
            raise ValidationError(
                "Meta live sending requires INVAR_META_IG_ACCOUNT_ID")
        if self.ai_provider_name == "openai_compat" and not (
                self.ai_api_base_url and self.ai_model):
            raise ValidationError(
                "openai_compat provider requires INVAR_AI_API_BASE_URL "
                "and INVAR_AI_MODEL")
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
                f"http: {self.http_host}:{self.http_port}",
                f"chatwoot_inbox_map: {self.chatwoot_inbox_map or 'not set'}",
                f"ai_api_base_url: {self.ai_api_base_url or 'not set'}",
                f"ai_model: {self.ai_model or 'not set'}",
                f"meta_account_map: {self.meta_account_map or 'not set'}",
                f"meta_ig_account_id: {self.meta_ig_account_id or 'not set'}",
                f"meta_graph_base_url: {self.meta_graph_base_url}",
                f"meta_api_version: {self.meta_api_version}",
                f"operator_token: {present(self.operator_token)}",
            ]
        )


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    source = os.environ if env is None else env
    try:
        http_port = int(source.get("INVAR_HTTP_PORT", "8000"))
    except ValueError as exc:
        raise ValidationError("INVAR_HTTP_PORT must be an integer") from exc
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
        http_host=source.get("INVAR_HTTP_HOST", "127.0.0.1"),
        http_port=http_port,
        chatwoot_inbox_map=source.get("INVAR_CHATWOOT_INBOX_MAP", ""),
        ai_api_base_url=source.get("INVAR_AI_API_BASE_URL", "").rstrip("/"),
        ai_model=source.get("INVAR_AI_MODEL", ""),
        meta_account_map=source.get("INVAR_META_ACCOUNT_MAP", ""),
        meta_ig_account_id=source.get("INVAR_META_IG_ACCOUNT_ID", ""),
        meta_graph_base_url=source.get(
            "INVAR_META_GRAPH_BASE_URL", "https://graph.instagram.com").rstrip("/"),
        meta_api_version=source.get("INVAR_META_API_VERSION", "v25.0"),
        operator_token=source.get("INVAR_OPERATOR_TOKEN", ""),
    )
    settings.validate()
    return settings
