from datetime import timedelta

import pytest
from helpers import AI, APPROVER, NOW, OPERATOR, make_doc

from invar_comms.domain.errors import AuthorizationError, ValidationError
from invar_comms.domain.knowledge import ApprovalStatus, Sensitivity, approve
from invar_comms.ports.knowledge_retrieval import InMemoryKnowledgeRetriever


def test_only_approved_valid_public_faq_is_eligible() -> None:
    assert make_doc().is_eligible_for_auto_reply(product_id="damiish", at=NOW)
    assert not make_doc(status=ApprovalStatus.DRAFT, approved_by=None,
                        approved_at=None).is_eligible_for_auto_reply(
        product_id="damiish", at=NOW)
    assert not make_doc(sensitivity=Sensitivity.INTERNAL_ONLY) \
        .is_eligible_for_auto_reply(product_id="damiish", at=NOW)
    assert not make_doc(product_id="maygoosh") \
        .is_eligible_for_auto_reply(product_id="damiish", at=NOW)
    assert not make_doc(valid_until=NOW - timedelta(days=1)) \
        .is_eligible_for_auto_reply(product_id="damiish", at=NOW)
    assert not make_doc(valid_from=NOW + timedelta(days=1)) \
        .is_eligible_for_auto_reply(product_id="damiish", at=NOW)


def test_approved_doc_requires_approver_metadata() -> None:
    with pytest.raises(ValidationError):
        make_doc(approved_by=None)


def test_approval_requires_authorized_role() -> None:
    draft = make_doc(status=ApprovalStatus.DRAFT, approved_by=None, approved_at=None)
    approved = approve(draft, APPROVER, NOW)
    assert approved.status is ApprovalStatus.APPROVED
    assert approved.approved_by == "approver-1"
    with pytest.raises(AuthorizationError):
        approve(draft, OPERATOR, NOW)
    with pytest.raises(AuthorizationError):
        approve(draft, AI, NOW)


def test_retriever_never_returns_ineligible_or_cross_product_docs() -> None:
    retriever = InMemoryKnowledgeRetriever([
        make_doc(),
        make_doc(document_id="internal", sensitivity=Sensitivity.INTERNAL_ONLY),
        make_doc(document_id="other-product", product_id="maygoosh"),
        make_doc(document_id="draft", status=ApprovalStatus.DRAFT,
                 approved_by=None, approved_at=None),
    ])
    results = retriever.search(product_id="damiish", query="register animal")
    assert [d.document_id for d in results] == ["faq-animal-registration"]
    assert retriever.search(product_id="damiish", query="zzz-no-match") == ()
