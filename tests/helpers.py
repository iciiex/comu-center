"""Shared test fixtures (plain helpers, no pytest magic needed)."""

from __future__ import annotations

from datetime import UTC, datetime

from invar_comms.domain.authorization import Actor, Role
from invar_comms.domain.conversation import Conversation
from invar_comms.domain.knowledge import (
    ApprovalStatus,
    KnowledgeDocument,
    Sensitivity,
)
from invar_comms.domain.messages import (
    Channel,
    ContactRef,
    ContentType,
    Direction,
    InternalMessage,
)

NOW = datetime(2026, 10, 22, 10, 0, tzinfo=UTC)

OPERATOR = Actor("op-1", Role.OPERATOR, frozenset({"damiish"}))
ADMIN = Actor("admin-1", Role.ADMIN, frozenset({"damiish", "maygoosh"}))
APPROVER = Actor("approver-1", Role.CONTENT_APPROVER, frozenset({"damiish"}))
AI = Actor("ai-damiish", Role.AI_SYSTEM, frozenset({"damiish"}))
OTHER_PRODUCT_OPERATOR = Actor("op-other", Role.OPERATOR, frozenset({"maygoosh"}))


def make_message(**overrides: object) -> InternalMessage:
    base: dict[str, object] = dict(
        product_id="damiish",
        channel=Channel.INSTAGRAM,
        channel_account_id="ig-acct-1",
        external_contact_id="ig-user-42",
        conversation_id="conv-1",
        external_event_id="evt-1",
        direction=Direction.INBOUND,
        content_type=ContentType.TEXT,
        occurred_at=NOW,
        text="How do I register a new animal?",
    )
    base.update(overrides)
    return InternalMessage(**base)  # type: ignore[arg-type]


def make_conversation(**overrides: object) -> Conversation:
    base: dict[str, object] = dict(
        conversation_id="conv-1",
        product_id="damiish",
        contact=ContactRef(Channel.INSTAGRAM, "ig-acct-1", "ig-user-42"),
    )
    base.update(overrides)
    return Conversation(**base)  # type: ignore[arg-type]


def make_doc(**overrides: object) -> KnowledgeDocument:
    base: dict[str, object] = dict(
        document_id="faq-animal-registration",
        version=1,
        product_id="damiish",
        title="Registering an animal",
        content="To register a new animal, open the herd screen and choose Add animal.",
        source="DAMIISH operator guide (approved extract)",
        status=ApprovalStatus.APPROVED,
        sensitivity=Sensitivity.PUBLIC_FAQ,
        updated_at=NOW,
        approved_by="approver-1",
        approved_at=NOW,
    )
    base.update(overrides)
    return KnowledgeDocument(**base)  # type: ignore[arg-type]
