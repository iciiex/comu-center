# Architecture overview

Status: **foundation implemented** (domain core + ports + fakes). Everything
marked *planned* does not exist yet.

## Logical architecture

```text
                        ┌─────────────────────────────┐
 Customer (Instagram)   │  Meta (official Graph API)  │   planned
        └──────────────►│  webhooks + Send API        │
                        └──────────────┬──────────────┘
                                       │ verified webhook (HMAC), raw body
                        ┌──────────────▼──────────────┐
                        │  Channel adapter (Meta IG)  │   stub: signature/
                        │  normalize → InternalMessage│   handshake only
                        └──────────────┬──────────────┘
   ┌───────────────────┐    ┌──────────▼───────────────┐    ┌─────────────────┐
   │ Operator inbox    │◄──►│  Application layer        │───►│ AI provider     │
   │ Chatwoot CE       │    │  ConversationService:     │    │ port (fake now) │
   │ (planned spike,   │    │  dedupe → retrieve →      │    └─────────────────┘
   │  external system) │    │  suggest → SEND GATE →    │    ┌─────────────────┐
   └───────────────────┘    │  send / escalate / audit  │───►│ Knowledge store │
                            └──────────┬───────────────┘    │ approved+valid  │
                                       │                    └─────────────────┘
                        ┌──────────────▼──────────────┐
                        │  Domain core (pure Python)  │
                        │  messages · conversation    │
                        │  control · authorization ·  │
                        │  knowledge · audit          │
                        └──────────────┬──────────────┘
                        ┌──────────────▼──────────────┐
                        │ PostgreSQL (planned         │
                        │ persistence + FTS)          │
                        └─────────────────────────────┘
```

## Component responsibilities

| Component | Responsibility | Status |
|---|---|---|
| Domain core `invar_comms/domain` | Contracts & invariants: message v1, control state machine, authorization, knowledge eligibility, audit events. No I/O. | Implemented, tested |
| Application `invar_comms/application` | Orchestration & send policy; the only path from suggestion to send. | Implemented (in-memory) |
| Ports `invar_comms/ports` | Provider/channel/retrieval interfaces. | Implemented |
| Adapters `invar_comms/adapters` | Fakes now; Meta IG stub (webhook verification only, sending disabled). | Fakes done; Meta stub |
| Operator inbox | Human queue, assignment, reply UI. **Buy (Chatwoot CE), don't build** — ADR-0002. | Planned spike |
| Persistence | Messages/conversations/knowledge/audit + outbox. PostgreSQL is the production target (FTS first). | Repository contracts + SQLite adapter implemented & tested (ADR-0008); Postgres adapter pending infra |
| Product adapters | DAMIISH/MAYGOOSH-specific knowledge & policies, *data and config*, not forks of the core. No AI access to product production DBs. | Planned |

## Boundaries that matter

1. **Product isolation** — every message, conversation, knowledge doc, actor
   scope, and (proposed) DB row carries `product_id`; authorization fails
   closed outside scope.
2. **Send gate** — `ConversationService` re-checks authorization, kill-switch,
   control state + version, confidence, and knowledge grounding at send time.
3. **Inbox independence** — Chatwoot (if adopted) talks to the core via APIs/
   webhooks; the core keeps its own conversation-control truth so the inbox is
   replaceable. Exit strategy: another inbox or a thin custom UI on the same
   core contracts.
4. **Provider independence** — swapping AI providers means one new adapter
   behind `AIProvider`; prompts never become authorization.

Deliberately absent (ADR-0005): microservices, Kubernetes, Dify, n8n, vector
DB, multi-agent systems. Each needs a demonstrated need + new ADR.
