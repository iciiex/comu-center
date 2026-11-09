# QA & Test Strategy (prototype)

- Status: **PARTIAL** — automated tests exist for the demo path; full strategy is doc 10.
- Mode: P

## Implemented automated coverage (18 tests)
- Health/mode banner; login page and demo users.
- Mission eligibility: date window, status, org (BR-001).
- Submit → review → score end-to-end; second approval blocked; no duplicate events.
- Rejection requires a reason and awards nothing.
- Role/authorization negatives (visitor/operator) and cross-org access.
- Rule-version publication on points change; historical event untouched.
- Max-per-user enforcement; duplicate `request_id` idempotency.
- Scoring: idempotent award, ledger == wallet, explain payload, active version selection.
- Jalali conversion and Persian digits.

## Not covered yet
- Sales import, reports, notifications (features not built).
- Load/performance, security scanning, UAT scripts.
- Browser E2E (only HTTP-level tests).

## Commands
`.venv/bin/pytest` · `.venv/bin/ruff check app tests`

## Rule
Never report an unrun test as passing. Golden data for scoring must be versioned with the rule.
