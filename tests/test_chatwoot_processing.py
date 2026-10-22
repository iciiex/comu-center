"""End-to-end Chatwoot event processing on the persistent stack."""

import pathlib

from helpers import AI, OPERATOR, make_doc

from invar_comms.adapters.chatwoot import InboxMapping
from invar_comms.adapters.fakes import FakeAIProvider, FakeChannelAdapter
from invar_comms.adapters.sqlite_store import (
    SqliteAuditLog,
    SqliteConversationRepository,
    SqliteDeduplicator,
    SqliteKnowledgeStore,
    SqliteMessageRepository,
    SqliteStore,
)
from invar_comms.application.chatwoot_processing import ChatwootEventProcessor
from invar_comms.application.conversation_service import ConversationService
from invar_comms.domain.conversation import ControlState
from invar_comms.domain.messages import Channel
from invar_comms.wiring import parse_inbox_map

INBOXES = {7: InboxMapping("damiish", Channel.INSTAGRAM, "ig-acct-1")}


def customer_event(text: str = "How do I register a new animal?",
                   msg_id: int = 101) -> dict[str, object]:
    return {
        "event": "message_created", "id": msg_id, "content": text,
        "created_at": 1792312800, "message_type": "incoming", "private": False,
        "source_id": "ig-msg-55",
        "sender": {"id": 42, "type": "contact"},
        "conversation": {"id": 900, "inbox_id": 7, "status": "pending",
                         "contact_inbox": {"source_id": "ig-user-42"}},
        "account": {"id": 3},
    }


class Rig:
    def __init__(self, tmp_path: pathlib.Path, *,
                 with_knowledge: bool = True,
                 operator_resolver=None, status_sync=None) -> None:  # type: ignore[no-untyped-def]
        self.store = SqliteStore(tmp_path / "t.sqlite3")
        self.conversations = SqliteConversationRepository(self.store)
        self.channel = FakeChannelAdapter()
        knowledge = SqliteKnowledgeStore(self.store)
        if with_knowledge:
            knowledge.add(make_doc())
        service = ConversationService(
            ai=FakeAIProvider(), channel=self.channel, knowledge=knowledge,
            audit=SqliteAuditLog(self.store), ai_actor=AI, ai_send_enabled=True,
            dedupe=SqliteDeduplicator(SqliteMessageRepository(self.store)),
        )
        self.processor = ChatwootEventProcessor(
            service=service, conversations=self.conversations,
            audit=SqliteAuditLog(self.store), ai_actor=AI, inboxes=INBOXES,
            operator_resolver=operator_resolver, status_sync=status_sync,
        )

    def state(self) -> ControlState:
        conv = self.conversations.load("cw-3-900")
        assert conv is not None
        return conv.state


def test_faq_event_replies_and_persists_conversation(tmp_path: pathlib.Path) -> None:
    synced: list[tuple[str, str]] = []
    rig = Rig(tmp_path, status_sync=lambda k, s: synced.append((k, s)))
    result = rig.processor.process(customer_event())  # type: ignore[arg-type]
    assert result.outcome == "replied"
    assert len(rig.channel.sent) == 1
    assert rig.state() is ControlState.AI_ACTIVE
    assert synced == []  # no handoff -> no status projection


def test_duplicate_event_does_not_send_twice(tmp_path: pathlib.Path) -> None:
    rig = Rig(tmp_path)
    rig.processor.process(customer_event())  # type: ignore[arg-type]
    second = rig.processor.process(customer_event())  # type: ignore[arg-type]
    assert second.duplicate is True
    assert len(rig.channel.sent) == 1


def test_no_knowledge_escalates_persists_and_projects_open(
        tmp_path: pathlib.Path) -> None:
    synced: list[tuple[str, str]] = []
    rig = Rig(tmp_path, with_knowledge=False,
              status_sync=lambda k, s: synced.append((k, s)))
    result = rig.processor.process(customer_event("قیمت چنده؟"))  # type: ignore[arg-type]
    assert result.escalated is True
    assert rig.channel.sent == []
    assert rig.state() is ControlState.HANDOVER_REQUESTED
    assert synced == [("cw-3-900", "open")]


def test_unmapped_operator_reply_still_blocks_ai(tmp_path: pathlib.Path) -> None:
    rig = Rig(tmp_path)
    rig.processor.process(customer_event())  # creates conversation
    operator_event = customer_event("سلام، من اپراتورم", msg_id=102)
    operator_event["message_type"] = "outgoing"
    operator_event["sender"] = {"id": 999, "type": "user"}
    result = rig.processor.process(operator_event)  # type: ignore[arg-type]
    assert result.outcome == "ai_blocked_unmapped_operator"
    assert rig.state() is ControlState.HANDOVER_REQUESTED


def test_mapped_operator_reply_records_takeover(tmp_path: pathlib.Path) -> None:
    rig = Rig(tmp_path, operator_resolver=lambda ref, pid:
              OPERATOR if ref == "9" else None)
    rig.processor.process(customer_event())  # type: ignore[arg-type]
    operator_event = customer_event("پیگیرم", msg_id=103)
    operator_event["message_type"] = "outgoing"
    operator_event["sender"] = {"id": 9, "type": "user"}
    result = rig.processor.process(operator_event)  # type: ignore[arg-type]
    assert result.outcome == "takeover_recorded"
    assert rig.state() is ControlState.HUMAN_ACTIVE


def test_status_pending_never_resumes_ai(tmp_path: pathlib.Path) -> None:
    rig = Rig(tmp_path, with_knowledge=False)
    rig.processor.process(customer_event())  # escalates -> handover_requested
    pending = {"event": "conversation_status_changed", "id": 900,
               "status": "pending", "account": {"id": 3}}
    result = rig.processor.process(pending)  # type: ignore[arg-type]
    assert result.outcome.startswith("resume_signal_ignored")
    assert rig.state() is ControlState.HANDOVER_REQUESTED  # unchanged


def test_parse_inbox_map_strictness() -> None:
    import pytest

    from invar_comms.domain.errors import ValidationError

    parsed = parse_inbox_map("7=damiish:instagram:ig-1", enabled_products=frozenset({"damiish"}))
    assert parsed[7].product_id == "damiish"
    for bad in ["x=damiish:instagram:a", "7=other:instagram:a", "7=damiish:nope:a",
                "7damiish:instagram:a", "7=damiish:instagram:a,7=damiish:instagram:b"]:
        with pytest.raises(ValidationError):
            parse_inbox_map(bad, enabled_products=frozenset({"damiish"}))
