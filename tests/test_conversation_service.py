import pytest
from helpers import AI, OPERATOR, make_conversation, make_doc, make_message

from invar_comms.adapters.fakes import FakeAIProvider, FakeChannelAdapter
from invar_comms.application.conversation_service import ConversationService
from invar_comms.domain.audit import AuditEventType, InMemoryAuditLog
from invar_comms.domain.conversation import ControlState
from invar_comms.domain.errors import AISendBlocked
from invar_comms.ports.knowledge_retrieval import InMemoryKnowledgeRetriever


def build_service(**overrides: object) -> tuple[ConversationService, FakeChannelAdapter,
                                                InMemoryAuditLog]:
    audit = InMemoryAuditLog()
    channel = FakeChannelAdapter()
    kwargs: dict[str, object] = dict(
        ai=FakeAIProvider(), channel=channel,
        knowledge=InMemoryKnowledgeRetriever([make_doc()]),
        audit=audit, ai_actor=AI, ai_send_enabled=True,
    )
    kwargs.update(overrides)
    return ConversationService(**kwargs), channel, audit  # type: ignore[arg-type]


def test_happy_path_sends_once_and_audits() -> None:
    service, channel, audit = build_service()
    result = service.handle_inbound(make_conversation(), make_message())
    assert result.sent_message_id == "fake-msg-1"
    assert len(channel.sent) == 1
    assert audit.events[-1].event_type is AuditEventType.AI_SEND_ALLOWED


def test_duplicate_webhook_delivery_is_ignored() -> None:
    service, channel, _ = build_service()
    conv, msg = make_conversation(), make_message()
    service.handle_inbound(conv, msg)
    second = service.handle_inbound(conv, msg)
    assert second.duplicate is True
    assert len(channel.sent) == 1


def test_kill_switch_off_blocks_send_and_audits() -> None:
    service, channel, audit = build_service(ai_send_enabled=False)
    with pytest.raises(AISendBlocked):
        service.handle_inbound(make_conversation(), make_message())
    assert channel.sent == []
    assert audit.events[-1].event_type is AuditEventType.AI_SEND_BLOCKED


def test_human_takeover_blocks_ai_send() -> None:
    service, channel, audit = build_service()
    conv = make_conversation()
    conv.accept_handover(OPERATOR, audit)
    with pytest.raises(AISendBlocked):
        service.handle_inbound(conv, make_message())
    assert channel.sent == []


def test_no_approved_knowledge_escalates_instead_of_inventing() -> None:
    service, channel, _ = build_service(knowledge=InMemoryKnowledgeRetriever([]))
    conv = make_conversation()
    result = service.handle_inbound(conv, make_message())
    assert result.escalated is True
    assert result.sent_message_id is None
    assert channel.sent == []
    assert conv.state is ControlState.HANDOVER_REQUESTED  # AI silenced until human acts


def test_low_confidence_escalates() -> None:
    service, channel, _ = build_service(ai=FakeAIProvider(confidence=0.2))
    result = service.handle_inbound(make_conversation(), make_message())
    assert result.escalated is True
    assert channel.sent == []
