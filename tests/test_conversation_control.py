import pytest
from helpers import AI, OPERATOR, OTHER_PRODUCT_OPERATOR, make_conversation

from invar_comms.domain.audit import AuditEventType, InMemoryAuditLog
from invar_comms.domain.conversation import ControlState
from invar_comms.domain.errors import (
    AISendBlocked,
    AuthorizationError,
    InvalidStateTransition,
)


def test_handover_request_immediately_blocks_ai() -> None:
    conv, audit = make_conversation(), InMemoryAuditLog()
    assert conv.ai_send_allowed is True
    conv.request_handover(OPERATOR, audit, reason="pricing question")
    assert conv.state is ControlState.HANDOVER_REQUESTED
    assert conv.ai_send_allowed is False
    assert conv.control_version == 1
    assert audit.events[-1].event_type is AuditEventType.HANDOVER_REQUESTED


def test_full_takeover_and_explicit_resume_cycle() -> None:
    conv, audit = make_conversation(), InMemoryAuditLog()
    conv.request_handover(OPERATOR, audit)
    conv.accept_handover(OPERATOR, audit)
    assert conv.state is ControlState.HUMAN_ACTIVE
    assert conv.human_owner_id == "op-1"
    with pytest.raises(AISendBlocked):
        conv.assert_ai_may_send(conv.control_version)
    conv.resume_ai(OPERATOR, audit)
    assert conv.state is ControlState.AI_ACTIVE
    assert conv.human_owner_id is None
    assert [e.event_type for e in audit.events] == [
        AuditEventType.HANDOVER_REQUESTED,
        AuditEventType.HUMAN_TOOK_OVER,
        AuditEventType.AI_RESUMED,
    ]


def test_ai_cannot_resume_itself_or_take_over() -> None:
    conv, audit = make_conversation(), InMemoryAuditLog()
    conv.accept_handover(OPERATOR, audit)
    with pytest.raises(AuthorizationError):
        conv.resume_ai(AI, audit)
    fresh = make_conversation()
    with pytest.raises(AuthorizationError):
        fresh.accept_handover(AI, audit)


def test_wrong_product_actor_is_rejected() -> None:
    conv, audit = make_conversation(), InMemoryAuditLog()
    with pytest.raises(AuthorizationError):
        conv.accept_handover(OTHER_PRODUCT_OPERATOR, audit)


def test_takeover_during_generation_blocks_send_via_version() -> None:
    conv, audit = make_conversation(), InMemoryAuditLog()
    version_at_generation_start = conv.control_version
    conv.accept_handover(OPERATOR, audit)  # human grabs it mid-generation
    conv.resume_ai(OPERATOR, audit)  # even if AI is active again afterwards...
    with pytest.raises(AISendBlocked):  # ...the stale generation must not send
        conv.assert_ai_may_send(version_at_generation_start)


def test_illegal_transitions_raise() -> None:
    conv, audit = make_conversation(), InMemoryAuditLog()
    with pytest.raises(InvalidStateTransition):
        conv.resume_ai(OPERATOR, audit)  # not human_active
    conv.accept_handover(OPERATOR, audit)
    with pytest.raises(InvalidStateTransition):
        conv.accept_handover(OPERATOR, audit)  # already human_active
    with pytest.raises(InvalidStateTransition):
        conv.request_handover(OPERATOR, audit)  # only from ai_active
