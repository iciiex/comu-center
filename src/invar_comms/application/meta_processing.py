"""Processing of (signature-verified, outbox-delivered) Meta webhook events.

Direct-Instagram path (ADR-0010): each customer message flows through the
same ConversationService send gate as every other channel, with the Meta
Graph adapter as its channel. Echoes are dropped (loop guard); unsupported
items are recorded as ignored outcomes. Blocked/unconfigured sends are job
outcomes, not job failures — retrying them would not change operator intent.
"""

from __future__ import annotations

from typing import Any

from ..adapters.meta_instagram import (
    MetaSignal,
    MetaSignalKind,
    normalize_meta_event,
)
from ..domain.audit import AuditEvent, AuditEventType, AuditLog
from ..domain.authorization import Actor
from ..domain.conversation import Conversation
from ..domain.errors import AISendBlocked, LiveSendDisabled
from ..ports.repositories import ConversationRepository
from .chatwoot_processing import ProcessingResult
from .conversation_service import ConversationService


class MetaEventProcessor:
    def __init__(
        self,
        *,
        service: ConversationService,
        conversations: ConversationRepository,
        audit: AuditLog,
        ai_actor: Actor,
        account_products: dict[str, str],
    ) -> None:
        self._service = service
        self._conversations = conversations
        self._audit = audit
        self._ai_actor = ai_actor
        self._account_products = account_products

    def process(self, payload: dict[str, Any]) -> list[ProcessingResult]:
        results: list[ProcessingResult] = []
        for signal in normalize_meta_event(
                payload, account_products=self._account_products):
            if signal.kind is not MetaSignalKind.CUSTOMER_MESSAGE:
                results.append(ProcessingResult(
                    f"ignored:{signal.kind}", signal.conversation_key))
                continue
            results.append(self._on_customer_message(signal))
        return results

    def _on_customer_message(self, signal: MetaSignal) -> ProcessingResult:
        message = signal.message
        if message is None:
            return ProcessingResult("ignored:no_message", signal.conversation_key)
        conversation = self._conversations.load(signal.conversation_key)
        if conversation is None:
            conversation = Conversation(
                conversation_id=signal.conversation_key,
                product_id=message.product_id,
                contact=message.contact,
            )
            self._conversations.add(conversation)
            self._audit.record(AuditEvent(
                AuditEventType.CONVERSATION_CREATED, conversation.product_id,
                conversation.conversation_id, self._ai_actor.actor_id,
                detail="origin=meta_instagram"))
        loaded_version = conversation.control_version
        try:
            result = self._service.handle_inbound(conversation, message)
            outcome = (
                "duplicate" if result.duplicate
                else "escalated" if result.escalated
                else "replied"
            )
            sent_id, escalated, duplicate = (
                result.sent_message_id, result.escalated, result.duplicate)
        except AISendBlocked as exc:
            outcome, sent_id, escalated, duplicate = (
                f"ai_blocked:{exc}", None, False, False)
        except LiveSendDisabled as exc:
            outcome, sent_id, escalated, duplicate = (
                f"send_not_configured:{exc}", None, False, False)
        if conversation.control_version != loaded_version:
            self._conversations.save(conversation, expected_version=loaded_version)
        return ProcessingResult(
            outcome, signal.conversation_key, sent_message_id=sent_id,
            escalated=escalated, duplicate=duplicate)
