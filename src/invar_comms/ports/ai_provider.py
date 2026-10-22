"""AI provider port. The domain never imports a provider SDK.

A provider *suggests* a reply grounded in supplied knowledge excerpts.
Suggesting is not sending: the application layer alone decides whether a
suggestion may be sent (state machine + authorization + kill-switch).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from ..domain.messages import InternalMessage, _require_nonempty


@dataclass(frozen=True)
class ReplyRequest:
    product_id: str
    inbound: InternalMessage
    knowledge_excerpts: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ReplySuggestion:
    text: str
    confidence: float  # provider-reported 0..1; policy thresholds live in the app layer
    used_document_ids: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        _require_nonempty(self.text, "suggestion text")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be within [0, 1]")


class AIProvider(Protocol):
    name: str

    def suggest_reply(self, request: ReplyRequest) -> ReplySuggestion: ...
