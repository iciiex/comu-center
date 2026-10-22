"""Meta / Instagram adapter — PREPARATION ONLY. No live integration exists yet.

Implemented (and unit-tested) here:
- Webhook subscription handshake check (hub.mode / hub.verify_token / hub.challenge)
  using a constant-time token comparison.
- Webhook payload authenticity: `X-Hub-Signature-256` HMAC-SHA256 verification
  over the *raw* request body, constant-time comparison.

Explicitly NOT implemented:
- Live message sending (raises LiveSendDisabled).
- Payload normalization beyond a defensive skeleton — field-level mapping must
  be verified against current official Meta documentation with a real test app
  (see docs/integrations/meta-instagram.md). Unknown shapes fail closed.
"""

from __future__ import annotations

import hashlib
import hmac
from typing import Any

from ..domain.errors import LiveSendDisabled, ValidationError
from ..domain.messages import InternalMessage

_SIGNATURE_PREFIX = "sha256="


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


class MetaInstagramAdapter:
    """Skeleton adapter. Live sending is disabled by design in the foundation."""

    channel_name = "instagram"

    def __init__(self, *, live_send_enabled: bool = False) -> None:
        self._live_send_enabled = live_send_enabled

    def normalize_inbound(self, payload: dict[str, Any]) -> list[InternalMessage]:
        # Defensive skeleton: only the envelope is checked. Field-level mapping
        # is intentionally deferred until verified against official Meta docs
        # with an approved test app — inventing its shape here would be faking it.
        if not isinstance(payload, dict) or payload.get("object") not in {"instagram", "page"}:
            raise ValidationError("unsupported Meta webhook payload object")
        raise ValidationError(
            "Meta payload normalization is not implemented yet (pending "
            "verification against official Meta docs — see "
            "docs/integrations/meta-instagram.md)"
        )

    def send_text(self, *, conversation_id: str, external_contact_id: str, text: str) -> str:
        raise LiveSendDisabled(
            "Live Instagram sending is not implemented in the foundation. "
            "It requires an approved Meta app, permissions, and an explicitly "
            "configured test environment (see docs/integrations/meta-instagram.md)."
        )
