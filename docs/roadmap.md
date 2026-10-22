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
2. **Persistence + worker** *(core ✅ 2026-10-22 — repository/outbox ports +
   SQLite adapter with CAS `control_version`, restart-safe idempotency,
   append-only audit, eligibility-filtered knowledge search, outbox worker;
   contract-tested. Remaining: PostgreSQL adapter against the same contracts
   on a real hosted DB (needs the Docker/hosting step), migration tooling,
   and FTS incl. the Persian tokenization check, ~3–5 days once infra exists.)*
3. **HTTP + live integration wiring** *(engineering core ✅ 2026-10-22 —
   stdlib HTTP adapter (ADR-0009) with signed Chatwoot/Meta webhook intake →
   outbox → processing with full send gate; Chatwoot REST client for Create
   Message / Toggle Status, stub-tested; `serve`/`worker` CLI smoke-tested
   end-to-end. Resume attribution (spike R6) is deliberately conservative:
   a bare `pending` flip never resumes the AI, unmapped operator replies still
   block it fail-safe. Remaining is not code-shaped: live Chatwoot + test IG
   account on a Docker host, operator-identity mapping data, then Meta App
   Review. Live switches stay off until the acceptance criteria pass.
   *Parallel business track:* Meta app + business verification, DAMIISH FAQ
   v1 approval, escalation policy, privacy policy — the likely critical path.)*

Then: AI provider selection (terms/privacy/Persian quality/cost) behind the
`AIProvider` port with shadow-mode (suggest-only) evaluation before any
auto-send; operator runbook; backup/restore drill; limited pilot with named
test customers.

> Update (ADR-0010): the **direct single-account product path is built and
> stub-proven end-to-end** — Meta normalization/send, OpenAI-compatible AI
> adapter (free tiers/local Ollama), token-gated inbox API, `kb-import`, and a
> Persian owner setup guide. Next is the owner's live hookup (their Meta app +
> public HTTPS), then shadow-mode evaluation on real FAQ traffic.

## Phase 2 — Harden & learn (after pilot evidence)
Observability/alerts, retention & privacy implementation, lead classification
v1, quality dashboards (resolution/escalation rates), pgvector *only if* FAQ
miss data justifies it, second channel (website chat) behind the same ports.

## Explicitly later / maybe never
WhatsApp/Telegram/LinkedIn/email agents, MAYGOOSH onboarding (reuse once
DAMIISH proves the loop), content assistance/publishing, CRM features,
multi-agent orchestration, Kubernetes. Each starts with a business case + ADR.
