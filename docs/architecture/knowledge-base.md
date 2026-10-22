# Knowledge base contract

Implemented in `src/invar_comms/domain/knowledge.py` and
`src/invar_comms/ports/knowledge_retrieval.py`; tested in
`tests/test_knowledge.py`.

## Document model

`document_id`, `version` (≥1, immutable once approved — changes ship as a new
version), `product_id`, `title`, `content`, `source`, `status`
(`draft → in_review → approved → retired`), `sensitivity`
(`public_faq | internal_only | restricted`), `approved_by`/`approved_at`
(mandatory for approved docs), optional `valid_from`/`valid_until`,
`updated_at`.

## Eligibility gate (single, fail-closed)

A document may ground an **automatic** reply only if **all** hold:
same `product_id` as the conversation · status `approved` · sensitivity
`public_faq` · currently within validity window. Approval requires an actor
with `approve_knowledge` in that product scope (approver/admin; never the AI).

If retrieval returns no eligible document, the service **escalates to a
human** — it must never invent features, prices, availability, or account data.

## Editing & versioning workflow (operational)

1. Product team drafts/updates content from an authoritative `source`.
2. Approver reviews and approves (recorded: who, when) → new version.
3. Expired/superseded versions are retired or given `valid_until`.
4. System prompts reference *policy* (tone, escalation), never product facts —
   facts live only here, so they can be corrected without redeploying prompts.

## Retrieval strategy

Now: deterministic keyword retrieval (tests). PoC: PostgreSQL full-text search
over the same eligibility filter. Semantic retrieval (pgvector) only after a
measured FAQ-miss problem justifies it (ADR-0003). Retrieved text is untrusted
input to the model: it informs content, it cannot change permissions or state.
