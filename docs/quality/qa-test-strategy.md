# QA & Test Strategy (prototype)

- Status: **PARTIAL** — automated tests exist for the demo path; full strategy is doc 10.
- Mode: P

## Implemented automated coverage (43 tests)
- Health/mode banner; login page and demo users.
- Mission eligibility: date window, status, org (BR-001).
- Submit → review → score end-to-end; second approval blocked; no duplicate events.
- Rejection requires a reason and awards nothing.
- Role/authorization negatives (visitor/operator) and cross-org access.
- Rule-version publication on points change; historical event untouched.
- Max-per-user enforcement; duplicate `request_id` idempotency.
- Scoring: idempotent award, ledger == wallet, explain payload, active version selection.
- Jalali conversion and Persian digits.
- Session fallback without cookies: `?s=` token authenticates GET and multipart POST, links keep the token.
- CSRF: missing/forged tokens rejected (403), uploads with forged tokens create nothing, forms render the field.
- Expired token rejected; cookie sessions keep clean URLs.
- Demo-login rate limit → 429.
- Security headers present and framing deliberately not denied (preview iframe).
- Persian 404 page for unknown routes.
- Review queue pagination and page clamping.
- Evidence retention purge: only old rows/files removed, audit row written, `--dry-run` deletes nothing.
- Score corrections: negative event + ledger + wallet + outbox + audit; double correction 409; blank reason 409;
  correction-of-correction rejected; admin-only (operator/visitor 403); cross-org 403; unknown event 404;
  CSRF required; `/score` marks the correction; totals return to zero.

## Not covered yet
- Sales import, reports, notifications (features not built).
- Load/performance, security scanning, UAT scripts.
- Multi-worker behaviour of the in-memory rate limiter and session store.
- Browser E2E (only HTTP-level tests).

## Commands
`.venv/bin/pytest` · `.venv/bin/ruff check app tests`

## Rule
Never report an unrun test as passing. Golden data for scoring must be versioned with the rule.
