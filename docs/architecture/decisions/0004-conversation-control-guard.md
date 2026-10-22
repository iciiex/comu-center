# ADR-0004: Server-side conversation control with control_version guard

Status: accepted; implemented and tested.

**Context.** The #1 product-safety invariant: once a human takes over, the AI
must not send again until an explicit authorized resume — including when a
reply was already being generated, or a webhook is redelivered.

**Decision.** Explicit state machine (`ai_active → handover_requested →
human_active → ai_active` only via authorized resume). Escalation itself
blocks AI sending. Every transition increments `control_version`; senders
capture it before generation and re-validate at send time. Authorization is
role- + product-scoped and fail-closed; the AI role can request handover but
never accept/resume/approve. All transitions and blocked sends are audited.

**Consequences.** + Race-safe by construction, portable to SQL CAS later;
+ prompt-injection cannot alter control state. − Slightly more ceremony in the
send path (worth it).

**Alternatives rejected.** Prompt-level "stop if human replied" (unenforceable);
boolean `bot_enabled` flag without versioning (loses the mid-generation race);
relying on the inbox's assignment state as the only guard (inbox is replaceable).
