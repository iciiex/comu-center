"""Knowledge retrieval port + a simple in-memory implementation.

Retrieval always passes through the eligibility gate in domain.knowledge:
unapproved, expired, wrong-product, or internal-only content can never be
returned for automatic replies. Start simple (keyword / Postgres FTS later);
semantic (pgvector) retrieval only when justified — see ADR-0003.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

from ..domain.knowledge import KnowledgeDocument


class KnowledgeRetriever(Protocol):
    def search(
        self, *, product_id: str, query: str, limit: int = 5
    ) -> tuple[KnowledgeDocument, ...]: ...


class InMemoryKnowledgeRetriever:
    """Deterministic keyword retriever for tests/local exercise of the contract."""

    def __init__(self, documents: list[KnowledgeDocument] | None = None) -> None:
        self._documents: list[KnowledgeDocument] = list(documents or [])

    def add(self, document: KnowledgeDocument) -> None:
        self._documents.append(document)

    def search(
        self, *, product_id: str, query: str, limit: int = 5
    ) -> tuple[KnowledgeDocument, ...]:
        now = datetime.now(UTC)
        terms = {t.lower() for t in query.split() if t.strip()}
        scored: list[tuple[int, KnowledgeDocument]] = []
        for doc in self._documents:
            if not doc.is_eligible_for_auto_reply(product_id=product_id, at=now):
                continue
            haystack = f"{doc.title} {doc.content}".lower()
            score = sum(1 for t in terms if t in haystack)
            if score > 0:
                scored.append((score, doc))
        scored.sort(key=lambda item: (-item[0], item[1].document_id))
        return tuple(doc for _, doc in scored[: max(limit, 0)])
