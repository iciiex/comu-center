"""Channel adapter port: normalize platform events in, send approved text out.

Adapters (Instagram/Meta, future channels, fakes) must not leak platform
shapes into the domain: inbound payloads become InternalMessage, outbound
sends go through the application layer's guards first.
"""

from __future__ import annotations

from typing import Any, Protocol

from ..domain.messages import InternalMessage


class ChannelAdapter(Protocol):
    channel_name: str

    def normalize_inbound(self, payload: dict[str, Any]) -> list[InternalMessage]: ...

    def send_text(self, *, conversation_id: str, external_contact_id: str, text: str) -> str:
        """Send and return the platform message id. May raise LiveSendDisabled."""
        ...
