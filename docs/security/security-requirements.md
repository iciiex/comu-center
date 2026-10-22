# Security requirements

**Authentication & authorization**
- Operators authenticate via the inbox (Chatwoot) — MFA required for admins;
  evaluate SSO licensing in the spike (SSO is a Chatwoot enterprise feature).
- Every customer-affecting action passes `domain.authorization.require`
  (role + product scope, fail closed) and writes an audit event.
- Service-to-service calls use scoped, rotatable tokens; never operator passwords.

**Secrets & configuration** — see `secrets-management.md`. Startup validation
fails fast on inconsistent/missing production secrets; secrets never appear in
logs, errors, or `repr`.

**Transport & storage**
- HTTPS everywhere externally (webhook endpoint must be publicly reachable over
  TLS for Meta); HSTS at the edge. Databases/dashboards are never published
  publicly (compose default keeps Postgres unexposed).
- Encryption at rest via the hosting platform before real customer data;
  field-level encryption only if a later assessment demands it.

**Input handling**
- Webhooks: verify signature on the *raw* body before parsing; size-limit
  payloads; treat all message/document text as untrusted.
- No `eval`/shell on external input; parameterized SQL only (future adapter).

**AI-specific**
- Grounding: approved knowledge only (eligibility gate). Confidence floor +
  escalation keywords (pricing/contract/complaint) route to humans — the exact
  keyword/policy list is a DAMIISH business decision, tracked in the roadmap.
- Customer data sent to an AI provider is minimized (message + excerpts);
  provider must contractually not train on it (selection criterion).

**Operations**
- Backups encrypted + restore-tested (`docs/operations/backup-and-recovery.md`).
- Audit events are append-only; alert on `ai_send_blocked` spikes and repeated
  signature failures once the HTTP endpoint exists.
- Dependency & secret scanning in CI on every PR (already wired).
