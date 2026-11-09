# Current Project State

- Last updated: 2026-11-09 (۱۸ آبان ۱۴۰۵)
- Updated by: Kiloos engineering agent
- Mode: P
- Current phase: Prototype
- Current milestone: MS-01 — Prototype Delivery (2026-11-18)
- Main branch / working branch: `main` / `arena/0d62c7d3-comu-center`

## Working features
- Demo login with 5 seeded users (visitor ×3, operator, admin) and role-aware redirect.
- Cookie-less session fallback: signed token in `?s=` propagated through links/forms/redirects, so the
  demo works inside the embedded preview where third-party cookies are blocked (D-002).
- CSRF guard on every state-changing route (value derived from the session token), rate-limited demo login,
  security headers, Persian 404/403/422 pages, paginated review queue.
- Mission list/detail filtered by `status=active`, date window, and organization (BR-001); expired and draft missions are hidden.
- Photo submission with type/size validation, private storage, sha256, and `request_id` idempotency (`UNIQUE(user_id, request_id)`).
- Operator review queue with approve/reject; rejection reason required; state machine blocks double review (409).
- Scoring on approval: append-only `score_events`, `idempotency_key`, ledger row, wallet projection, outbox row in one transaction.
- "Why this score" explanation surfaced to the user (rule code, version, conditions, sample flag).
- Wallet + score history; period leaderboard with rank and temporary tie-break.
- Admin mission CRUD: create draft → publish → archive; changing points publishes a new rule version and retires the old one.
- Server-side authorization: visitor / operator / admin + same-organization scope (negative tests exist).

## In progress
- Sales-import vertical slice (EP-07): contract documented in `.agent/playbooks/sales-import.md`; no code/table yet.
- Reports (EP-10) and notifications (EP-11): not started.
- Correction/reversal flow for score events: schema column exists (`corrects_event_id`), flow not implemented.

## Mocked / Demo-only
- **Auth:** demo user picker instead of OTP/SMS (OD-01). Exit condition: approved login method + provider.
- **Tenant:** one organization; multi-company not exposed (OD-02). Exit: approved org model.
- **Points:** all seeded values (10/15/5/20) are `SAMPLE` (OD-04/05). Exit: approved rule matrix.
- **Wallet:** non-redeemable, display only (OD-08). Exit: approved wallet policy.
- **Dates in admin forms:** Gregorian input, Jalali display. Exit: unified calendar in Harden.
- **Leaderboard:** computed on read with proposed tie-break (BR-009). Exit: approved competition criteria + snapshot strategy.

## Known issues
- `?s=` puts the session token in the URL (history/logs/referrer); demo-only, exit condition in D-002.
- Rate limiting and session state live in process memory (single-worker only).
- Evidence retention is a manual command; no scheduler, and the 90-day window is a sample default (D-003).
- SQLite single-writer; no connection pooling or WAL tuning yet.
- Mission and leaderboard lists are still unpaginated (queue is paginated).
- `alembic`-style migration runner absent; schema executes at startup (prototype only).
- `tests/` uses FastAPI TestClient; Starlette emits a deprecation warning about `httpx` (harmless for now).

## Decisions approved
- None yet. D-001 (FastAPI + SQLite for prototype) is **PROPOSED**.

## Open decisions / assumptions
- OD-01…OD-12 remain OPEN (see `docs/decisions/open-decisions.md`).
- Assumptions in force: A-P1 demo auth, A-P2 single tenant, A-P3 photo mission, A-P4 manual review,
  A-P5 sample fixed points, A-P7 temporary tie-break, A-P8 non-redeemable wallet.

## Recent migrations / API changes
- `db/migrations/0001_init.sql`: initial schema (organizations, users, missions, scoring_rule_versions,
  submissions, submission_evidences, score_events, point_transactions, point_wallets, competitions,
  audit_logs, outbox_events).
- Implemented endpoints listed in `docs/engineering/api-spec.md`.

## Tests and verification
- `.venv/bin/ruff check app tests` → **All checks passed**
- `.venv/bin/pytest` → **34 passed**
- Manual HTTP smoke test (uvicorn): health → login → mission → submit → operator approve → score ۱۰ →
  leaderboard; second approval returns 409; ledger/wallet/outbox verified in SQLite.
- `curl /health` → `{"status":"ok","mode":"P",...}`

## Next recommended tasks
1. **Sales import slice (EP-07):** tables + validate/process + error report + dedupe + golden test, using the documented contract.
2. **Reports (EP-10):** mission/score report per org and per user, CSV export, with org-scope tests.
3. **Correction/reversal flow** for score events (`corrects_event_id` exists, no flow yet).
4. **Auth hardening beyond the prototype:** server-side sessions or OTP behind `app/security.py` (needs OD-01).

## Important files and entry points
- `app/main.py` — routes and access dependencies
- `app/scoring.py` — score event contract
- `app/repo.py` — org-scoped data access + domain errors
- `db/migrations/0001_init.sql` — schema
- `tests/test_flow.py`, `tests/test_scoring.py` — executable behaviour spec
- `.agent/playbooks/prototype-9-days.md` — demo plan and fallbacks

## Demo status
- Runnable from scratch? Yes (`make setup && make run`, or `make seed` to reset).
- Demo data labeled? Yes — persistent DEMO strip plus «نمونه» pills.
- Last successful demo run: 2026-11-09 (manual smoke test + automated flow test).
