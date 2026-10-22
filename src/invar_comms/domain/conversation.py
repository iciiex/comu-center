"""Conversation-control state machine — the human-takeover safety core.

States:
    AI_ACTIVE            AI may send (subject to authorization + kill-switch).
    HANDOVER_REQUESTED   Escalation asked for; AI sending is already blocked.
    HUMAN_ACTIVE         A human owns the conversation; AI sending is blocked.

Transitions (all require an authorized actor; see authorization.py):
    AI_ACTIVE --request_handover--> HANDOVER_REQUESTED --accept_handover--> HUMAN_ACTIVE
    AI_ACTIVE --accept_handover (direct takeover)--> HUMAN_ACTIVE
    HUMAN_ACTIVE --resume_ai (explicit)--> AI_ACTIVE

Race-condition defence: every control change increments `control_version`.
The application layer captures the version before generating an AI reply and
re-checks it at send time; a takeover during generation makes the captured
version stale and the send is blocked. See docs/architecture/conversation-control.md.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from enum import StrEnum

from .audit import AuditEvent, AuditEventType, AuditLog
from .authorization import Action, Actor
from .authorization import require as require_auth
from .errors import AISendBlocked, InvalidStateTransition
from .messages import ContactRef, _require_nonempty, _require_slug


class ControlState(StrEnum):
    AI_ACTIVE = "ai_active"
    HANDOVER_REQUESTED = "handover_requested"
    HUMAN_ACTIVE = "human_active"


@dataclass
class Conversation:
    conversation_id: str
    product_id: str
    contact: ContactRef
    state: ControlState = ControlState.AI_ACTIVE
    control_version: int = 0
    human_owner_id: str | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def __post_init__(self) -> None:
        _require_nonempty(self.conversation_id, "conversation_id")
        _require_slug(self.product_id, "product_id")
        if self.control_version < 0:
            raise InvalidStateTransition("control_version must be >= 0")

    # -- queries ---------------------------------------------------------
    @property
    def ai_send_allowed(self) -> bool:
        """True only in AI_ACTIVE. Handover requested already blocks the AI."""
        return self.state is ControlState.AI_ACTIVE

    # -- transitions -----------------------------------------------------
    def request_handover(
        self, actor: Actor, audit: AuditLog, reason: str = ""
    ) -> None:
        require_auth(actor, Action.REQUEST_HANDOVER, self.product_id)
        with self._lock:
            if self.state is not ControlState.AI_ACTIVE:
                raise InvalidStateTransition(
                    f"handover can only be requested from ai_active, not {self.state}"
                )
            self.state = ControlState.HANDOVER_REQUESTED
            self.control_version += 1
        audit.record(
            AuditEvent(
                AuditEventType.HANDOVER_REQUESTED,
                self.product_id,
                self.conversation_id,
                actor.actor_id,
                detail=reason,
            )
        )

    def accept_handover(self, actor: Actor, audit: AuditLog) -> None:
        """Human takeover: blocks all automatic AI sending until explicit resume."""
        require_auth(actor, Action.ACCEPT_HANDOVER, self.product_id)
        with self._lock:
            if self.state is ControlState.HUMAN_ACTIVE:
                raise InvalidStateTransition("conversation is already human_active")
            self.state = ControlState.HUMAN_ACTIVE
            self.human_owner_id = actor.actor_id
            self.control_version += 1
        audit.record(
            AuditEvent(
                AuditEventType.HUMAN_TOOK_OVER,
                self.product_id,
                self.conversation_id,
                actor.actor_id,
            )
        )

    def resume_ai(self, actor: Actor, audit: AuditLog) -> None:
        """Explicit, authorized AI resume. The ONLY way back to AI_ACTIVE."""
        require_auth(actor, Action.RESUME_AI, self.product_id)
        with self._lock:
            if self.state is not ControlState.HUMAN_ACTIVE:
                raise InvalidStateTransition(
                    f"AI can only resume from human_active, not {self.state}"
                )
            self.state = ControlState.AI_ACTIVE
            self.human_owner_id = None
            self.control_version += 1
        audit.record(
            AuditEvent(
                AuditEventType.AI_RESUMED,
                self.product_id,
                self.conversation_id,
                actor.actor_id,
            )
        )

    # -- send guard ------------------------------------------------------
    def assert_ai_may_send(self, expected_control_version: int) -> None:
        """Re-validate at send time. Raises AISendBlocked if anything changed."""
        with self._lock:
            if not self.ai_send_allowed:
                raise AISendBlocked(
                    f"AI sending blocked: conversation is {self.state}"
                )
            if expected_control_version != self.control_version:
                raise AISendBlocked(
                    "AI sending blocked: control changed during generation "
                    f"(expected version {expected_control_version}, now {self.control_version})"
                )
