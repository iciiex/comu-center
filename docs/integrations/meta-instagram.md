# Meta / Instagram integration plan (prepare, do not fake)

Status: **implemented, not yet connected to a real account**. Implemented and
tested today (ADR-0010): handshake + signature verification, webhook
normalization of `entry[].messaging[]`, Graph send client
(`POST /{version}/{ig_id}/messages`, refuses to run unless live switches +
credentials are set), and processing through the core send gate — proven
end-to-end against local stub AI/Graph servers. Connecting a real account is
an owner-side task: `docs/operations/instagram-ai-setup-fa.md`.
Verify every platform fact below against current official Meta documentation at
build time — policies, permission names, and windows change.

## Boundary
Our Meta adapter is the *only* component that speaks to Meta. It verifies
webhooks, normalizes events into `InternalMessage` v1, and (future) sends via
the official Send API after the core's send gate. Decide during the Chatwoot
spike whether Chatwoot's Instagram channel or this adapter owns the Meta
connection — **exactly one owner** (double webhooks = duplicate replies).

## Prerequisites checklist (owner actions, engineering cannot shortcut)
- [ ] Meta developer account + app; **business verification** if required.
- [ ] DAMIISH Instagram **professional** account; choose login route:
      Instagram Login (`instagram_business_basic`,
      `instagram_business_manage_messages`) vs Facebook Login
      (`instagram_basic`, `instagram_manage_messages`, `pages_*`) — confirm
      current names/scopes in official docs and pick one deliberately.
- [ ] **App Review / Advanced Access** for messaging people without an app
      role (Standard Access suffices only for app-role test users).
- [ ] Public HTTPS webhook endpoint (FastAPI adapter, PoC task 3) responding
      within Meta's timeout; background processing after the 200.
- [ ] Privacy policy URL + data-handling answers for App Review (legal input).
- [ ] Test accounts/roles for end-to-end contract tests before any customer.

## Webhook authenticity & delivery (implemented core, endpoint pending)
- GET handshake: `hub.mode=subscribe` + constant-time `hub.verify_token`
  check → echo `hub.challenge` (`verify_webhook_subscription`).
- POST events: verify `X-Hub-Signature-256` = HMAC-SHA256(**raw body**, app
  secret), constant-time compare, before parsing (`verify_payload_signature`).
  Missing secret/header = reject. Meta signs payloads this way; there is no
  timestamp in the signature, so replay defence = our idempotency key + DB
  uniqueness + processing timestamps.
- Assume **at-least-once delivery**: dedupe by idempotency key (done in core),
  ack fast, process async, bounded retries with audit on failure.

## Messaging policy guardrails (verify in official docs at build time)
- Standard reply window: **24 hours** from the user's last message.
- `HUMAN_AGENT` tag extends human (non-automated) support replies to **7 days**
  and needs its own approval — it must never be used for AI auto-replies.
  Our core can *enforce* this distinction (human_send vs ai_send actions).
- Comments → private replies have their own one-message/window rules; treat
  comment handling as a separate, later scope with its own tests.
- Rate limits exist per endpoint/account; the worker must back off, not burst.

## Tokens & secrets
App secret / verify token / access tokens via the secrets manager
(`docs/security/secrets-management.md`). Plan for token expiry/refresh per the
chosen login route (long-lived tokens still expire/rotate; revocation by an
account admin must page the operator, not fail silently). Never log tokens.

## Explicitly forbidden
Scraping, browser automation, credential sharing, unofficial APIs, purchased
"DM automation" proxies. If the official API cannot do it, we don't do it.

## Test strategy without live access
Contract tests with recorded/synthetic webhook payloads (signed with a test
secret), signature-tamper cases (done), duplicate-delivery cases (done), and a
fake channel for end-to-end service tests (done). Live verification happens
only with app-role test users on the DAMIISH test setup.
