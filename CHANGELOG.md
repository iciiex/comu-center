# Changelog

What changed in this repository, newest first. Read it to learn why the code looks the way it
does; read [`docs/handoffs/current-state.md`](docs/handoffs/current-state.md) to learn what is
true now.

- The project has no tags and no releases. `pyproject.toml` has said `0.1.0` since the first
  Kiloos Club commit, so entries are grouped by merged pull request, not by version.
- Every entry names the decisions (`D-xxx`), migrations and test count it introduced.
  Decision statuses are in [`docs/decisions/decision-log.md`](docs/decisions/decision-log.md);
  on 2026-11-11 none was `APPROVED`.
- Times are UTC. Mode of the whole history: `P` (Prototype).

How to add an entry: write your lines under `[Unreleased]` while you work; when the pull request
exists, move them under a dated heading with its number
([`docs/agent-guide/03-deliver.md`](docs/agent-guide/03-deliver.md) §3 and §4).

## [Unreleased]

Nothing yet.

## 2026-11-11 — Documentation, agent guide and knowledge graph — [PR #8](https://github.com/iciiex/comu-center/pull/8)

Tests: 58 (two documentation tests added). No decision, no migration. No application code,
schema or behaviour changed.

Added

- `docs/delivery/backlog.md` (`PROPOSED`): evidence-based backlog with rows A1–A10 (before
  MS-01), B1–B6 (client decisions), C1–C13 (MVP completion) and D1–D6 (Harden). About twenty
  defects were reproduced by running the code; each row cites the file and the cause.
- `docs/agent-guide/`: `README.md` (index and "where is X" table), `01-start.md`,
  `02-continue.md`, `03-deliver.md`, `knowledge-graph.md`, `troubleshooting.md`.
- `docs/agent-guide/code-map.md` and `docs/agent-guide/traceability.md`: generated from the
  code, the tests and the documents; never edited by hand.
- `.agent/tools/knowledge_map.py`: the generator. Reads the code with `ast` and never imports
  the application. `--check` fails when the generated files are stale or a curated link names a
  missing symbol; `--graph` builds the knowledge graph.
- `.agent/context/traceability.json`: curated links from MVP-01…13, BR-001…014 and EP-01…13 to
  code symbols, tests and backlog rows, with an engineering judgement of each state.
- `graphify-out/`: knowledge graph of code, schema, templates, tests and documents
  (`graph.json`, `graph.html`, `GRAPH_REPORT.md`, `BUILD_INFO.json`). Built with graphify
  0.9.106 plus a project layer, without a language model.
- `tests/test_docs.py`: the generated documents are fresh; the code map lists exactly the routes
  the application serves.
- `Makefile` targets `docs`, `docs-check`, `graph`, `doctor`.
- `docs/delivery/demo-script.md` (`PROPOSED`): the MS-01 demo walk with the numbers each step
  shows, checked by an automated run on a fresh seed.
- `docs/handoffs/handover.md`: project handover.
- `CHANGELOG.md`: this file.

Changed

- `AGENTS.md`: one repository note in the header (kit paths live under `.agent/`, pointer to the
  agent guide). No rule changed.
- `docs/README.md`, `docs/handoffs/current-state.md`, `README.md`: new documents indexed, state
  refreshed.
- `.gitignore`: graph cache and working files.
- Stale statements corrected to match the code in `README.md`, `db/migrations/README.md`,
  `docs/product/prd.md`, `docs/product/admin-panel-spec.md`, `docs/architecture/*.md`,
  `docs/engineering/*.md`, `docs/delivery/execution-plan.md`, `docs/quality/qa-test-strategy.md`,
  `.agent/CONTEXT.md` and `.agent/MASTER_PROMPT.fa.md` (list: `docs/delivery/backlog.md` § A8).
- `docs/operations/runbook.md`: section on repository health and generated documents.

Found, not fixed

- The secret-scan step in `.github/workflows/ci.yml` cannot fail (backlog A10).
- Open defects before the demo: backlog A1, A2, A3, A5, A6, A7.

## 2026-11-09 — Sales import — [PR #7](https://github.com/iciiex/comu-center/pull/7)

Merged 15:55 as `60cad25`. Tests: 56. Decision: D-005. Epic: EP-07.

Added

- Admin-only XLSX upload at `/admin/sales/new`, with two-level validation (file, then row) and
  a per-row report: `app/sales.py`, three templates, five routes.
- Explicit processing step: upload never scores; `POST /admin/sales/{id}/process` creates one
  score event per valid row and can be repeated without creating duplicates.
- Deduplication inside the organization by file hash and by row fingerprint; reconciliation of
  row counts and points on the import page.
- `SAMPLE` rule `SALES_AMOUNT_SAMPLE` (`per_unit_amount`: one point per 1,000,000 units of
  amount) and a seeded visitor mapping `VIS-001…003`.
- `python -m app.sample_sales` writes a sample workbook.
- Migration `0003_sales_import.sql`: `sales_imports`, `sales_records`, `sales_user_map`,
  `scoring_rule_versions.unit_size`.
- Dependency `openpyxl`.

Changed

- `app/db.py`: the migration runner records applied files in `schema_migrations` and wraps each
  file in a transaction.
- `app/scoring.py`: the award path is shared by missions and sales.

## 2026-11-09 — Score corrections — [PR #6](https://github.com/iciiex/comu-center/pull/6)

Merged 15:30 as `9305edd`. Tests: 43. Decision: D-004.

Added

- A correction is a new negative score event that points at the original
  (`corrects_event_id`); nothing is updated or deleted. Event, ledger row, wallet, outbox row
  and audit row are written in one transaction.
- `POST /admin/score-events/{id}/reverse`: admin only, reason required, limited to the
  organization. Guards: `REASON_REQUIRED`, `ALREADY_REVERSED`, `CANNOT_REVERSE_CORRECTION`.
- Migration `0002_score_corrections.sql`: partial unique index, so one event can be corrected
  once even outside the UI.
- `app.db.apply_migrations`: runs every `db/migrations/*.sql` in filename order.
- The submission page shows the correction form to an admin; `/score` marks corrections.

## 2026-11-09 — Demo hardening — [PR #5](https://github.com/iciiex/comu-center/pull/5)

Merged 15:18 as `1df545f`. Tests: 34. Decisions: D-002, D-003.

Added

- Session transport without cookies: the signed token is also accepted as `?s=` and carried
  through links, forms and redirects, because the embedded preview blocks third-party cookies
  (D-002, demo only).
- CSRF check on every POST except `/demo-login`; the value is derived from the session token.
- Rate limit on demo login (default 10 per 60 seconds per client address) → 429.
- Security headers: `nosniff`, `no-referrer`, a content security policy. `X-Frame-Options` is
  left out on purpose so the preview can embed the app.
- Pagination of the review queue; Persian 404 page.
- `python -m app.maintenance purge-evidence [--dry-run] [--days N]` with an audit row (D-003,
  retention period is `SAMPLE`).

## 2026-11-09 — Kiloos Club prototype — [PR #4](https://github.com/iciiex/comu-center/pull/4)

Merged 15:03 as `eba1ee0`. Tests: 19. Decision: D-001. ADR-0001.

Added

- The agent kit: `AGENTS.md`, `.agent/` (product context with ids, seven roles, five playbooks,
  templates, `bootstrap.py`, `doctor.py`).
- A runnable prototype on FastAPI, Jinja (right-to-left) and SQLite: demo login, missions
  filtered by status, date window and organization (BR-001), photo submission with
  `request_id` idempotency, operator review with a required rejection reason.
- Scoring: append-only `score_events` with an idempotency key and a unique index; ledger,
  wallet projection and outbox row in one transaction; `explain_json` shown as
  «چرا این امتیاز؟».
- Wallet and history, period leaderboard, admin mission management with rule versioning.
- Documentation skeleton, decision registers (OD-01…12), CI workflow.

Removed

- The previous `comu-center` code (see below). It stays recoverable at `fd2fc90`.

## Before Kiloos Club

This repository first held a different project, `comu-center` (pull requests #1 and #2, merged
2026-10-22 as `a926e47` and `fd2fc90`). PR #4 replaced it. PR #3 («feat: direct Instagram +
free-tier AI product path (ADR-0010)») belongs to that project and was still open on 2026-11-11;
it does not apply to the current tree.
