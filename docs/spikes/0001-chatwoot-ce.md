# Spike 0001 — Chatwoot CE as operator inbox & Meta connection owner

**Date:** 2026-10-22 · **Type:** desk spike (official-docs evidence) · **Status:**
desk phase complete; **live phase pending** (no Docker host available in the
authoring sandbox — nothing here claims a running Chatwoot).
Decision recorded in **ADR-0007**. Target pin: **Chatwoot v4.19.0** (latest
stable release, 2026-10-20, verified via GitHub Releases API; use the CE image).

## Questions & evidence

| # | Question | Finding (source) | Verdict |
|---|---|---|---|
| Q1 | Can CE represent "AI active vs human owns it"? | Agent Bot model: bot-connected inboxes create conversations as `pending` (bot triages); bot hands off by toggling status to `open`; agents return a conversation to the bot by setting it back to `pending` [1]. | **Yes, maps cleanly** (see mapping table) |
| Q2 | Can the Invar core stay the control authority? | Bot receives webhook events; replies via Create Message API; handoff via Toggle Status API (`open/pending/resolved/snoozed`) [2][3]. Our core decides every send; Chatwoot status is treated as a *projection/signal*, never as truth (adapter returns signals; the domain state machine re-validates). | **Yes, by design** |
| Q3 | Instagram channel maturity? | Dedicated Instagram channel since v4.1 using **Instagram Business Login** (recommended; Facebook-Login route deprecated from v4.1). Still self-hosted = **our own Meta app**, IG professional account, webhook `{chatwoot}/webhooks/instagram`, subscribe `messages` (+seen/reactions), testers before production, Meta app verification for production [4]. | **Usable; Meta lead time unchanged** |
| Q4 | Webhook authenticity & event coverage? | Docs specify signed deliveries: `X-Chatwoot-Signature: sha256=HMAC-SHA256(secret,"{timestamp}.{raw_body}")`, `X-Chatwoot-Timestamp`, `X-Chatwoot-Delivery` [5] — implemented in `adapters/chatwoot.py` with freshness window. **But:** signing is recent/version-sensitive, a secret-source bug was reported for API-created account webhooks (R2), and docs note `conversation_status_changed` was "not supported yet" via agent-bot APIs while the changelog later says it is dispatched to bots (R3). | **Implement + must verify live** |
| Q5 | Least-privilege auth for the bot? | Agent bots get their own access token, scoped to bot-permitted endpoints (create message, toggle status/priority, assignments, labels) vs. user/admin tokens [2][6]. Auth header: `api_access_token` (Bearer added in v4.19 per API docs — pin behavior at deploy). | **Good enough for PoC** |
| Q6 | Product isolation (DAMIISH vs MAYGOOSH)? | Chatwoot *accounts* isolate inboxes/users. Plan: **one Chatwoot account per product** + explicit `inbox → product` mapping enforced in our adapter (unknown inbox = reject, already tested). CE lacks EE custom roles/SSO, so operator→core `Actor` mapping stays in our core. | **Yes, with account-per-product** |
| Q7 | Channel limits that affect the core? | Instagram: max **1000 chars**/message; cannot start outbound conversations; 24h window (7d only with human-agent) surfaced in UI [7]. Our payload builder enforces 1000 chars (tested). Comments need a separate Meta permission — out of PoC scope. | **Handled in adapter** |
| Q8 | Operational burden? | Rails + Sidekiq + Postgres + Redis (upstream compose), ~4 GB RAM class; Meta/IG tokens need lifecycle attention (community reports ~60-day token refresh issues, sender-identification quirks in some IG setups) (R4/R5). | **Acceptable for pilot; monitor** |

## Meta connection ownership — options

| | A: Chatwoot native IG channel owns Meta (**chosen**, ADR-0007) | B: Invar core owns Meta; Chatwoot = API-channel inbox |
|---|---|---|
| PoC speed | Fast — channel, windows, retries are upstream features | Slow — we build Meta send/normalize + Chatwoot sync |
| Control | Core is Agent Bot; state machine still gates every send | Maximum direct control |
| Lock-in | Bot webhook/API is our only coupling; exit = re-point bot or move to B | Lower inbox lock-in, higher build/maintain cost now |
| Risk | Chatwoot channel quirks (R4), event coverage (R3) | More of our code in the hot path before product proof |

Exactly one system subscribes to Meta webhooks in option A (Chatwoot), so the
"double webhook = double reply" failure mode is avoided. The foundation's
direct-Meta verification helpers remain the **exit path** to option B.

## Control-state mapping (core ⇄ Chatwoot)

| Invar core | Chatwoot projection | Signal back into core |
|---|---|---|
| `ai_active` | status `pending`, bot assigned | `message_created` (incoming, sender=contact) → process via send gate |
| `handover_requested` | bot calls toggle_status `open` (+ private note with reason) | `conversation_status_changed=open` / operator reply → confirm AI blocked |
| `human_active` | status `open`, human assignee | operator `message_created` (outgoing, sender=user) → ensure takeover recorded |
| explicit resume | operator sets status `pending` | **Resume signal only** — core requires mapping the acting operator to an authorized `Actor` before `resume_ai`; a bare status webhook never resumes the AI by itself (R6) |
| loop guard | bot's own messages echo back as webhooks | sender.type=`agent_bot` → ignored (tested) |

## Kill criteria (re-check ADR-0002 if any triggers)
None triggered by desk evidence. Still open until live phase: status-event
coverage to the bot (R3), signature verification with the actual secret (R2),
correct IG sender identification (R4). Any of these failing without a
workaround that preserves our invariants = fall back to option B or a custom
thin inbox (new ADR; do not fork Chatwoot casually).

## Risks / open questions
- **R2** Signed-webhook secret source may differ between UI- and API-created
  webhooks in some versions (upstream issue #13809). Live step L3 must prove
  verification end-to-end; until then treat our verifier as doc-based.
- **R3** Does the pinned version deliver `conversation_status_changed` to
  agent bots? Mitigation: also subscribe an account-level webhook for it.
- **R4** IG sender identity/profile display issues reported in community
  discussions; verify `contact_inbox.source_id` stability for our contact key.
- **R5** Token expiry/refresh behavior for the IG channel; needs an ops check
  + alert before pilot (silent DM stoppage is the failure mode).
- **R6** "Who pressed pending?" — resume attribution. Options for live phase:
  conversation_updated changed-attributes actor, assignee heuristics (weak),
  or require resume through our own minimal endpoint/link. Decide in Task 3.
- **R7** CE has no SSO/SAML or fine-grained roles (EE). Compensate: strong
  passwords + MFA where available, minimal operator accounts, core audit.

## Live-spike runbook (next, on a Docker host — ~1–2 days of the original 3–5)
1. Deploy upstream Chatwoot at tag **v4.19.0** (CE image) following the
   official self-hosted Docker guide; keep DB/Redis unexposed; HTTPS in front.
2. Create account "DAMIISH (pilot)", operator users, Agent Bot pointing at a
   reachable test endpoint for our core; record bot token + secret via the
   secrets process (never in git).
3. **L3 signature proof:** capture a real bot webhook; verify with
   `verify_chatwoot_signature`; tamper and replay must fail.
4. Connect a **test** Instagram professional account via Instagram Business
   Login (Meta testers; app in dev/test mode — no customers).
5. Walk the mapping table: inbound DM → pending → bot reply (fake provider,
   send gate on) → handoff `open` → operator reply → AI stays silent →
   operator returns to `pending` → resume path per R6 decision.
6. Verify: duplicate webhook delivery dedupe, 1000-char limit, 24h-window UI
   behavior, sender `source_id` stability, status-changed delivery to bot.
7. Record results in this file (append "Live phase results"), then confirm or
   revise ADR-0007. Only then schedule App Review work.

## Sources (accessed 2026-10-22)
1. Agent bots & handoff: https://www.chatwoot.com/hc/user-guide/articles/1677497472-how-to-use-agent-bots
2. Toggle status API: https://developers.chatwoot.com/api-reference/conversations/toggle-status · Create message: https://developers.chatwoot.com/api-reference/messages/create-new-message
3. Agent Bot API overview: https://www.chatwoot.com/features/chatbots
4. Instagram Business Login setup: https://developers.chatwoot.com/self-hosted/configuration/features/integrations/instagram-via-instagram-business-login
5. Webhooks & verification: https://www.chatwoot.com/hc/user-guide/articles/1677693021-how-to-use-webhooks
6. Create agent bot (platform API): https://developers.chatwoot.com/api-reference/agentbots/create-an-agent-bot
7. Supported channel features/limits: https://developers.chatwoot.com/self-hosted/supported-features
