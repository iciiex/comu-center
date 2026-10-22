"""SQLite persistence adapter (stdlib `sqlite3`, zero new dependencies).

Purpose: a real, durable store for local development and contract testing of
the repository ports. It mirrors the proposed PostgreSQL schema
(`db/migrations/0001_initial.sql`) so the future Postgres adapter can reuse
the same contracts/tests. Per ADR-0008 this is NOT the production database —
PostgreSQL remains the target; this adapter must never be presented as such.

Guarantees implemented here (and covered by tests):
- messages.idempotency_key UNIQUE -> webhook redelivery dedupe survives restart;
- conversation save is compare-and-swap on control_version;
- audit events are append-only (no update/delete API exists);
- knowledge search applies the eligibility gate (product, APPROVED,
  PUBLIC_FAQ, validity window) — scoring is simple keyword overlap until
  Postgres FTS arrives.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..domain.audit import AuditEvent, AuditEventType
from ..domain.conversation import ControlState, Conversation
from ..domain.errors import ConcurrencyConflict
from ..domain.knowledge import ApprovalStatus, KnowledgeDocument, Sensitivity
from ..domain.messages import (
    Channel,
    ContactRef,
    ContentType,
    DeliveryStatus,
    Direction,
    InternalMessage,
    ProcessingStatus,
)
from ..ports.repositories import OutboxJob

SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
    conversation_id     TEXT PRIMARY KEY,
    product_id          TEXT NOT NULL,
    channel             TEXT NOT NULL,
    channel_account_id  TEXT NOT NULL,
    external_contact_id TEXT NOT NULL,
    control_state       TEXT NOT NULL,
    control_version     INTEGER NOT NULL,
    human_owner_id      TEXT,
    updated_at          TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    schema_version      INTEGER NOT NULL,
    product_id          TEXT NOT NULL,
    channel             TEXT NOT NULL,
    channel_account_id  TEXT NOT NULL,
    external_contact_id TEXT NOT NULL,
    conversation_id     TEXT NOT NULL,
    external_event_id   TEXT NOT NULL,
    external_message_id TEXT,
    idempotency_key     TEXT NOT NULL UNIQUE,
    direction           TEXT NOT NULL,
    content_type        TEXT NOT NULL,
    body_text           TEXT NOT NULL,
    processing_status   TEXT NOT NULL,
    delivery_status     TEXT NOT NULL,
    correlation_id      TEXT NOT NULL,
    metadata_json       TEXT NOT NULL,
    occurred_at         TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS knowledge_documents (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id  TEXT NOT NULL,
    version      INTEGER NOT NULL,
    product_id   TEXT NOT NULL,
    title        TEXT NOT NULL,
    content      TEXT NOT NULL,
    source       TEXT NOT NULL,
    status       TEXT NOT NULL,
    sensitivity  TEXT NOT NULL,
    approved_by  TEXT,
    approved_at  TEXT,
    valid_from   TEXT,
    valid_until  TEXT,
    updated_at   TEXT NOT NULL,
    UNIQUE (product_id, document_id, version)
);
CREATE TABLE IF NOT EXISTS audit_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type      TEXT NOT NULL,
    product_id      TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    actor_id        TEXT NOT NULL,
    detail          TEXT NOT NULL,
    occurred_at     TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS outbox_jobs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    job_type     TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'pending',
    attempts     INTEGER NOT NULL DEFAULT 0,
    last_error   TEXT NOT NULL DEFAULT '',
    created_at   TEXT NOT NULL,
    processed_at TEXT
);
"""


def _iso(ts: datetime) -> str:
    return ts.astimezone(UTC).isoformat()


def _parse(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _now() -> str:
    return _iso(datetime.now(UTC))


class SqliteStore:
    """Single-file store implementing all repository ports for local use."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock, self._conn:
            self._conn.executescript(SCHEMA)

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def __enter__(self) -> SqliteStore:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def table_names(self) -> list[str]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            ).fetchall()
        return [str(r["name"]) for r in rows]

    # -- conversations (CAS on control_version) ---------------------------
    def conversation_add(self, conversation: Conversation) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO conversations VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    conversation.conversation_id,
                    conversation.product_id,
                    str(conversation.contact.channel),
                    conversation.contact.channel_account_id,
                    conversation.contact.external_contact_id,
                    str(conversation.state),
                    conversation.control_version,
                    conversation.human_owner_id,
                    _now(),
                ),
            )

    def conversation_load(self, conversation_id: str) -> Conversation | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM conversations WHERE conversation_id=?",
                (conversation_id,),
            ).fetchone()
        if row is None:
            return None
        return Conversation(
            conversation_id=row["conversation_id"],
            product_id=row["product_id"],
            contact=ContactRef(
                Channel(row["channel"]),
                row["channel_account_id"],
                row["external_contact_id"],
            ),
            state=ControlState(row["control_state"]),
            control_version=int(row["control_version"]),
            human_owner_id=row["human_owner_id"],
        )

    def conversations_list(self, *, limit: int = 100) -> list[Conversation]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM conversations ORDER BY updated_at DESC LIMIT ?",
                (max(limit, 0),),
            ).fetchall()
        result: list[Conversation] = []
        for row in rows:
            loaded = self.conversation_load(row["conversation_id"])
            if loaded is not None:
                result.append(loaded)
        return result

    def messages_list(self, conversation_id: str, *,
                      limit: int = 200) -> list[InternalMessage]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM messages WHERE conversation_id=? "
                "ORDER BY id LIMIT ?",
                (conversation_id, max(limit, 0)),
            ).fetchall()
        messages: list[InternalMessage] = []
        for row in rows:
            messages.append(InternalMessage(
                product_id=row["product_id"],
                channel=Channel(row["channel"]),
                channel_account_id=row["channel_account_id"],
                external_contact_id=row["external_contact_id"],
                conversation_id=row["conversation_id"],
                external_event_id=row["external_event_id"],
                external_message_id=row["external_message_id"],
                direction=Direction(row["direction"]),
                content_type=ContentType(row["content_type"]),
                occurred_at=_parse(row["occurred_at"]) or datetime.now(UTC),
                text=row["body_text"],
                processing_status=ProcessingStatus(row["processing_status"]),
                delivery_status=DeliveryStatus(row["delivery_status"]),
                schema_version=int(row["schema_version"]),
                correlation_id=row["correlation_id"],
                metadata=json.loads(row["metadata_json"] or "{}"),
            ))
        return messages

    def conversation_save(
        self, conversation: Conversation, *, expected_version: int
    ) -> None:
        with self._lock, self._conn:
            cur = self._conn.execute(
                "UPDATE conversations SET control_state=?, control_version=?, "
                "human_owner_id=?, updated_at=? "
                "WHERE conversation_id=? AND control_version=?",
                (
                    str(conversation.state),
                    conversation.control_version,
                    conversation.human_owner_id,
                    _now(),
                    conversation.conversation_id,
                    expected_version,
                ),
            )
            if cur.rowcount != 1:
                raise ConcurrencyConflict(
                    f"conversation {conversation.conversation_id} changed "
                    f"concurrently (expected stored version {expected_version})"
                )

    # -- messages (idempotent insert) --------------------------------------
    def message_try_insert(self, message: InternalMessage) -> bool:
        try:
            with self._lock, self._conn:
                self._conn.execute(
                    "INSERT INTO messages (schema_version, product_id, channel, "
                    "channel_account_id, external_contact_id, conversation_id, "
                    "external_event_id, external_message_id, idempotency_key, "
                    "direction, content_type, body_text, processing_status, "
                    "delivery_status, correlation_id, metadata_json, occurred_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        message.schema_version,
                        message.product_id,
                        str(message.channel),
                        message.channel_account_id,
                        message.external_contact_id,
                        message.conversation_id,
                        message.external_event_id,
                        message.external_message_id,
                        message.idempotency_key,
                        str(message.direction),
                        str(message.content_type),
                        message.text,
                        str(message.processing_status),
                        str(message.delivery_status),
                        message.correlation_id,
                        json.dumps(message.metadata),
                        _iso(message.occurred_at),
                    ),
                )
            return True
        except sqlite3.IntegrityError:
            return False  # duplicate idempotency_key — expected, not an error

    # -- audit (append-only) ------------------------------------------------
    def record(self, event: AuditEvent) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO audit_events (event_type, product_id, "
                "conversation_id, actor_id, detail, occurred_at) "
                "VALUES (?,?,?,?,?,?)",
                (
                    str(event.event_type),
                    event.product_id,
                    event.conversation_id,
                    event.actor_id,
                    event.detail,
                    _iso(event.occurred_at),
                ),
            )

    def audit_list(self, conversation_id: str) -> list[AuditEvent]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM audit_events WHERE conversation_id=? ORDER BY id",
                (conversation_id,),
            ).fetchall()
        return [
            AuditEvent(
                AuditEventType(r["event_type"]),
                r["product_id"],
                r["conversation_id"],
                r["actor_id"],
                occurred_at=_parse(r["occurred_at"]) or datetime.now(UTC),
                detail=r["detail"],
            )
            for r in rows
        ]

    # -- knowledge -----------------------------------------------------------
    def knowledge_add(self, doc: KnowledgeDocument) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO knowledge_documents (document_id, version, "
                "product_id, title, content, source, status, sensitivity, "
                "approved_by, approved_at, valid_from, valid_until, updated_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    doc.document_id,
                    doc.version,
                    doc.product_id,
                    doc.title,
                    doc.content,
                    doc.source,
                    str(doc.status),
                    str(doc.sensitivity),
                    doc.approved_by,
                    _iso(doc.approved_at) if doc.approved_at else None,
                    _iso(doc.valid_from) if doc.valid_from else None,
                    _iso(doc.valid_until) if doc.valid_until else None,
                    _iso(doc.updated_at),
                ),
            )

    def knowledge_search(
        self, *, product_id: str, query: str, limit: int = 5
    ) -> tuple[KnowledgeDocument, ...]:
        now = datetime.now(UTC)
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM knowledge_documents WHERE product_id=? "
                "AND status='approved' AND sensitivity='public_faq'",
                (product_id,),
            ).fetchall()
        terms = {t.lower() for t in query.split() if t.strip()}
        scored: list[tuple[int, KnowledgeDocument]] = []
        for row in rows:
            doc = KnowledgeDocument(
                document_id=row["document_id"],
                version=int(row["version"]),
                product_id=row["product_id"],
                title=row["title"],
                content=row["content"],
                source=row["source"],
                status=ApprovalStatus(row["status"]),
                sensitivity=Sensitivity(row["sensitivity"]),
                updated_at=_parse(row["updated_at"]) or now,
                approved_by=row["approved_by"],
                approved_at=_parse(row["approved_at"]),
                valid_from=_parse(row["valid_from"]),
                valid_until=_parse(row["valid_until"]),
            )
            # Validity window is part of the domain gate — re-checked here.
            if not doc.is_eligible_for_auto_reply(product_id=product_id, at=now):
                continue
            haystack = f"{doc.title} {doc.content}".lower()
            score = sum(1 for t in terms if t in haystack)
            if score:
                scored.append((score, doc))
        scored.sort(key=lambda item: (-item[0], item[1].document_id))
        return tuple(doc for _, doc in scored[: max(limit, 0)])

    # -- outbox ----------------------------------------------------------------
    def outbox_enqueue(self, job_type: str, payload: dict[str, Any]) -> int:
        with self._lock, self._conn:
            cur = self._conn.execute(
                "INSERT INTO outbox_jobs (job_type, payload_json, created_at) "
                "VALUES (?,?,?)",
                (job_type, json.dumps(payload), _now()),
            )
            return int(cur.lastrowid or 0)

    def outbox_fetch_pending(self, *, limit: int = 1) -> list[OutboxJob]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM outbox_jobs WHERE status='pending' "
                "ORDER BY id LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            OutboxJob(
                job_id=int(r["id"]),
                job_type=r["job_type"],
                payload=json.loads(r["payload_json"]),
                attempts=int(r["attempts"]),
            )
            for r in rows
        ]

    def outbox_mark_done(self, job_id: int) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE outbox_jobs SET status='done', processed_at=? WHERE id=?",
                (_now(), job_id),
            )

    def outbox_mark_failed(self, job_id: int, error: str, *, retry: bool) -> None:
        status = "pending" if retry else "failed"
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE outbox_jobs SET status=?, attempts=attempts+1, "
                "last_error=?, processed_at=? WHERE id=?",
                (status, error[:500], _now(), job_id),
            )


# -- thin port adapters over SqliteStore --------------------------------------

class SqliteConversationRepository:
    def __init__(self, store: SqliteStore) -> None:
        self._store = store

    def add(self, conversation: Conversation) -> None:
        self._store.conversation_add(conversation)

    def load(self, conversation_id: str) -> Conversation | None:
        return self._store.conversation_load(conversation_id)

    def save(self, conversation: Conversation, *, expected_version: int) -> None:
        self._store.conversation_save(conversation, expected_version=expected_version)


class SqliteMessageRepository:
    def __init__(self, store: SqliteStore) -> None:
        self._store = store

    def try_insert(self, message: InternalMessage) -> bool:
        return self._store.message_try_insert(message)


class SqliteAuditLog:
    """Satisfies both the domain AuditLog port and AuditRepository."""

    def __init__(self, store: SqliteStore) -> None:
        self._store = store

    def record(self, event: AuditEvent) -> None:
        self._store.record(event)

    def list_for_conversation(self, conversation_id: str) -> list[AuditEvent]:
        return self._store.audit_list(conversation_id)


class SqliteKnowledgeStore:
    def __init__(self, store: SqliteStore) -> None:
        self._store = store

    def add(self, document: KnowledgeDocument) -> None:
        self._store.knowledge_add(document)

    def search(
        self, *, product_id: str, query: str, limit: int = 5
    ) -> tuple[KnowledgeDocument, ...]:
        return self._store.knowledge_search(
            product_id=product_id, query=query, limit=limit
        )


class SqliteOutbox:
    def __init__(self, store: SqliteStore) -> None:
        self._store = store

    def enqueue(self, job_type: str, payload: dict[str, Any]) -> int:
        return self._store.outbox_enqueue(job_type, payload)

    def fetch_pending(self, *, limit: int = 1) -> list[OutboxJob]:
        return self._store.outbox_fetch_pending(limit=limit)

    def mark_done(self, job_id: int) -> None:
        self._store.outbox_mark_done(job_id)

    def mark_failed(self, job_id: int, error: str, *, retry: bool) -> None:
        self._store.outbox_mark_failed(job_id, error, retry=retry)


class SqliteDeduplicator:
    """Persistent dedupe: `seen` is backed by the messages UNIQUE constraint."""

    def __init__(self, messages: SqliteMessageRepository) -> None:
        self._messages = messages

    def seen(self, message: InternalMessage) -> bool:
        return not self._messages.try_insert(message)


__all__ = [
    "SCHEMA",
    "SqliteAuditLog",
    "SqliteConversationRepository",
    "SqliteDeduplicator",
    "SqliteKnowledgeStore",
    "SqliteMessageRepository",
    "SqliteOutbox",
    "SqliteStore",
]
