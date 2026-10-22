"""Conversation service: the only path from an AI suggestion to a channel send.

Send policy (all must hold, re-checked at send time — fail closed):
1. The AI actor is authorized for AI_SEND in the conversation's product scope.
2. The global AI-send kill-switch is on (config).
3. The conversation is AI_ACTIVE *and* its control_version is unchanged since
   generation started (a human takeover mid-generation blocks the send).
4. The suggestion meets the minimum confidence threshold and is grounded in
   at least one eligible knowledge document (no knowledge -> escalate, never invent).
"""

from __future__ import annotations

from dataclasses import dataclass

from ..domain.audit import AuditEvent, AuditEventType, AuditLog
from ..domain.authorization import Action, Actor
from ..domain.authorization import require as require_auth
from ..domain.conversation import Conversation
from ..domain.errors import AISendBlocked
from ..domain.messages import InternalMessage, MessageDeduplicator
from ..ports.ai_provider import AIProvider, ReplyRequest
from ..ports.channel import ChannelAdapter
from ..ports.knowledge_retrieval import KnowledgeRetriever


@dataclass(frozen=True)
class InboundResult:
    duplicate: bool
    sent_message_id: str | None
    escalated: bool
    reason: str = ""


class ConversationService:
    def __init__(
        self,
        *,
        ai: AIProvider,
        channel: ChannelAdapter,
        knowledge: KnowledgeRetriever,
        audit: AuditLog,
        ai_actor: Actor,
        ai_send_enabled: bool = False,
        min_confidence: float = 0.7,
    ) -> None:
        self._ai = ai
        self._channel = channel
        self._knowledge = knowledge
        self._audit = audit
        self._ai_actor = ai_actor
        self._ai_send_enabled = ai_send_enabled
        self._min_confidence = min_confidence
        self._dedupe = MessageDeduplicator()

    def handle_inbound(
        self, conversation: Conversation, message: InternalMessage
    ) -> InboundResult:
        if message.product_id != conversation.product_id:
            raise AISendBlocked("message product does not match conversation product")

        if self._dedupe.seen(message):
            self._audit.record(
                AuditEvent(
                    AuditEventType.DUPLICATE_IGNORED,
                    conversation.product_id,
                    conversation.conversation_id,
                    self._ai_actor.actor_id,
                    detail=f"external_event_id={message.external_event_id}",
                )
            )
            return InboundResult(duplicate=True, sent_message_id=None, escalated=False,
                                 reason="duplicate event ignored")

        # Capture control version BEFORE generation; re-validated at send time.
        version_at_start = conversation.control_version

        docs = self._knowledge.search(
            product_id=conversation.product_id, query=message.text, limit=3
        )
        if not docs:
            return self._escalate(conversation, "no eligible approved knowledge found")

        require_auth(self._ai_actor, Action.AI_SUGGEST, conversation.product_id)
        suggestion = self._ai.suggest_reply(
            ReplyRequest(
                product_id=conversation.product_id,
                inbound=message,
                knowledge_excerpts=tuple(d.content for d in docs),
            )
        )
        if suggestion.confidence < self._min_confidence:
            return self._escalate(
                conversation,
                f"suggestion confidence {suggestion.confidence:.2f} below threshold "
                f"{self._min_confidence:.2f}",
            )

        # --- send gate (re-checked now, not assumed from generation time) ---
        try:
            require_auth(self._ai_actor, Action.AI_SEND, conversation.product_id)
            if not self._ai_send_enabled:
                raise AISendBlocked("AI sending disabled by configuration kill-switch")
            conversation.assert_ai_may_send(version_at_start)
        except AISendBlocked as exc:
            self._audit.record(
                AuditEvent(
                    AuditEventType.AI_SEND_BLOCKED,
                    conversation.product_id,
                    conversation.conversation_id,
                    self._ai_actor.actor_id,
                    detail=str(exc),
                )
            )
            raise

        sent_id = self._channel.send_text(
            conversation_id=conversation.conversation_id,
            external_contact_id=message.external_contact_id,
            text=suggestion.text,
        )
        self._audit.record(
            AuditEvent(
                AuditEventType.AI_SEND_ALLOWED,
                conversation.product_id,
                conversation.conversation_id,
                self._ai_actor.actor_id,
                detail=f"channel_message_id={sent_id}",
            )
        )
        return InboundResult(duplicate=False, sent_message_id=sent_id, escalated=False)

    def _escalate(self, conversation: Conversation, reason: str) -> InboundResult:
        # Escalation is the fail-safe direction: requesting handover immediately
        # blocks further AI sending until a human acts. The AI cannot undo this
        # (resume requires a human operator/admin — see authorization.py).
        from ..domain.conversation import ControlState

        if conversation.state is ControlState.AI_ACTIVE:
            conversation.request_handover(self._ai_actor, self._audit, reason=reason)
        return InboundResult(
            duplicate=False, sent_message_id=None, escalated=True, reason=reason
        )
