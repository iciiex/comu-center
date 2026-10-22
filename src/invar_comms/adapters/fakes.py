"""Deterministic fakes for tests and local contract exercise. Never for production."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from ..domain.messages import (
    Channel,
    ContentType,
    Direction,
    InternalMessage,
)
from ..ports.ai_provider import ReplyRequest, ReplySuggestion


class FakeAIProvider:
    """Returns a canned, clearly-marked suggestion. No model, no network."""

    name = "fake"

    def __init__(self, text: str = "[fake suggestion] Thanks for your message.",
                 confidence: float = 0.9) -> None:
        self._text = text
        self._confidence = confidence
        self.requests: list[ReplyRequest] = []

    def suggest_reply(self, request: ReplyRequest) -> ReplySuggestion:
        self.requests.append(request)
        return ReplySuggestion(
            text=self._text,
            confidence=self._confidence,
            used_document_ids=tuple(),
        )


class FakeChannelAdapter:
    """Records sends instead of touching any external platform."""

    channel_name = Channel.FAKE

    def __init__(self) -> None:
        self.sent: list[dict[str, str]] = []

    def normalize_inbound(self, payload: dict[str, Any]) -> list[InternalMessage]:
        return [
            InternalMessage(
                product_id=str(payload.get("product_id", "damiish")),
                channel=Channel.FAKE,
                channel_account_id=str(payload.get("channel_account_id", "fake-acct")),
                external_contact_id=str(payload["external_contact_id"]),
                conversation_id=str(payload["conversation_id"]),
                external_event_id=str(payload["external_event_id"]),
                direction=Direction.INBOUND,
                content_type=ContentType.TEXT,
                occurred_at=datetime.now(UTC),
                text=str(payload["text"]),
            )
        ]

    def send_text(self, *, conversation_id: str, external_contact_id: str, text: str) -> str:
        self.sent.append(
            {
                "conversation_id": conversation_id,
                "external_contact_id": external_contact_id,
                "text": text,
            }
        )
        return f"fake-msg-{len(self.sent)}"
