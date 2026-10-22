"""Standardized internal message contract (schema version 1).

Design rules (see docs/architecture/message-contract.md):
- Identity is always scoped: a contact ID is unique only within
  (product_id, channel, channel_account_id) — never assumed globally unique.
- Every inbound event carries a deterministic idempotency key so webhook
  redeliveries and retries can be deduplicated.
- Content from external systems is untrusted data, never instructions.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from .errors import ValidationError

SCHEMA_VERSION = 1

_SLUG = re.compile(r"^[a-z0-9][a-z0-9_-]{1,62}$")


def _require_slug(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not _SLUG.match(value):
        raise ValidationError(f"{field_name} must be a slug like 'damiish', got {value!r}")
    return value


def _require_nonempty(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field_name} must be a non-empty string")
    return value


def _require_aware(ts: datetime, field_name: str) -> datetime:
    if ts.tzinfo is None or ts.utcoffset() is None:
        raise ValidationError(f"{field_name} must be timezone-aware (UTC expected)")
    return ts.astimezone(UTC)


class Channel(StrEnum):
    INSTAGRAM = "instagram"
    WEBSITE_CHAT = "website_chat"
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"
    EMAIL = "email"
    FAKE = "fake"  # tests / local exercise only


class Direction(StrEnum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class ContentType(StrEnum):
    TEXT = "text"
    COMMENT = "comment"
    REACTION = "reaction"
    SYSTEM = "system"


class ProcessingStatus(StrEnum):
    RECEIVED = "received"
    NORMALIZED = "normalized"
    PROCESSED = "processed"
    IGNORED_DUPLICATE = "ignored_duplicate"
    FAILED = "failed"


class DeliveryStatus(StrEnum):
    NOT_APPLICABLE = "not_applicable"  # inbound messages
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    BLOCKED = "blocked"  # e.g. AI send blocked by human takeover


@dataclass(frozen=True)
class ContactRef:
    """An external contact, scoped to one connected account on one channel."""

    channel: Channel
    channel_account_id: str
    external_contact_id: str

    def __post_init__(self) -> None:
        _require_nonempty(self.channel_account_id, "channel_account_id")
        _require_nonempty(self.external_contact_id, "external_contact_id")

    @property
    def scoped_key(self) -> str:
        return f"{self.channel}:{self.channel_account_id}:{self.external_contact_id}"


@dataclass(frozen=True)
class InternalMessage:
    """Versioned internal representation of one inbound or outbound message/event."""

    product_id: str
    channel: Channel
    channel_account_id: str
    external_contact_id: str
    conversation_id: str
    external_event_id: str
    direction: Direction
    content_type: ContentType
    occurred_at: datetime
    text: str = ""
    external_message_id: str | None = None
    processing_status: ProcessingStatus = ProcessingStatus.RECEIVED
    delivery_status: DeliveryStatus = DeliveryStatus.NOT_APPLICABLE
    schema_version: int = SCHEMA_VERSION
    correlation_id: str = ""
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_slug(self.product_id, "product_id")
        _require_nonempty(self.channel_account_id, "channel_account_id")
        _require_nonempty(self.external_contact_id, "external_contact_id")
        _require_nonempty(self.conversation_id, "conversation_id")
        _require_nonempty(self.external_event_id, "external_event_id")
        object.__setattr__(self, "occurred_at", _require_aware(self.occurred_at, "occurred_at"))
        if self.schema_version != SCHEMA_VERSION:
            raise ValidationError(
                f"unsupported schema_version {self.schema_version}, expected {SCHEMA_VERSION}"
            )
        if self.content_type in (ContentType.TEXT, ContentType.COMMENT) and not self.text.strip():
            raise ValidationError("text/comment messages must have non-empty text")
        if self.direction is Direction.INBOUND and self.delivery_status is not (
            DeliveryStatus.NOT_APPLICABLE
        ):
            raise ValidationError("inbound messages must have delivery_status=not_applicable")

    @property
    def contact(self) -> ContactRef:
        return ContactRef(
            channel=self.channel,
            channel_account_id=self.channel_account_id,
            external_contact_id=self.external_contact_id,
        )

    @property
    def idempotency_key(self) -> str:
        """Deterministic key for deduplication of redelivered events.

        Scoped by product + channel + connected account + external event id,
        so identical platform IDs on different accounts never collide.
        """
        raw = "|".join(
            [self.product_id, str(self.channel), self.channel_account_id, self.external_event_id]
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class MessageDeduplicator:
    """In-memory idempotency registry (persistence arrives with the DB adapter).

    `seen()` returns True exactly once per idempotency key.
    """

    def __init__(self) -> None:
        self._keys: set[str] = set()

    def seen(self, message: InternalMessage) -> bool:
        key = message.idempotency_key
        if key in self._keys:
            return True
        self._keys.add(key)
        return False
