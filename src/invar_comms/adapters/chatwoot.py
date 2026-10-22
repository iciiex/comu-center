"""Chatwoot Agent Bot adapter — mapping layer only (no network calls).

Integration model (ADR-0007, spike docs/spikes/0001-chatwoot-ce.md):
Chatwoot CE owns the Instagram channel and operator inbox; the Invar core
attaches as a Chatwoot *Agent Bot*. Chatwoot posts signed webhook events to
us; we reply / hand off through its REST API. This module implements the
pure, testable parts:

- verification of Chatwoot's signed webhooks
  (`X-Chatwoot-Signature: sha256=HMAC-SHA256(secret, "{timestamp}.{raw_body}")`,
  `X-Chatwoot-Timestamp`, per current Chatwoot docs — re-verify secret source
  and behavior against the pinned deployment, see spike risks R2);
- normalization of Chatwoot events into domain signals. Chatwoot's
  conversation status is a *projection* — the core state machine stays the
  authority, and no webhook can directly mutate it;
- builders for outbound REST payloads (no HTTP client is faked here; the
  transport arrives with the HTTP task).
"""

from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from ..domain.errors import ValidationError
from ..domain.messages import (
    Channel,
    ContentType,
    Direction,
    InternalMessage,
)

SIGNATURE_TOLERANCE_SECONDS = 300
INSTAGRAM_MAX_MESSAGE_CHARS = 1000  # per Chatwoot supported-features docs


def verify_chatwoot_signature(
    *,
    raw_body: bytes,
    signature_header: str | None,
    timestamp_header: str | None,
    secret: str,
    now_epoch: float | None = None,
) -> None:
    """Verify a signed Chatwoot webhook. Raises ValidationError (fail closed).

    Checks signature form, timestamp freshness (replay defence), and HMAC over
    the raw body with a constant-time comparison.
    """
    if not secret:
        raise ValidationError("Chatwoot webhook secret is not configured")
    if not signature_header or not signature_header.startswith("sha256="):
        raise ValidationError("missing or malformed X-Chatwoot-Signature header")
    if not timestamp_header:
        raise ValidationError("missing X-Chatwoot-Timestamp header")
    try:
        ts = int(timestamp_header)
    except ValueError as exc:
        raise ValidationError("malformed X-Chatwoot-Timestamp header") from exc
    now = time.time() if now_epoch is None else now_epoch
    if abs(now - ts) > SIGNATURE_TOLERANCE_SECONDS:
        raise ValidationError("Chatwoot webhook timestamp outside tolerance window")
    signed = f"{timestamp_header}.".encode() + raw_body
    expected = "sha256=" + hmac.new(
        secret.encode("utf-8"), signed, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, signature_header):
        raise ValidationError("Chatwoot webhook signature verification failed")


class ChatwootSignalKind(StrEnum):
    CUSTOMER_MESSAGE = "customer_message"
    OPERATOR_REPLIED = "operator_replied"      # human is active -> ensure takeover
    BOT_ECHO = "bot_echo"                      # our own send, ignore (loop guard)
    PRIVATE_NOTE = "private_note"              # internal note, ignore for customers
    STATUS_OPEN = "status_open"                # Chatwoot: humans own it
    STATUS_PENDING = "status_pending"          # Chatwoot: returned to bot queue
    STATUS_OTHER = "status_other"
    IGNORED = "ignored"


@dataclass(frozen=True)
class InboxMapping:
    """Explicit product binding for one Chatwoot inbox (fail closed if unknown)."""

    product_id: str
    channel: Channel
    channel_account_id: str


@dataclass(frozen=True)
class ChatwootSignal:
    kind: ChatwootSignalKind
    conversation_key: str  # deterministic Invar conversation id: cw-{account}-{conv}
    message: InternalMessage | None = None
    detail: str = ""


def _parse_timestamp(value: object) -> datetime:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=UTC)
    if isinstance(value, str) and value.strip():
        text = value.strip()
        try:
            return datetime.fromtimestamp(float(text), tz=UTC)
        except ValueError:
            pass
        for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z",
                    "%Y-%m-%d %H:%M:%S %Z"):
            try:
                parsed = datetime.strptime(text.replace("Z", "+0000"), fmt)
                return parsed.astimezone(UTC)
            except ValueError:
                continue
    raise ValidationError(f"unsupported Chatwoot timestamp: {value!r}")


def conversation_key(account_id: object, conversation_id: object) -> str:
    if account_id is None or conversation_id is None:
        raise ValidationError("Chatwoot event missing account/conversation id")
    return f"cw-{account_id}-{conversation_id}"


def normalize_event(
    payload: dict[str, Any], *, inboxes: dict[int, InboxMapping]
) -> ChatwootSignal:
    """Map one (signature-verified) Chatwoot webhook payload to a core signal.

    Unknown inboxes, unknown shapes, and anything ambiguous fail closed with
    ValidationError rather than being guessed at.
    """
    if not isinstance(payload, dict):
        raise ValidationError("Chatwoot payload must be an object")
    event = payload.get("event")
    account = payload.get("account") or {}
    conversation = payload.get("conversation") or {}

    conv_id = conversation.get("id", payload.get("id") if event and
                               str(event).startswith("conversation_") else None)
    if event == "message_created":
        conv_id = conversation.get("id")
    key = conversation_key(account.get("id", payload.get("account_id")), conv_id)

    if event == "conversation_status_changed":
        status = str(payload.get("status") or conversation.get("status") or "")
        kind = {
            "open": ChatwootSignalKind.STATUS_OPEN,
            "pending": ChatwootSignalKind.STATUS_PENDING,
        }.get(status, ChatwootSignalKind.STATUS_OTHER)
        return ChatwootSignal(kind, key, detail=f"chatwoot_status={status}")

    if event != "message_created":
        return ChatwootSignal(ChatwootSignalKind.IGNORED, key,
                              detail=f"event={event!r}")

    if payload.get("private") is True:
        return ChatwootSignal(ChatwootSignalKind.PRIVATE_NOTE, key)

    sender = payload.get("sender") or {}
    sender_type = str(sender.get("type") or "").lower()
    if sender_type == "agent_bot":
        return ChatwootSignal(ChatwootSignalKind.BOT_ECHO, key)

    message_type = str(payload.get("message_type") or "").lower()
    if message_type == "outgoing" or sender_type == "user":
        return ChatwootSignal(
            ChatwootSignalKind.OPERATOR_REPLIED, key,
            detail=f"operator_chatwoot_id={sender.get('id')}",
        )
    if message_type != "incoming":
        return ChatwootSignal(ChatwootSignalKind.IGNORED, key,
                              detail=f"message_type={message_type!r}")

    inbox_id_raw = conversation.get("inbox_id") or (payload.get("inbox") or {}).get("id")
    try:
        inbox_id = int(inbox_id_raw)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise ValidationError("Chatwoot event missing inbox id") from exc
    mapping = inboxes.get(inbox_id)
    if mapping is None:
        raise ValidationError(f"no product mapping for Chatwoot inbox {inbox_id}")

    contact_inbox = conversation.get("contact_inbox") or {}
    external_contact_id = (
        contact_inbox.get("source_id") or sender.get("id") or payload.get("source_id")
    )
    if external_contact_id is None:
        raise ValidationError("Chatwoot event missing contact identifier")
    message_id = payload.get("id")
    if message_id is None:
        raise ValidationError("Chatwoot event missing message id")

    message = InternalMessage(
        product_id=mapping.product_id,
        channel=mapping.channel,
        channel_account_id=mapping.channel_account_id,
        external_contact_id=str(external_contact_id),
        conversation_id=key,
        external_event_id=f"chatwoot-msg-{message_id}",
        external_message_id=str(payload.get("source_id") or message_id),
        direction=Direction.INBOUND,
        content_type=ContentType.TEXT,
        occurred_at=_parse_timestamp(payload.get("created_at")),
        text=str(payload.get("content") or ""),
        metadata={"origin": "chatwoot_agent_bot"},
    )
    return ChatwootSignal(ChatwootSignalKind.CUSTOMER_MESSAGE, key, message=message)


# -- outbound REST payload builders (transport deferred, nothing faked) ------

def build_create_message_payload(text: str) -> dict[str, Any]:
    """Payload for POST /api/v1/accounts/{id}/conversations/{id}/messages."""
    cleaned = text.strip()
    if not cleaned:
        raise ValidationError("outgoing message text must be non-empty")
    if len(cleaned) > INSTAGRAM_MAX_MESSAGE_CHARS:
        raise ValidationError(
            f"message exceeds Instagram limit of {INSTAGRAM_MAX_MESSAGE_CHARS} chars"
        )
    return {"content": cleaned, "message_type": "outgoing", "private": False}


def build_toggle_status_payload(status: str) -> dict[str, Any]:
    """Payload for POST .../conversations/{id}/toggle_status (handoff control)."""
    if status not in {"open", "pending", "resolved", "snoozed"}:
        raise ValidationError(f"unsupported Chatwoot status {status!r}")
    return {"status": status}
