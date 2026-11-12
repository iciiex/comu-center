# QA & Test Strategy (prototype)

- Status: **PARTIAL** — automated tests exist for the demo path; full strategy is doc 10.
- Mode: P

## Implemented automated coverage (71 tests on 2026-11-12)

Which test covers which route and function: `docs/agent-guide/code-map.md` §3, §4 and §7.
Routes and requirements without a test are listed there and in `docs/agent-guide/traceability.md`.

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
- Sales import: validation without scoring, counts by status, row-level messages with row numbers,
  fingerprint duplicate 409, cross-import duplicate skipped, missing headers rejected, non-xlsx rejected,
  idempotent processing (second run `processed=0`), sub-unit amount awards nothing, admin-only, CSRF,
  org scope, reconciliation panel.
- Score corrections: negative event + ledger + wallet + outbox + audit; double correction 409; blank reason 409;
  correction-of-correction rejected; admin-only (operator/visitor 403); cross-org 403; unknown event 404;
  CSRF required; `/score` marks the correction; totals return to zero.
- Documentation: generated agent documents are fresh; the code map lists exactly the served routes
  (`tests/test_docs.py`).
- Demo stability (`tests/test_demo_stability.py`): A1 rollback/effective-rule regressions, A6 navigation/
  badge/pending-count/typo fixes, admin-only SAMPLE workbook download, A2 correction from the admin
  review screen and sales import detail (admin-only/org-scoped), and a replay of the documented demo
  path including sales import and the optional mission-score correction.

## Not covered yet
- Reports and notifications (features not built).
- Multi-sheet / column-mapped imports and very large files (limits tested only at the boundary).
- Load/performance, security scanning, UAT scripts.
- Multi-worker behaviour of the in-memory rate limiter and session store.
- Browser E2E (only HTTP-level tests).

## Commands
`make check` (= `.venv/bin/ruff check app tests` + `.venv/bin/pytest`) · `make docs-check` ·
`make doctor`

## Rule
Never report an unrun test as passing. Golden data for scoring must be versioned with the rule.
