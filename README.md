# Invar AI Operations & Communications Platform (`comu-center`)

Reusable AI operations and customer-communications platform by **Invar**.
First pilot product: **DAMIISH** (livestock farm management). Future products
(e.g. MAYGOOSH) reuse the same core with product-scoped data, knowledge, and
permissions.

## Status: engineering foundation (Phase 0) — not production, no live integrations

What exists today:

- A **provider-independent Python core** (`src/invar_comms/`) with zero runtime
  dependencies: versioned internal message contract, human-takeover
  conversation-control state machine, explicit product-scoped authorization,
  approved-knowledge eligibility gate, and audit events.
- **Ports** for AI providers, knowledge retrieval, and channel adapters, plus
  deterministic **fakes** for tests/local exercise.
- **Meta/Instagram preparation only**: unit-tested webhook handshake and
  `X-Hub-Signature-256` verification helpers. Live sending is *not* implemented
  and raises `LiveSendDisabled`. See `docs/integrations/meta-instagram.md`.
- **Chatwoot spike (desk phase) done**: ADR-0007 — Chatwoot CE will own the
  Instagram connection, the core attaches as an Agent Bot. Signed-webhook
  verification + event mapping implemented and tested
  (`adapters/chatwoot.py`); no Chatwoot is deployed yet — live phase in
  `docs/spikes/0001-chatwoot-ce.md`.
- CI (lint incl. security rules, type-check, tests, config validation,
  dependency audit, secret-pattern scan), Docker Compose dev skeleton
  (PostgreSQL, not exposed), and the docs below.

What does **not** exist yet (planned, see `docs/roadmap.md`): HTTP API/webhook
endpoint, database persistence, operator inbox deployment (Chatwoot CE spike),
any real AI provider, and any Meta connectivity. Nothing in this repo has
messaged a real customer.

## Quick start (local)

Requires Python 3.11+.

```bash
make setup        # venv + dev dependencies
make check        # lint + type-check + tests + config validation
```

Equivalent manual commands:

```bash
python3 -m venv .venv
.venv/bin/pip install --upgrade pip setuptools wheel
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest
.venv/bin/ruff check src tests
.venv/bin/mypy
cp .env.example .env   # safe local defaults; never commit .env
.venv/bin/python -m invar_comms config-check   # secrets are redacted in output
.venv/bin/python -m invar_comms health
```

Optional Docker dev environment (requires Docker; PostgreSQL stays unexposed):

```bash
docker compose config   # validate
docker compose up db    # database only; the `core` service is a CLI skeleton
```

## Demo site (Vercel)

A static showcase + interactive simulation of the conversation-control rules
lives in `public/` with a serverless health check in `api/health.py`. Deploy
by importing this repo on Vercel (zero configuration — see
`docs/operations/vercel-demo.md`). It is a demo: no channel is connected and
nothing can message a customer from it.

## Safety defaults

- AI sending and Meta live sending are **off** unless explicitly enabled
  (`INVAR_AI_SEND_ENABLED`, `INVAR_META_LIVE_SEND_ENABLED`) — see `.env.example`.
- Human takeover blocks AI sending server-side until an authorized, explicit
  resume. Prompts/messages/documents can never override this.
- Only approved, currently valid, product-scoped `public_faq` knowledge may
  ground an automatic reply. Otherwise the conversation escalates to a human.

## Documentation map

| Topic | File |
|---|---|
| Architecture overview | `docs/architecture/overview.md` |
| Architecture decisions | `docs/architecture/decisions/` |
| Message contract | `docs/architecture/message-contract.md` |
| Conversation control | `docs/architecture/conversation-control.md` |
| Knowledge base | `docs/architecture/knowledge-base.md` |
| Roadmap | `docs/roadmap.md` |
| Open-source evaluation | `docs/open-source-evaluation.md` |
| Security | `docs/security/` + `SECURITY.md` |
| Operations | `docs/operations/` |
| PoC acceptance criteria | `docs/quality/acceptance-criteria.md` |
| Meta/Instagram plan | `docs/integrations/meta-instagram.md` |
| Contributing | `CONTRIBUTING.md` |

Products: DAMIISH first; the platform and its IP belong to Invar (see `LICENSE.md`).
