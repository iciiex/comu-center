"""Approved-knowledge contract.

Only documents that are APPROVED, currently VALID, scoped to the conversation's
product, and classified for customer-facing FAQ use may ground an automatic
response. Knowledge is versioned data — editable independently of system prompts.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from .authorization import Action, Actor
from .authorization import require as require_auth
from .errors import ValidationError
from .messages import _require_aware, _require_nonempty, _require_slug


class ApprovalStatus(StrEnum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    RETIRED = "retired"


class Sensitivity(StrEnum):
    PUBLIC_FAQ = "public_faq"  # eligible to ground automatic customer replies
    INTERNAL_ONLY = "internal_only"  # never eligible for automatic replies
    RESTRICTED = "restricted"  # never eligible; extra access control


@dataclass(frozen=True)
class KnowledgeDocument:
    document_id: str
    version: int
    product_id: str
    title: str
    content: str
    source: str
    status: ApprovalStatus
    sensitivity: Sensitivity
    updated_at: datetime
    approved_by: str | None = None
    approved_at: datetime | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None

    def __post_init__(self) -> None:
        _require_nonempty(self.document_id, "document_id")
        _require_slug(self.product_id, "product_id")
        _require_nonempty(self.title, "title")
        _require_nonempty(self.content, "content")
        _require_nonempty(self.source, "source")
        if self.version < 1:
            raise ValidationError("knowledge version must be >= 1")
        _require_aware(self.updated_at, "updated_at")
        if self.status is ApprovalStatus.APPROVED:
            if not self.approved_by or self.approved_at is None:
                raise ValidationError("approved knowledge needs approved_by and approved_at")
        if (
            self.valid_from is not None
            and self.valid_until is not None
            and self.valid_until <= self.valid_from
        ):
            raise ValidationError("valid_until must be after valid_from")

    def is_eligible_for_auto_reply(self, *, product_id: str, at: datetime) -> bool:
        """The single eligibility gate for automatic responses (fail closed)."""
        at = _require_aware(at, "at")
        if self.product_id != product_id:
            return False
        if self.status is not ApprovalStatus.APPROVED:
            return False
        if self.sensitivity is not Sensitivity.PUBLIC_FAQ:
            return False
        if self.valid_from is not None and at < self.valid_from:
            return False
        return not (self.valid_until is not None and at >= self.valid_until)


def approve(doc: KnowledgeDocument, actor: Actor, at: datetime) -> KnowledgeDocument:
    """Return an APPROVED copy. Only an authorized approver/admin may do this."""
    require_auth(actor, Action.APPROVE_KNOWLEDGE, doc.product_id)
    if doc.status is ApprovalStatus.APPROVED:
        raise ValidationError("document is already approved; publish a new version instead")
    from dataclasses import replace

    return replace(
        doc,
        status=ApprovalStatus.APPROVED,
        approved_by=actor.actor_id,
        approved_at=_require_aware(at, "at"),
    )
