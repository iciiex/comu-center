# ADR-0007: Chatwoot owns the Instagram connection; core integrates as Agent Bot

Status: accepted for the PoC, **conditional on the live-spike checklist** in
`docs/spikes/0001-chatwoot-ce.md` (desk evidence only so far). Extends ADR-0002.

**Context.** The spike found Chatwoot's Agent Bot model maps directly onto our
control states (`pending`=bot triage ⇄ `open`=human), its dedicated Instagram
channel (v4.1+, Instagram Business Login) already implements Meta plumbing and
window restrictions, and bot tokens are least-privilege. Rebuilding that in
our core before any product proof would violate the "prefer mature OSS"
principle. Details/risks: spike 0001 (Q1–Q8, R2–R7).

**Decision.** For the DAMIISH PoC: (1) Chatwoot CE (pinned v4.19.0-CE) is the
single subscriber to Meta webhooks and owns sending to Instagram; (2) the
Invar core connects as an **Agent Bot** — signed webhooks in, Create-Message /
Toggle-Status API out; (3) the core state machine remains the only send
authority — Chatwoot status is a projection, webhook signals never mutate core
state directly, and "back to pending" alone never resumes the AI without an
authorized-actor record; (4) one Chatwoot account per product, inboxes
explicitly mapped to `product_id` in our adapter (unknown inbox = reject).

**Consequences.** + Fastest credible path to the pilot; + Meta token/channel
maintenance largely upstream; + exit preserved (direct-Meta adapter = option B).
− We inherit Chatwoot event-coverage/version quirks (R2/R3) — both are
live-spike gates, and our send gate stays safe even if Chatwoot misbehaves;
− foundation `adapters/meta_instagram.py` becomes the *exit-path* component
rather than the PoC hot path (kept, still tested).

**Alternatives rejected (for now).** Core-owns-Meta + API-channel inbox
(option B: more control, too much build pre-proof); Chatwoot Captain AI
(enterprise/paid, duplicates our core's job); letting Chatwoot status be the
control truth (inbox must stay replaceable; a status flip is not an
authorized resume).
