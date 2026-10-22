"""Processing of (already signature-verified, outbox-delivered) Chatwoot events.

This is where Chatwoot signals meet the domain. Safety rules encoded here:

- Chatwoot status is a projection/signal, never the control truth. A
  `pending` signal NEVER resumes the AI by itself (spike R6): resume requires
  an operator Actor resolved out-of-band, which this layer does not invent.
- An operator replying in Chatwoot is fail-safe: if we cannot map them to an
  authorized core Actor yet, the AI still gets blocked (handover requested
  by the AI actor — the safe direction) instead of staying silently active.
- Every state mutation is persisted with compare-and-swap on control_version.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from ..adapters.chatwoot import (
    ChatwootSignal,
    ChatwootSignalKind,
    InboxMapping,
    normalize_event,
)
from ..domain.audit import AuditEvent, AuditEventType, AuditLog
from ..domain.authorization import Actor
from ..domain.conversation import ControlState, Conversation
from ..domain.errors import AISendBlocked
from ..ports.repositories import ConversationRepository
from .conversation_service import ConversationService

# Resolve a Chatwoot user id + product to an authorized core Actor, or None.
OperatorResolver = Callable[[str | None, str], Actor | None]
# Project core state back to Chatwoot (e.g. toggle_status). Optional.
StatusSync = Callable[[str, str], None]


@dataclass(frozen=True)
class ProcessingResult:
    outcome: str
    conversation_key: str
    sent_message_id: str | None = None
    escalated: bool = False
    duplicate: bool = False
    warnings: tuple[str, ...] = field(default_factory=tuple)


class ChatwootEventProcessor:
    def __init__(
        self,
        *,
        service: ConversationService,
        conversations: ConversationRepository,
        audit: AuditLog,
        ai_actor: Actor,
        inboxes: dict[int, InboxMapping],
        operator_resolver: OperatorResolver | None = None,
        status_sync: StatusSync | None = None,
    ) -> None:
        self._service = service
        self._conversations = conversations
        self._audit = audit
        self._ai_actor = ai_actor
        self._inboxes = inboxes
        self._resolve_operator = operator_resolver or (lambda _ref, _pid: None)
        self._status_sync = status_sync

    def process(self, payload: dict[str, Any]) -> ProcessingResult:
        signal = normalize_event(payload, inboxes=self._inboxes)
        handler = {
            ChatwootSignalKind.CUSTOMER_MESSAGE: self._on_customer_message,
            ChatwootSignalKind.OPERATOR_REPLIED: self._on_operator_replied,
            ChatwootSignalKind.STATUS_OPEN: self._on_status_open,
            ChatwootSignalKind.STATUS_PENDING: self._on_status_pending,
        }.get(signal.kind)
        if handler is None:
            return ProcessingResult(f"ignored:{signal.kind}", signal.conversation_key)
        return handler(signal)

    # -- helpers ---------------------------------------------------------------
    def _load_or_create(self, signal: ChatwootSignal) -> tuple[Conversation, int]:
        existing = self._conversations.load(signal.conversation_key)
        if existing is not None:
            return existing, existing.control_version
        if signal.message is None:  # only customer-message signals create rows
            raise ValueError("cannot create conversation without a message")
        conversation = Conversation(
            conversation_id=signal.conversation_key,
            product_id=signal.message.product_id,
            contact=signal.message.contact,
        )
        self._conversations.add(conversation)
        self._audit.record(
            AuditEvent(
                AuditEventType.CONVERSATION_CREATED,
                conversation.product_id,
                conversation.conversation_id,
                self._ai_actor.actor_id,
                detail="origin=chatwoot",
            )
        )
        return conversation, conversation.control_version

    def _sync_status(self, conversation_key: str, status: str,
                     warnings: list[str]) -> None:
        if self._status_sync is None:
            return
        try:
            self._status_sync(conversation_key, status)
        except Exception as exc:  # noqa: BLE001 - projection failure must not undo core safety
            warnings.append(f"status_sync_failed:{type(exc).__name__}:{exc}")

    # -- signal handlers ----------------------------------------------------------
    def _on_customer_message(self, signal: ChatwootSignal) -> ProcessingResult:
        if signal.message is None:
            return ProcessingResult("ignored:no_message", signal.conversation_key)
        conversation, loaded_version = self._load_or_create(signal)
        warnings: list[str] = []
        try:
            result = self._service.handle_inbound(conversation, signal.message)
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
        if conversation.control_version != loaded_version:
            self._conversations.save(conversation, expected_version=loaded_version)
        if escalated:
            self._sync_status(signal.conversation_key, "open", warnings)
        return ProcessingResult(
            outcome, signal.conversation_key, sent_message_id=sent_id,
            escalated=escalated, duplicate=duplicate, warnings=tuple(warnings),
        )

    def _block_ai_fail_safe(self, conversation: Conversation, reason: str) -> bool:
        """Block AI without needing an operator mapping. Returns True if changed."""
        if conversation.state is not ControlState.AI_ACTIVE:
            return False
        conversation.request_handover(self._ai_actor, self._audit, reason=reason)
        return True

    def _on_operator_replied(self, signal: ChatwootSignal) -> ProcessingResult:
        conversation = self._conversations.load(signal.conversation_key)
        if conversation is None:
            return ProcessingResult("ignored:no_conversation", signal.conversation_key)
        loaded_version = conversation.control_version
        operator = self._resolve_operator(signal.actor_ref, conversation.product_id)
        if operator is not None and conversation.state is not ControlState.HUMAN_ACTIVE:
            conversation.accept_handover(operator, self._audit)
            outcome = "takeover_recorded"
        elif self._block_ai_fail_safe(
            conversation, "operator replied in Chatwoot (unmapped identity)"
        ):
            outcome = "ai_blocked_unmapped_operator"
        else:
            outcome = "already_human_controlled"
        if conversation.control_version != loaded_version:
            self._conversations.save(conversation, expected_version=loaded_version)
        return ProcessingResult(outcome, signal.conversation_key)

    def _on_status_open(self, signal: ChatwootSignal) -> ProcessingResult:
        conversation = self._conversations.load(signal.conversation_key)
        if conversation is None:
            return ProcessingResult("ignored:no_conversation", signal.conversation_key)
        loaded_version = conversation.control_version
        changed = self._block_ai_fail_safe(
            conversation, "Chatwoot status=open (human side)")
        if changed:
            self._conversations.save(conversation, expected_version=loaded_version)
        return ProcessingResult(
            "ai_blocked_status_open" if changed else "already_blocked",
            signal.conversation_key,
        )

    def _on_status_pending(self, signal: ChatwootSignal) -> ProcessingResult:
        # Spike R6: a bare status flip carries no trustworthy, authorized actor
        # identity, so it must NOT resume the AI. Resume happens through an
        # explicitly mapped operator action (future operator endpoint).
        return ProcessingResult(
            "resume_signal_ignored:requires_authorized_operator",
            signal.conversation_key,
        )
