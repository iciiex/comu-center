"""Chatwoot REST client (stdlib urllib) — the bot's outbound side.

Implements the ChannelAdapter port for sending through Chatwoot, plus
conversation status toggling for handoff projection. Sending is an external,
customer-affecting action: it is only ever invoked *after* the application
layer's send gate, and this client additionally refuses to operate without an
explicitly configured base URL + bot token (LiveSendDisabled — fail closed).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from ..domain.errors import DomainError, LiveSendDisabled, ValidationError
from ..domain.messages import InternalMessage
from .chatwoot import build_create_message_payload, build_toggle_status_payload


class ChatwootApiError(DomainError):
    """Chatwoot API returned an error or was unreachable."""


def parse_conversation_key(key: str) -> tuple[str, str]:
    """`cw-{account_id}-{conversation_id}` -> (account_id, conversation_id)."""
    parts = key.split("-")
    if len(parts) != 3 or parts[0] != "cw" or not parts[1] or not parts[2]:
        raise ValidationError(f"not a Chatwoot conversation key: {key!r}")
    return parts[1], parts[2]


class ChatwootRestChannel:
    channel_name = "chatwoot"

    def __init__(
        self, *, base_url: str, bot_token: str, timeout_seconds: float = 10.0
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._bot_token = bot_token
        self._timeout = timeout_seconds

    @property
    def configured(self) -> bool:
        return bool(self._base_url and self._bot_token)

    def _require_configured(self) -> None:
        if not self.configured:
            raise LiveSendDisabled(
                "Chatwoot REST sending is not configured "
                "(INVAR_CHATWOOT_BASE_URL / INVAR_CHATWOOT_BOT_TOKEN)"
            )

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_configured()
        request = urllib.request.Request(  # noqa: S310 - base URL is operator config
            f"{self._base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Content-Type": "application/json",
                "api_access_token": self._bot_token,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as resp:  # noqa: S310
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            raise ChatwootApiError(
                f"Chatwoot API HTTP {exc.code} for {path}"
            ) from exc
        except urllib.error.URLError as exc:
            raise ChatwootApiError(f"Chatwoot API unreachable: {exc.reason}") from exc
        try:
            parsed = json.loads(raw) if raw else {}
        except json.JSONDecodeError as exc:
            raise ChatwootApiError("Chatwoot API returned non-JSON response") from exc
        return parsed if isinstance(parsed, dict) else {"data": parsed}

    # -- ChannelAdapter port ---------------------------------------------------
    def normalize_inbound(self, payload: dict[str, Any]) -> list[InternalMessage]:
        raise NotImplementedError(
            "Inbound normalization lives in adapters.chatwoot.normalize_event "
            "(signal-based); this client is outbound-only."
        )

    def send_text(self, *, conversation_id: str, external_contact_id: str,
                  text: str) -> str:
        account_id, chatwoot_conversation_id = parse_conversation_key(conversation_id)
        result = self._post(
            f"/api/v1/accounts/{account_id}/conversations/"
            f"{chatwoot_conversation_id}/messages",
            build_create_message_payload(text),
        )
        message_id = result.get("id")
        return f"chatwoot-msg-{message_id}" if message_id is not None else "chatwoot-msg-unknown"

    # -- handoff projection -----------------------------------------------------
    def toggle_status(self, *, conversation_id: str, status: str) -> None:
        account_id, chatwoot_conversation_id = parse_conversation_key(conversation_id)
        self._post(
            f"/api/v1/accounts/{account_id}/conversations/"
            f"{chatwoot_conversation_id}/toggle_status",
            build_toggle_status_payload(status),
        )
