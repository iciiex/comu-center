# Current Project State

- Last updated: 2026-11-11 (۲۰ آبان ۱۴۰۵)
- Updated by: Kiloos engineering agent
- Mode: P
- Current phase: Prototype
- Current milestone: MS-01 — Prototype Delivery (2026-11-18)
- Main branch / working branch: `main` / `arena/26ce8c46-comu-center`
- Prioritised backlog: `docs/delivery/backlog.md` (PROPOSED)
- Project handover (dated snapshot, Persian): `docs/handoffs/handover.md`
- Agent guide (start, continue, deliver, code map, traceability, knowledge graph): `docs/agent-guide/README.md`
- Change history: `CHANGELOG.md`

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
- Sales import (EP-07, D-005): admin uploads XLSX → file/row validation (never scores) → explicit,
  idempotent processing that awards `floor(amount / unit_size) * points`; explicit
  `sales_user_map`, fingerprint-level file dedupe, row-level duplicate/error report and reconciliation.
- Score corrections (D-004): admin reverses an event with a negative event (`corrects_event_id`, reason required);
  ledger, wallet, outbox and audit are written in one transaction; double correction is impossible
  (`ux_score_events_corrects`); `/score` marks corrections and the leaderboard sums them automatically.
- Server-side authorization: visitor / operator / admin + same-organization scope (negative tests exist).
- Documentation tooling (no effect on the running app): `make docs` regenerates
  `docs/agent-guide/code-map.md` and `traceability.md` from code, tests and documents;
  `tests/test_docs.py` fails when they are stale; `make graph` rebuilds the knowledge graph in
  `graphify-out/`; `make doctor` runs the repository health check.

## In progress
- Sales import is XLSX-only with the SAMPLE contract; a real export (OD-03) may add columns or a mapping UI.
- Reports (EP-10) and notifications (EP-11): not started.
- Partial corrections (correcting part of an award) are not implemented.

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
- The migration runner is a stopgap (`app/db.py::apply_migrations`): files run once at startup in filename
  order; no checksums, no downgrades.
- The secret-scan step in CI can never fail (backlog A10); `make doctor` is the only working secret check.
- `tests/` uses FastAPI TestClient; Starlette emits a deprecation warning about `httpx` (harmless for now).

Found on 2026-11-11 by running the code (reproduction and proposed fix per item in
`docs/delivery/backlog.md`; none of these is fixed yet):
- **A1** Approval can end as `approved` with no score event (HTTP 500, retry → 409) when no rule version is
  effective, e.g. a mission created with a future start whose start date is later moved back.
- **A2** Score corrections have no entry point in the admin panel (the form lives on `/submissions/{id}` only),
  and reversing a `sales_record` event returns 403, so sales points cannot be corrected.
- **A3** Dates and times are rendered in raw UTC (3:30 behind Asia/Tehran); admin date inputs are UTC day bounds.
- **A4** The seeded competition ends exactly 7 days after seeding; the leaderboard then silently falls back to
  all-time totals. `docs/delivery/demo-script.md` now exists and its numbers were checked by an automated run,
  but no browser rehearsal on the demo host has been done.
- **A5** Sales points have no "why this score" view; `/score` rows link nowhere.
- **C2** Users ranked below 50 get no rank at all (`LIMIT 50`).
- **C4** Sales detail shows only the first 200 rows with no filter or export; a Jalali `sale_date` such as
  `1405/08/10` is accepted as a Gregorian year, while `1405/02/31` is rejected.
- **C5** Evidence content type is trusted from the client, identical images are not flagged, and replayed or
  over-cap submissions leave orphan files that `purge-evidence` never removes.
- **C6** An operator can approve their own submission.
- **C8** A correction made after a period ends is subtracted from the current period (BR-008).
- **C9** Demo login works under any `KILOOS_ENV`; a `?s=` link keeps working after logout.

## Decisions approved
- None yet. D-001…D-005 are all **PROPOSED** (D-005 also carries "Approved by: کارفرما" and needs an explicit
  confirmation before its status changes).

## Open decisions / assumptions
- OD-01…OD-12 remain OPEN (see `docs/decisions/open-decisions.md`).
- Assumptions in force: A-P1 demo auth, A-P2 single tenant, A-P3 photo mission, A-P4 manual review,
  A-P5 sample fixed points, A-P7 temporary tie-break, A-P8 non-redeemable wallet.
- Four business-rule questions surfaced on 2026-11-11 and are **not yet registered** as open decisions:
  rejected attempts consuming the per-user cap, rule version chosen at approval time, staff self-approval,
  and period attribution of corrections and sales points (backlog B4 and B6).

## Recent migrations / API changes
- `db/migrations/0001_init.sql`: initial schema (organizations, users, missions, scoring_rule_versions,
  submissions, submission_evidences, score_events, point_transactions, point_wallets, competitions,
  audit_logs, outbox_events).
- `db/migrations/0002_score_corrections.sql`: `ux_score_events_corrects` — one correction per event.
- `db/migrations/0003_sales_import.sql`: `sales_imports`, `sales_records`, `sales_user_map` and
  `scoring_rule_versions.unit_size`; `ux_sales_records_external` is partial (valid/scored only).
- `app.db.apply_migrations` runs each file once, tracked in `schema_migrations (name, applied_at)`.
- Implemented endpoints listed in `docs/engineering/api-spec.md`.

## Tests and verification
Run on 2026-11-11 (virtualenv from `pip install -e ".[dev]"`; fastapi 0.162.4, starlette 1.10.0), after the
last documentation edit of the session:
- `make check` → ruff **All checks passed!** · pytest **58 passed, 1 warning** (about 6 seconds; the warning is
  Starlette's `TestClient` deprecation notice). 58 = the 56 application tests + 2 in `tests/test_docs.py`.
- `make doctor` (`python3 .agent/tools/doctor.py --root . --strict`) → **8 ok · 0 warn · 0 fail**
- `make docs-check` → generated documents current (29 routes, 16 tables); knowledge graph up to date
- `make graph` → graph rebuilt with graphify 0.9.106; counts in `graphify-out/BUILD_INFO.json`
- Demo walk (`docs/delivery/demo-script.md` §۳ and §۴) replayed with `TestClient` on a fresh seed: every
  number in the script was observed. Not done: a browser rehearsal on the demo host.
- HTTP smoke test against a real uvicorn process with a temporary database: health → visitor login → submit →
  operator approve → +۱۰ with explanation → balance ۱۰ → rank ۲ → admin changes points 10→15 (new rule
  version) → sample sales upload and processing (4 events, 15 points) → wallet equals ledger.
- The defects listed under "Known issues" were reproduced with throwaway `TestClient` scripts on temporary
  databases. Those scripts are not in the repository; each fix must add its own regression test.
- No application code changed in this session. Added: documentation, the generator
  `.agent/tools/knowledge_map.py`, `tests/test_docs.py`, Makefile targets.
- Not verified: Mermaid rendering in `docs/agent-guide/01-start.md`, and `graphify-out/graph.html` in a
  browser (it needs internet access for one script).

## Next recommended tasks
Full list with evidence, IDs and size estimates: `docs/delivery/backlog.md` (PROPOSED order).
1. **Before MS-01 (group A):** start with A1 in `app/repo.py:review_submission`, then A2 (correction entry point
   and sales events), A3 (Asia/Tehran display), A4 (the script exists; reseed on demo morning and do one
   browser rehearsal on the demo host), then A5–A7, A9 and A10. A8 (documents aligned with code) is done
   except two items that need the owner (D-005 status, the ownership table in `AGENTS.md` §5).
2. **At MS-01 / MS-02 (group B):** collect the decisions that unblock the MVP — route approval and P→H,
   D-001…D-005, production stack, OD-01…OD-08 and OD-10, plus the four questions in B6.
3. **MVP completion (group C):** user management and sales-ID mapping (C1), competition periods (C2),
   reports + CSV (C3, EP-10), sales error report and date validation (C4), evidence controls (C5); the earlier
   candidates map to C8 (correction hardening), C9 (auth, needs OD-01) and C10 (real sales contract,
   needs OD-03/04/05).
4. **Harden (group D):** only after P→H is recorded in `docs/decisions/decision-log.md`.

## Important files and entry points
- `app/main.py` — routes and access dependencies
- `app/scoring.py` — score event contract
- `app/repo.py` — org-scoped data access + domain errors
- `app/sales.py` — sales workbook parsing and row validation
- `db/migrations/*.sql` — schema (three files, applied in order)
- `tests/test_flow.py`, `tests/test_scoring.py`, `tests/test_sales.py`, `tests/test_corrections.py`,
  `tests/test_hardening.py` — executable behaviour spec
- `docs/agent-guide/code-map.md` — every route, function, table and test, generated from the code
- `docs/agent-guide/traceability.md` — requirement ↔ code ↔ test ↔ backlog row
- `.agent/context/traceability.json` — the curated links behind that matrix; update it when a requirement's
  code or state changes
- `.agent/playbooks/prototype-9-days.md` — demo plan and fallbacks
- `docs/delivery/backlog.md` — prioritised backlog with evidence (start here for the next task)

## Demo status
- Runnable from scratch? Yes (`make setup && make run`, or `make seed` to reset).
- Demo data labeled? Yes — persistent DEMO strip plus «نمونه» pills.
- Last successful demo run: 2026-11-11 (automated flow tests, HTTP smoke test of the main path on uvicorn, and
  an automated replay of `docs/delivery/demo-script.md`). No browser rehearsal yet.
- Demo-day caveat: reseed on the morning of the demo, otherwise the sample competition period may have ended (A4).
- Demo script, accounts, expected numbers, things not to do on stage: `docs/delivery/demo-script.md`.
