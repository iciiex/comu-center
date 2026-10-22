"""Meta / Instagram adapter (official Graph API only — ADR-0006/0010).

Implemented and unit-tested here:
- Webhook subscription handshake + `X-Hub-Signature-256` HMAC-SHA256
  verification over the raw request body (constant-time).
- Normalization of Instagram `messages` webhook events into InternalMessage
  signals, per the official payload shape
  (`object=instagram`, `entry[].messaging[]` with sender/recipient ids,
  millisecond timestamp, and `message.mid/text/is_echo`).
- Sending text via `POST {graph}/{version}/{ig_id}/messages` on
  graph.instagram.com (Instagram Login route; host/version configurable so
  the Facebook-Login route can reuse it). Sending refuses to run unless the
  explicit live switch is on AND a token + IG account id are configured.

Still NOT done here: real-account verification (needs the owner's Meta app,
permissions and test users — docs/operations/instagram-ai-setup-fa.md),
comments, reactions, media. Unknown shapes fail closed or are ignored with a
recorded reason — never guessed.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from ..domain.errors import DomainError, LiveSendDisabled, ValidationError
from ..domain.messages import (
    Channel,
    ContentType,
    Direction,
    InternalMessage,
)

_SIGNATURE_PREFIX = "sha256="
INSTAGRAM_MAX_TEXT_BYTES = 1000  # official limit: message text <= 1000 bytes UTF-8


class MetaApiError(DomainError):
    """Meta Graph API returned an error or was unreachable."""


class MetaSignalKind(StrEnum):
    CUSTOMER_MESSAGE = "customer_message"
    ECHO = "echo"  # our own outbound message echoed back — loop guard
    IGNORED = "ignored"


@dataclass(frozen=True)
class MetaSignal:
    kind: MetaSignalKind
    conversation_key: str
    message: InternalMessage | None = None
    detail: str = ""


def verify_webhook_subscription(
    *, mode: str | None, verify_token: str | None, challenge: str | None,
    expected_token: str,
) -> str:
    """Return the challenge to echo back, or raise ValidationError (fail closed)."""
    if not expected_token:
        raise ValidationError("webhook verify token is not configured")
    if mode != "subscribe" or not challenge:
        raise ValidationError("invalid webhook verification request")
    if verify_token is None or not hmac.compare_digest(verify_token, expected_token):
        raise ValidationError("webhook verify token mismatch")
    return challenge


def verify_payload_signature(
    *, raw_body: bytes, signature_header: str | None, app_secret: str
) -> None:
    """Verify X-Hub-Signature-256 over the raw body. Raises ValidationError.

    Must be called with the exact raw bytes received — re-serialized JSON
    breaks the HMAC. A missing secret or header is a hard failure.
    """
    if not app_secret:
        raise ValidationError("Meta app secret is not configured")
    if not signature_header or not signature_header.startswith(_SIGNATURE_PREFIX):
        raise ValidationError("missing or malformed X-Hub-Signature-256 header")
    provided = signature_header[len(_SIGNATURE_PREFIX):]
    expected = hmac.new(app_secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(provided, expected):
        raise ValidationError("webhook signature verification failed")


def _conversation_key(account_id: str, contact_id: str) -> str:
    return f"ig-{account_id}-{contact_id}"


def normalize_meta_event(
    payload: dict[str, Any], *, account_products: dict[str, str]
) -> list[MetaSignal]:
    """Map a (signature-verified) Meta webhook payload into core signals.

    `account_products` maps our connected IG account id -> product_id.
    Events for unmapped accounts, non-text messages, comments (`changes`),
    reactions, seen receipts etc. become IGNORED signals with a reason —
    nothing is guessed. malformed envelopes raise ValidationError.
    """
    if not isinstance(payload, dict) or payload.get("object") not in {"instagram", "page"}:
        raise ValidationError("unsupported Meta webhook payload object")
    entries = payload.get("entry")
    if not isinstance(entries, list):
        raise ValidationError("Meta webhook payload missing entry list")

    signals: list[MetaSignal] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        account_id = str(entry.get("id") or "")
        messaging = entry.get("messaging")
        if not isinstance(messaging, list):
            signals.append(MetaSignal(
                MetaSignalKind.IGNORED, _conversation_key(account_id or "?", "?"),
                detail="non-messaging entry (e.g. comments/changes) — out of scope"))
            continue
        for item in messaging:
            if not isinstance(item, dict):
                continue
            sender_id = str((item.get("sender") or {}).get("id") or "")
            recipient_id = str((item.get("recipient") or {}).get("id") or "")
            account = recipient_id or account_id
            message = item.get("message")
            if not isinstance(message, dict) or not sender_id or not account:
                signals.append(MetaSignal(
                    MetaSignalKind.IGNORED,
                    _conversation_key(account or "?", sender_id or "?"),
                    detail="non-message messaging item (seen/reaction/postback...)"))
                continue
            key = _conversation_key(account, sender_id)
            if message.get("is_echo") is True:
                signals.append(MetaSignal(MetaSignalKind.ECHO, key))
                continue
            text = message.get("text")
            if not isinstance(text, str) or not text.strip():
                signals.append(MetaSignal(
                    MetaSignalKind.IGNORED, key,
                    detail="message without text (media/attachments not handled yet)"))
                continue
            product_id = account_products.get(account)
            if product_id is None:
                signals.append(MetaSignal(
                    MetaSignalKind.IGNORED, key,
                    detail=f"unmapped IG account {account!r} (INVAR_META_ACCOUNT_MAP)"))
                continue
            timestamp_ms = item.get("timestamp")
            if not isinstance(timestamp_ms, (int, float)):
                raise ValidationError("Meta messaging item missing numeric timestamp")
            mid = str(message.get("mid") or f"{int(timestamp_ms)}-{sender_id}")
            signals.append(MetaSignal(
                MetaSignalKind.CUSTOMER_MESSAGE, key,
                message=InternalMessage(
                    product_id=product_id,
                    channel=Channel.INSTAGRAM,
                    channel_account_id=account,
                    external_contact_id=sender_id,
                    conversation_id=key,
                    external_event_id=f"meta-{mid}",
                    external_message_id=mid,
                    direction=Direction.INBOUND,
                    content_type=ContentType.TEXT,
                    occurred_at=datetime.fromtimestamp(
                        float(timestamp_ms) / 1000.0, tz=UTC),
                    text=text,
                    metadata={"origin": "meta_instagram"},
                )))
    return signals


class MetaInstagramAdapter:
    """Official Graph API channel adapter (Instagram Login route by default)."""

    channel_name = "instagram"

    def __init__(
        self,
        *,
        access_token: str = "",
        ig_account_id: str = "",
        graph_base_url: str = "https://graph.instagram.com",
        api_version: str = "v25.0",
        live_send_enabled: bool = False,
        account_products: dict[str, str] | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._access_token = access_token
        self._ig_account_id = ig_account_id
        self._graph_base_url = graph_base_url.rstrip("/")
        self._api_version = api_version.strip("/")
        self._live_send_enabled = live_send_enabled
        self._account_products = dict(account_products or {})
        self._timeout = timeout_seconds

    @property
    def can_send(self) -> bool:
        return bool(
            self._live_send_enabled and self._access_token and self._ig_account_id)

    def normalize_inbound(self, payload: dict[str, Any]) -> list[InternalMessage]:
        return [
            signal.message for signal in normalize_meta_event(
                payload, account_products=self._account_products)
            if signal.message is not None
        ]

    def send_text(self, *, conversation_id: str, external_contact_id: str,
                  text: str) -> str:
        if not self.can_send:
            raise LiveSendDisabled(
                "Live Instagram sending is disabled or unconfigured "
                "(INVAR_META_LIVE_SEND_ENABLED + INVAR_META_ACCESS_TOKEN + "
                "INVAR_META_IG_ACCOUNT_ID required — see "
                "docs/operations/instagram-ai-setup-fa.md)."
            )
        cleaned = text.strip()
        if not cleaned:
            raise ValidationError("outgoing message text must be non-empty")
        if len(cleaned.encode("utf-8")) > INSTAGRAM_MAX_TEXT_BYTES:
            raise ValidationError(
                f"message exceeds Instagram limit of {INSTAGRAM_MAX_TEXT_BYTES} bytes")
        url = (f"{self._graph_base_url}/{self._api_version}/"
               f"{self._ig_account_id}/messages")
        body = {
            "recipient": {"id": external_contact_id},
            "messaging_type": "RESPONSE",
            "message": {"text": cleaned},
        }
        request = urllib.request.Request(  # noqa: S310 - operator-configured Meta host
            url, data=json.dumps(body).encode("utf-8"), method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._access_token}",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as resp:  # noqa: S310
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:300] if exc.fp else ""
            raise MetaApiError(f"Meta Graph API HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise MetaApiError(f"Meta Graph API unreachable: {exc.reason}") from exc
        try:
            parsed = json.loads(raw) if raw else {}
        except json.JSONDecodeError as exc:
            raise MetaApiError("Meta Graph API returned non-JSON response") from exc
        message_id = parsed.get("message_id") if isinstance(parsed, dict) else None
        return str(message_id or "meta-msg-unknown")
