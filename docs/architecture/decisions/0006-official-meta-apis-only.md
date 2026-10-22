# ADR-0006: Official Meta APIs only — prepare, don't fake

Status: accepted; foundation implements verification helpers only.

**Context.** Instagram automation via scraping/browser bots/password sharing
risks account bans and violates platform terms. Official integration requires a
Meta app, the right login route (Instagram Login vs Facebook Login),
permissions/App Review for public use, webhook verification, and respect for
Meta's messaging windows (24h standard; human-agent tag up to 7 days for
genuine human support — verify current policy at build time).

**Decision.** Official Graph APIs only. Foundation ships: webhook handshake +
`X-Hub-Signature-256` HMAC verification (tested), a normalization stub that
fails closed, and a send method that raises `LiveSendDisabled`. Live sending
requires — in order — approved test app + permissions, secrets via the manager,
both kill-switches explicitly on, and contract tests against a test account.

**Consequences.** + No ban/ToS risk, no fake "integration"; + security posture
verifiable early. − Time-to-first-live-message includes Meta review lead time
(plan for it in the roadmap; test users/roles work before Advanced Access).

Details and prerequisites checklist: `docs/integrations/meta-instagram.md`.
