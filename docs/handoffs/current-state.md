# Current Project State

- Last updated: 2026-11-12 (۲۱ آبان ۱۴۰۵)
- Updated by: Kiloos engineering agent
- Mode: P
- Current phase: Prototype
- Current milestone: MS-01 — Prototype Delivery (2026-11-18)
- Main branch / working branch: `main` / `arena/a7dc5adb-comu-center`
- Prioritised backlog: `docs/delivery/backlog.md` (PROPOSED)
- Project handover (dated snapshot, Persian): `docs/handoffs/handover.md`
- Agent guide: `docs/agent-guide/README.md`
- Change history: `CHANGELOG.md`

## Working features
- Demo login with 5 seeded users (visitor ×3, operator, admin) and role-aware redirect.
- Cookie-less session fallback: signed token in `?s=` propagated through links/forms/redirects (D-002, demo only).
- CSRF guard on every state-changing route except `/demo-login`, rate-limited demo login, security headers,
  Persian 404/403/422 pages, paginated review queue.
- Mission list/detail filtered by `status=active`, date window, and organization (BR-001).
- Photo submission with client-declared type/size validation, private storage, sha256, `request_id` idempotency.
- Operator review queue with approve/reject; rejection reason required; state machine blocks double review (409).
- **A1 fixed:** review status, audit row and mission score award commit in one transaction. If no rule version is
  effective, the review rolls back to `submitted` and the operator sees a Persian 409. Moving a mission start date
  or publishing a draft ensures an effective same-points rule version when needed; past events are not rewritten.
- Scoring: append-only `score_events`, idempotency key, ledger row, wallet projection, outbox row; explain payload.
- Wallet + score history; period leaderboard with temporary tie-break.
- Admin mission CRUD: create draft → publish → archive; points change publishes a new rule version.
- Sales import (EP-07, D-005): admin-only XLSX upload, file/row validation, explicit idempotent processing,
  fingerprint dedupe, row-level duplicate/error report, reconciliation. Admin can download the SAMPLE workbook
  from `GET /admin/sales/sample` or the link on `/admin/sales/new`.
- **A2 fixed:** score correction is reachable from the admin review screen and the sales import detail page.
  Sales events are org-scoped through the owner user; reversal redirects to the sales import for sales records.
- **A6 fixed (four unambiguous items):** sales navigation is admin-only; submission/review badges show recorded
  event points after a mission points change; the sales list counts pending `valid` rows; processing banner typo fixed.
  The rejected-attempt cap display remains open under B6-1/C6.
- Server-side authorization: visitor / operator / admin + same-organization scope (negative tests exist).
- Documentation tooling: `make docs`, `make docs-check`, `make graph`, `make doctor`.

## In progress
- Sales Quest Arena integration: public frontend reviewed; BFF prototype routes and migration `0004_game_progress.sql`
  are implemented. Contract/source snapshot: `docs/engineering/game-bff-alignment.md` + `app/game_catalog.json`.
  Agreed direction: server-authoritative game progress/rewards, with game XP/coins separate from organizational score events.
  A dev/test-only visitor picker/login/logout API now sets an HttpOnly cookie and bootstrap CSRF header.
  Remaining: the React frontend is not wired to the API; its localStorage seam is synchronous and completion logic remains client-side.
- A4: the demo script has an automated replay (`tests/test_demo_stability.py`) and a live local preview was smoke-tested
  on uvicorn. **Browser rehearsal on the final demo host is still not done.**
- Sales import is XLSX-only with the SAMPLE contract; a real export (OD-03) may add columns or a mapping UI.
- Reports (EP-10) and notifications (EP-11): not started.
- Partial corrections (correcting part of an award) are not implemented.

## Mocked / Demo-only
- **Auth:** demo user picker instead of OTP/SMS (OD-01). Exit: approved login method + provider.
- **Tenant:** one organization; multi-company not exposed (OD-02). Exit: approved org model.
- **Points:** all seeded values (10/15/5/20) are `SAMPLE` (OD-04/05). Exit: approved rule matrix.
- **Wallet:** non-redeemable, display only (OD-08). Exit: approved wallet policy.
- **Dates in admin forms:** Gregorian input, Jalali display. Exit: unified calendar in Harden.
- **Leaderboard:** computed on read with proposed tie-break (BR-009). Exit: approved competition criteria.

## Known issues
- `?s=` puts the session token in the URL (history/logs/referrer); demo-only, exit condition in D-002.
- Rate limiting and session state live in process memory (single-worker only).
- Evidence retention is a manual command; no scheduler, and the 90-day window is a sample default (D-003).
- SQLite single-writer; no connection pooling or WAL tuning yet.
- Mission and leaderboard lists are still unpaginated (queue is paginated).
- The migration runner is a stopgap: files run once at startup in filename order; no checksums, no downgrades.
- The secret-scan step in CI can never fail (backlog A10); `make doctor` is the only working secret check.
- `tests/` uses FastAPI TestClient; Starlette emits a deprecation warning about `httpx` (harmless for now).
- **A3** Dates and times are rendered in raw UTC (3:30 behind Asia/Tehran); admin date inputs are UTC day bounds.
- **A4** The seeded competition ends exactly 7 days after seeding; reseed on demo morning. No browser rehearsal
  on the final demo host has been recorded.
- **A5** Sales points have no "why this score" view; `/score` rows link nowhere.
- **C2** Users ranked below 50 get no rank at all (`LIMIT 50`).
- **C4** Sales detail shows only the first 200 rows with no filter or export; a Jalali `sale_date` is read as Gregorian.
- **C5** Evidence content type is trusted from the client, identical images are not flagged, orphan files can remain.
- **C6** An operator can approve their own submission; rejected attempts consume the per-user cap (B6-1).
- **C8** A correction made after a period ends is subtracted from the current period (BR-008); reversal path uses `float`.
- **C9** Demo login works under any `KILOOS_ENV`; a `?s=` link keeps working after logout.

## Decisions approved
- None yet. D-001…D-005 are all **PROPOSED** (D-005 also carries "Approved by: کارفرما" and needs explicit confirmation).
- This slice changed no business rule: B6-1 rejected-attempt cap, B6-2 approval-time rule selection, B6-3 staff
  self-approval and B6-4 period attribution remain open.

## Open decisions / assumptions
- OD-01…OD-12 remain OPEN (see `docs/decisions/open-decisions.md`).
- Assumptions in force: A-P1 demo auth, A-P2 single tenant, A-P3 photo mission, A-P4 manual review,
  A-P5 sample fixed points, A-P7 temporary tie-break, A-P8 non-redeemable wallet.
- Four business-rule questions surfaced on 2026-11-11 are still **not registered** as open decisions (backlog B4/B6).

## Recent migrations / API changes
- Added `0004_game_progress.sql`: per-user game projection and append-only idempotent game completions, separate from score ledger.
- New route: `GET /admin/sales/sample` (admin-only) downloads the SAMPLE workbook.
- `POST /admin/score-events/{id}/reverse` now redirects sales-record corrections to `/admin/sales/{import_id}?reversed=1`.
- `POST /admin/submissions/{id}/review` renders a Persian 409 and rolls back when scoring has no effective rule version.
- Implemented endpoints listed in `docs/engineering/api-spec.md`, including `/api/v1/game/{bootstrap,progress,history}`,
  profile/draft writes, idempotent game completion, and dev/test-only `/demo-users`, `/demo-login`, `/logout`.
  `/api/v1/game` uses JSON errors/401 and cookie sessions only; URL session tokens are rejected.

## Tests and verification
Run on 2026-11-12 after the A1/A2/A4/A6 slice:
- `.venv/bin/ruff check app tests` → **All checks passed!**
- `.venv/bin/pytest -q` → **81 passed, 1 warning** (Starlette `TestClient`/`httpx` deprecation notice):
  71 prior tests + 10 in `tests/test_game_api.py`.
- `make check` → Ruff clean; **81 passed, 1 warning**. Game API tests cover dev/test demo login/logout, JSON auth/CSRF,
  profile/drafts, canonical answer validation, unlocks, server rewards, daily bonus/replay, idempotency, history,
  user/role scope, and no score-ledger writes.
  `make docs` refreshed the generated documents.
- `make graph` → rebuilt `graphify-out/` (1090 nodes, 3226 edges); `make docs-check` → generated docs current
  (40 routes, 18 tables), knowledge graph up to date.
- `make doctor` → **8 ok · 0 warn · 0 fail**.
- `make seed` and `.venv/bin/python -m app.sample_sales` → fresh demo DB and workbook created.
- Live preview restarted **after A2**, without `--reload`: process `kiloos-club-a39f76b9`, port 8000,
  <https://8000-i5n8yqkt7cn44zmnczefp.e2b.app>. This sandbox URL is not the final demo host.
- HTTP smoke on the restarted preview, using the shared-preview Host header: health → admin demo login →
  sales upload page/sample download (6 data rows) → review/sales/mission pages. Result: **OK**; no demo records changed.
- Sales Quest BFF HTTP smoke on temporary DB, uvicorn port 8002: anonymous bootstrap → JSON 401; visitor demo login →
  bootstrap (6 missions) → server completion (+180 sample XP/+20 coins) → same-key replay. Result: **OK**;
  replay header `Idempotent-Replay: true`.
- Earlier full HTTP smoke (before A2) against a separate uvicorn process on port 8001 with a temporary DB:
  health → visitor login/submit → operator approve (+1 event) → admin sample download/upload/process/reprocess
  → sales list pending count ۰. Result: **OK**. The smoke process was stopped afterwards. The current A2 behavior
  is covered by the three new integration tests and the automated demo replay above.
- Automated demo replay: `tests/test_demo_stability.py::test_demo_script_main_path_and_optional_correction` and
  `test_demo_optional_new_rule_version_awards_fifteen_at_approval` pass with the documented numbers.
- Not verified: a real browser rehearsal on the final demo host; Mermaid rendering; `graphify-out/graph.html` in a browser.

## Next recommended tasks
Full list with evidence: `docs/delivery/backlog.md`.
1. **A4 final step:** run the demo script in a browser on the actual demo host and record it in `demo-script.md` §9.
2. **A3:** Asia/Tehran display and admin day bounds (`app/jalali.py`, `app/repo.py::_parse_day`).
3. **A5:** score-event detail/explain links from history and sales points.
4. **A7 + A10:** dependency constraints and a CI secret scan that can actually fail.
5. **B decisions:** collect client answers at MS-01/MS-02; register B6 questions before changing cap/self-approval/period rules.
6. **C/D:** only after the relevant decisions; do not start Harden without recorded P→H.

## Important files and entry points
- `app/main.py` — routes and access dependencies
- `app/scoring.py` — score event contract; mission award is caller-transactional
- `app/repo.py` — org-scoped data access, atomic review, rule effective-date guard, sales correction context
- `app/sales.py` — sales workbook parsing and row validation
- `app/sample_sales.py` — CLI and in-memory SAMPLE workbook
- `tests/test_demo_stability.py` — A1/A2/A4/A6 regressions and demo replay
- `docs/agent-guide/code-map.md` / `traceability.md` — generated; run `make docs`
- `.agent/context/traceability.json` — curated links behind the matrix
- `docs/delivery/backlog.md` — prioritised backlog
- `docs/delivery/demo-script.md` — demo accounts, numbers, rehearsal table

## Demo status
- Runnable from scratch? Yes (`make setup && make run`, or `make seed` to reset).
- Demo data labeled? Yes — persistent DEMO strip plus «نمونه» pills.
- Last successful demo run: 2026-11-12 (automated replay + uvicorn HTTP smoke). No final-host browser rehearsal yet.
- Demo-day caveat: reseed on the morning of the demo, otherwise the sample competition period may have ended (A4).
- Demo script, accounts, expected numbers, things not to do on stage: `docs/delivery/demo-script.md`.
