"""Repository contract tests (SQLite adapter).

These encode the invariants the future PostgreSQL adapter must also satisfy:
CAS on control_version, idempotent message insert across restarts,
append-only audit, eligibility-filtered knowledge search, outbox lifecycle.
"""

import pathlib

import pytest
from helpers import AI, OPERATOR, make_conversation, make_doc, make_message

from invar_comms.adapters.fakes import FakeAIProvider, FakeChannelAdapter
from invar_comms.adapters.sqlite_store import (
    SqliteAuditLog,
    SqliteConversationRepository,
    SqliteDeduplicator,
    SqliteKnowledgeStore,
    SqliteMessageRepository,
    SqliteOutbox,
    SqliteStore,
)
from invar_comms.application.conversation_service import ConversationService
from invar_comms.application.worker import OutboxWorker
from invar_comms.domain.audit import AuditEventType
from invar_comms.domain.conversation import ControlState
from invar_comms.domain.errors import ConcurrencyConflict
from invar_comms.domain.knowledge import ApprovalStatus, Sensitivity


def test_conversation_roundtrip_and_cas_conflict(tmp_path: pathlib.Path) -> None:
    store = SqliteStore(tmp_path / "t.sqlite3")
    repo = SqliteConversationRepository(store)
    conv = make_conversation()
    repo.add(conv)

    loaded = repo.load("conv-1")
    assert loaded is not None
    assert loaded.state is ControlState.AI_ACTIVE
    assert loaded.control_version == 0

    audit = SqliteAuditLog(store)
    loaded.accept_handover(OPERATOR, audit)  # version 0 -> 1
    repo.save(loaded, expected_version=0)

    reloaded = repo.load("conv-1")
    assert reloaded is not None
    assert reloaded.state is ControlState.HUMAN_ACTIVE
    assert reloaded.human_owner_id == "op-1"

    # A stale writer (still expecting version 0) must never overwrite.
    with pytest.raises(ConcurrencyConflict):
        repo.save(reloaded, expected_version=0)
    store.close()


def test_message_dedupe_survives_restart(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "t.sqlite3"
    store = SqliteStore(path)
    messages = SqliteMessageRepository(store)
    assert messages.try_insert(make_message()) is True
    assert messages.try_insert(make_message()) is False  # same idempotency key
    store.close()

    reopened = SqliteStore(path)
    assert SqliteMessageRepository(reopened).try_insert(make_message()) is False
    reopened.close()


def test_audit_is_append_only_and_ordered(tmp_path: pathlib.Path) -> None:
    store = SqliteStore(tmp_path / "t.sqlite3")
    audit = SqliteAuditLog(store)
    conv = make_conversation()
    conv.request_handover(OPERATOR, audit, reason="pricing")
    conv.accept_handover(OPERATOR, audit)
    events = audit.list_for_conversation("conv-1")
    assert [e.event_type for e in events] == [
        AuditEventType.HANDOVER_REQUESTED,
        AuditEventType.HUMAN_TOOK_OVER,
    ]
    store.close()


def test_knowledge_search_applies_eligibility_in_store(tmp_path: pathlib.Path) -> None:
    store = SqliteStore(tmp_path / "t.sqlite3")
    knowledge = SqliteKnowledgeStore(store)
    knowledge.add(make_doc())
    knowledge.add(make_doc(document_id="internal",
                           sensitivity=Sensitivity.INTERNAL_ONLY))
    knowledge.add(make_doc(document_id="draft", status=ApprovalStatus.DRAFT,
                           approved_by=None, approved_at=None))
    knowledge.add(make_doc(document_id="other", product_id="maygoosh"))
    results = knowledge.search(product_id="damiish", query="register animal")
    assert [d.document_id for d in results] == ["faq-animal-registration"]
    store.close()


def test_outbox_worker_lifecycle_and_retries(tmp_path: pathlib.Path) -> None:
    store = SqliteStore(tmp_path / "t.sqlite3")
    outbox = SqliteOutbox(store)
    handled: list[dict[str, object]] = []
    outbox.enqueue("echo", {"n": 1})
    fail_id = outbox.enqueue("boom", {})
    outbox.enqueue("mystery", {})

    def boom(_: dict[str, object]) -> None:
        raise RuntimeError("kaboom")

    worker = OutboxWorker(outbox, {"echo": handled.append, "boom": boom},
                          max_attempts=2)
    # echo ok; boom retried immediately (no backoff yet) then failed finally;
    # mystery has no handler -> failed permanently. Attempts in order: 4.
    assert worker.drain() == 4
    assert handled == [{"n": 1}]
    assert outbox.fetch_pending(limit=10) == []
    rows = store._conn.execute(  # noqa: SLF001 - verify durable attempts in test
        "SELECT status, attempts FROM outbox_jobs WHERE id=?", (fail_id,)
    ).fetchone()
    assert (rows["status"], rows["attempts"]) == ("failed", 2)
    store.close()


def test_service_with_persistent_store_sends_once(tmp_path: pathlib.Path) -> None:
    store = SqliteStore(tmp_path / "t.sqlite3")
    knowledge = SqliteKnowledgeStore(store)
    knowledge.add(make_doc())
    channel = FakeChannelAdapter()
    service = ConversationService(
        ai=FakeAIProvider(), channel=channel, knowledge=knowledge,
        audit=SqliteAuditLog(store), ai_actor=AI, ai_send_enabled=True,
        dedupe=SqliteDeduplicator(SqliteMessageRepository(store)),
    )
    conv, msg = make_conversation(), make_message()
    first = service.handle_inbound(conv, msg)
    second = service.handle_inbound(conv, msg)  # webhook redelivery
    assert first.sent_message_id == "fake-msg-1"
    assert second.duplicate is True
    assert len(channel.sent) == 1
    events = SqliteAuditLog(store).list_for_conversation("conv-1")
    assert [e.event_type for e in events] == [
        AuditEventType.AI_SEND_ALLOWED,
        AuditEventType.DUPLICATE_IGNORED,
    ]
    store.close()
