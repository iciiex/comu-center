"""Audit events: append-only record of control changes and send decisions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol

from .messages import _require_aware, _require_nonempty, _require_slug


class AuditEventType(StrEnum):
    CONVERSATION_CREATED = "conversation_created"
    HANDOVER_REQUESTED = "handover_requested"
    HUMAN_TOOK_OVER = "human_took_over"
    AI_RESUMED = "ai_resumed"
    AI_SEND_ALLOWED = "ai_send_allowed"
    AI_SEND_BLOCKED = "ai_send_blocked"
    HUMAN_SENT = "human_sent"
    KNOWLEDGE_APPROVED = "knowledge_approved"
    DUPLICATE_IGNORED = "duplicate_ignored"


@dataclass(frozen=True)
class AuditEvent:
    event_type: AuditEventType
    product_id: str
    conversation_id: str
    actor_id: str
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    detail: str = ""

    def __post_init__(self) -> None:
        _require_slug(self.product_id, "product_id")
        _require_nonempty(self.conversation_id, "conversation_id")
        _require_nonempty(self.actor_id, "actor_id")
        object.__setattr__(self, "occurred_at", _require_aware(self.occurred_at, "occurred_at"))


class AuditLog(Protocol):
    def record(self, event: AuditEvent) -> None: ...


class InMemoryAuditLog:
    """Test/local audit sink. A persistent, append-only store replaces this later."""

    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def record(self, event: AuditEvent) -> None:
        self.events.append(event)
