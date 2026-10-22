# Roadmap

Staged for fast learning from DAMIISH at low total cost of ownership.
Effort estimates are rough engineering ranges for one experienced engineer,
excluding Meta review waiting time and business/legal decisions.

## Phase 0 — Foundation ✅ (this repository state)
Domain contracts, handover state machine, authorization, knowledge gate,
audit, config/security defaults, CI, docs/ADRs, Meta webhook verification.
No live integrations.

## Phase 1 — DAMIISH Instagram PoC (see `docs/quality/acceptance-criteria.md`)

**Next three implementation tasks (in order):**

1. **Chatwoot CE spike + Meta connection-ownership decision** *(~3–5 days)*
   Deploy CE (pinned `-ce` image) on a dev host; verify: Instagram channel vs.
   our adapter owning webhooks, API/webhooks for takeover/handover signals,
   operator UX for "AI blocked until resume", roles/MFA reality in CE.
   Output: spike report + ADR confirming/revising ADR-0002; kill criteria =
   CE cannot represent our control states without forking.
2. **Persistence + worker** *(~1–2 weeks)*
   PostgreSQL repositories implementing the ports; apply/adapt
   `db/migrations/0001_initial.sql` (migration tool ADR); DB-backed outbox/job
   processing with idempotency + `control_version` CAS; audit store; FTS
   knowledge search (incl. Persian tokenization check) behind the eligibility
   gate. Preserve every foundation invariant as an integration test.
3. **HTTP + live integration wiring** *(~1–2 weeks + Meta lead time; narrowed
   by ADR-0007 — no direct Meta send in the PoC hot path)*
   Thin FastAPI (or equivalent — small ADR) endpoint receiving Chatwoot Agent
   Bot webhooks (signature verification already implemented); REST client for
   Create Message / Toggle Status using the adapter's payload builders;
   operator-identity mapping for takeover/resume (spike R6); test IG account
   end-to-end; then App Review submission. Live switches stay off until the
   acceptance criteria pass. *Parallel business track from day 1:* Meta app +
   business verification, DAMIISH FAQ v1 approval, escalation policy, privacy
   policy — these, not code, are the likely critical path.

Then: AI provider selection (terms/privacy/Persian quality/cost) behind the
`AIProvider` port with shadow-mode (suggest-only) evaluation before any
auto-send; operator runbook; backup/restore drill; limited pilot with named
test customers.

## Phase 2 — Harden & learn (after pilot evidence)
Observability/alerts, retention & privacy implementation, lead classification
v1, quality dashboards (resolution/escalation rates), pgvector *only if* FAQ
miss data justifies it, second channel (website chat) behind the same ports.

## Explicitly later / maybe never
WhatsApp/Telegram/LinkedIn/email agents, MAYGOOSH onboarding (reuse once
DAMIISH proves the loop), content assistance/publishing, CRM features,
multi-agent orchestration, Kubernetes. Each starts with a business case + ADR.
