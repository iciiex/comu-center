"""Explicit, server-side authorization.

Rules:
- Every action that affects customers or external systems requires an
  authorized actor acting inside an explicit product scope (fail closed).
- An AI/system actor may *suggest* and may *send only when* the conversation
  state machine and kill-switch allow it (enforced in the application layer).
  It may never approve knowledge, take over a conversation, or resume itself.
- Prompt text, customer messages, and retrieved documents can never grant
  permissions — they are untrusted input and are not actors.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from .errors import AuthorizationError, ValidationError
from .messages import _require_nonempty, _require_slug


class Role(StrEnum):
    ADMIN = "admin"
    OPERATOR = "operator"  # human support operator in the inbox
    CONTENT_APPROVER = "content_approver"
    AI_SYSTEM = "ai_system"
    READ_ONLY = "read_only"


class Action(StrEnum):
    AI_SUGGEST = "ai_suggest"
    AI_SEND = "ai_send"
    HUMAN_SEND = "human_send"
    REQUEST_HANDOVER = "request_handover"
    ACCEPT_HANDOVER = "accept_handover"
    RESUME_AI = "resume_ai"
    APPROVE_KNOWLEDGE = "approve_knowledge"
    EDIT_KNOWLEDGE = "edit_knowledge"
    VIEW_CONVERSATION = "view_conversation"


# Role -> permitted actions (product-scope is checked separately, always).
_PERMISSIONS: dict[Role, frozenset[Action]] = {
    Role.ADMIN: frozenset(Action),
    Role.OPERATOR: frozenset(
        {
            Action.HUMAN_SEND,
            Action.REQUEST_HANDOVER,
            Action.ACCEPT_HANDOVER,
            Action.RESUME_AI,
            Action.VIEW_CONVERSATION,
        }
    ),
    Role.CONTENT_APPROVER: frozenset(
        {Action.APPROVE_KNOWLEDGE, Action.EDIT_KNOWLEDGE, Action.VIEW_CONVERSATION}
    ),
    # Escalating to a human is the fail-safe direction, so the AI may *request*
    # handover (which blocks its own sending). It may never accept/resume/approve.
    Role.AI_SYSTEM: frozenset(
        {Action.AI_SUGGEST, Action.AI_SEND, Action.REQUEST_HANDOVER}
    ),
    Role.READ_ONLY: frozenset({Action.VIEW_CONVERSATION}),
}


@dataclass(frozen=True)
class Actor:
    actor_id: str
    role: Role
    product_ids: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        _require_nonempty(self.actor_id, "actor_id")
        if not self.product_ids:
            raise ValidationError("actor must have at least one product scope (fail closed)")
        for pid in self.product_ids:
            _require_slug(pid, "product_ids")


def require(actor: Actor, action: Action, product_id: str) -> None:
    """Raise AuthorizationError unless `actor` may perform `action` for `product_id`."""
    _require_slug(product_id, "product_id")
    if product_id not in actor.product_ids:
        raise AuthorizationError(
            f"actor {actor.actor_id!r} has no scope for product {product_id!r}"
        )
    if action not in _PERMISSIONS[actor.role]:
        raise AuthorizationError(
            f"role {actor.role} may not perform {action} (actor {actor.actor_id!r})"
        )
