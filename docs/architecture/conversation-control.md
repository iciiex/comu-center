# Conversation control & human handover

Implemented in `src/invar_comms/domain/conversation.py` +
`authorization.py`; enforced again in
`src/invar_comms/application/conversation_service.py`; tested in
`tests/test_conversation_control.py` / `test_conversation_service.py`.

## State model

```text
            request_handover              accept_handover
 AI_ACTIVE ───────────────► HANDOVER_REQUESTED ─────────────► HUMAN_ACTIVE
    ▲                                │                             │
    │                                └── accept = takeover ────────┘
    └──────────────────── resume_ai (explicit, human only) ────────┘
```

- **AI_ACTIVE** — AI may send, subject to the full send gate.
- **HANDOVER_REQUESTED** — AI sending is *already blocked* (escalation is the
  fail-safe direction; the AI itself may request it and thereby silences itself).
- **HUMAN_ACTIVE** — a named human owns it. AI sending blocked. The **only**
  exit is `resume_ai` by an authorized operator/admin. The AI can never resume
  or take over (`Role.AI_SYSTEM` lacks those actions).

## Race-condition defence

1. Every control change increments `control_version` (optimistic concurrency).
2. The service captures the version **before** generating a reply and calls
   `assert_ai_may_send(version)` **at send time**. A takeover (even one later
   resumed) makes the in-flight generation stale → `AISendBlocked`, audited.
3. In-memory transitions hold a per-conversation lock. With PostgreSQL the same
   invariant becomes `UPDATE ... WHERE control_version = :expected` inside the
   send transaction (PoC task 2 must preserve this; it is an acceptance test).
4. Duplicate inbound events are deduplicated by idempotency key before any
   generation, so webhook redelivery cannot double-send.
5. Kill-switches (`INVAR_AI_SEND_ENABLED=false`) block sending globally,
   independent of conversation state.

## Authorization matrix (summary)

| Action | Admin | Operator | Content approver | AI system | Read-only |
|---|---|---|---|---|---|
| suggest / send (AI) | ✓ | – | – | ✓ (gated) | – |
| human send | ✓ | ✓ | – | – | – |
| request handover | ✓ | ✓ | – | ✓ | – |
| accept handover / resume AI | ✓ | ✓ | – | **never** | – |
| approve / edit knowledge | ✓ | – | ✓ | **never** | – |

All actions additionally require the actor's product scope to include the
conversation's `product_id` (fail closed). A prompt, message, or document is
not an actor and can grant nothing.
