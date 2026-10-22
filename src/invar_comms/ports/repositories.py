"""Repository & outbox ports (persistence contracts).

These contracts are storage-technology independent: the SQLite adapter
implements them today; the PostgreSQL adapter (production target, ADR-0008)
must pass the same contract tests later. The invariants that matter are part
of the contract, not adapter trivia:

- message insert is idempotent by `idempotency_key` (duplicate -> False);
- conversation save is compare-and-swap on `control_version`
  (stale writer -> ConcurrencyConflict, never a silent overwrite);
- audit is append-only;
- knowledge search never returns ineligible documents (domain gate).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from ..domain.audit import AuditEvent
from ..domain.conversation import Conversation
from ..domain.knowledge import KnowledgeDocument
from ..domain.messages import InternalMessage


class Deduplicator(Protocol):
    def seen(self, message: InternalMessage) -> bool:
        """Return True exactly once per idempotency key (first call False)."""
        ...


class ConversationRepository(Protocol):
    def add(self, conversation: Conversation) -> None: ...

    def load(self, conversation_id: str) -> Conversation | None: ...

    def save(self, conversation: Conversation, *, expected_version: int) -> None:
        """CAS update: succeeds only if stored control_version == expected."""
        ...


class MessageRepository(Protocol):
    def try_insert(self, message: InternalMessage) -> bool:
        """Insert; return False (no error) if the idempotency key exists."""
        ...


class AuditRepository(Protocol):
    def record(self, event: AuditEvent) -> None: ...

    def list_for_conversation(self, conversation_id: str) -> list[AuditEvent]: ...


class KnowledgeStore(Protocol):
    def add(self, document: KnowledgeDocument) -> None: ...

    def search(
        self, *, product_id: str, query: str, limit: int = 5
    ) -> tuple[KnowledgeDocument, ...]: ...


@dataclass(frozen=True)
class OutboxJob:
    job_id: int
    job_type: str
    payload: dict[str, Any] = field(default_factory=dict)
    attempts: int = 0


class Outbox(Protocol):
    def enqueue(self, job_type: str, payload: dict[str, Any]) -> int: ...

    def fetch_pending(self, *, limit: int = 1) -> list[OutboxJob]: ...

    def mark_done(self, job_id: int) -> None: ...

    def mark_failed(self, job_id: int, error: str, *, retry: bool) -> None:
        """Record failure; retry=True keeps the job pending for another attempt."""
        ...
