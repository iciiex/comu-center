# Kiloos Club — 3-hour demo sprint

Repository: https://github.com/iciiex/comu-center
Base: main
Working branch: demo/2026-11-18-three-hour-sprint
Timebox: 180 minutes
Mode: P (prototype)

## Mission

Deliver a polished, functional, publicly reachable demo today. Do not rewrite the platform. Reuse the existing FastAPI application, XLSX import, scoring engine, game APIs and React game. Target architecture: FastAPI on Render + Neon PostgreSQL as the authoritative hosted database. Preserve SQLite for local development/tests if practical. Inspect the current source before making assumptions.

## Read first

- AGENTS.md
- .agent/CONTEXT.md
- docs/handoffs/current-state.md
- docs/decisions/open-decisions.md
- docs/delivery/backlog.md
- docs/engineering/sales-import.md
- docs/engineering/game-bff-alignment.md
- docs/delivery/demo-script.md
- app/main.py, app/db.py, app/config.py, app/repo.py, app/sales.py, app/scoring.py, app/game.py
- app/game_catalog.json and app/game_store_catalog.json
- tests/, app/templates/, app/static/

The Sales Quest Arena frontend is confirmed in the separate public repository https://github.com/mrkavousi/sales-quest-arena (default branch main). Its README and docs/bff-integration.md already document the BFF integration; npm run test:bff runs a cross-repository integration test. You have confirmed read/write access to this repository. Clone it into a sibling folder and work on a dedicated feature branch; do not copy the app into the backend repo or build a competing Jinja game UI. Keep the separate React/Vite frontend as the actual player-facing game.

## Non-negotiable correctness

1. Keep MODE P. Never claim production readiness.
2. Organizational points and game XP/coins are separate accounting domains. Never mix them.
3. Existing scoring engine and import contract are the source of truth.
4. Never fabricate business rules, point values, user data, successful tests or deploys.
5. Never award points by editing balances directly. Use the existing append-only scoring/ledger flow.
6. Preserve organization scoping, role checks, CSRF, audit logging and idempotency.
7. Uploading an XLSX must not score it. Processing must require explicit admin confirmation.
8. Reprocessing or duplicate external sales must never award twice.
9. Do not reset or destructively migrate an existing database.
10. Do not commit secrets, real user data or uploaded evidence.

## Timeboxed delivery

### 0–20 min: discovery and baseline
Inspect the current source and tests. Run existing checks. Identify exact admin routes, import lifecycle, scoring rule, game endpoints and frontend location. Write a concise implementation plan, then proceed without waiting for routine approval.

### 20–65 min: admin demo experience
Build or complete a Persian RTL admin experience using existing FastAPI routes/templates:
- Dashboard with real DB-derived users, sales, organizational points, pending reviews, top visitors and recent imports.
- User list/detail with search by name/personnel external ID, wallet balance, sales and score history.
- XLSX import center: sample download, upload, row preview, validation counts, row errors, matched users, expected points, explicit process confirmation, result/reconciliation and import detail.
- Points audit: user, amount, source, timestamp, rule/version, explanation and correction history.
- Navigation for dashboard, users, imports, mission review, score history, game/competition, leaderboard and activity.

Keep the UI focused on the demo. Label sample-derived values clearly. Never show hardcoded KPIs as real metrics.

### 65–115 min: game integration
Work across BOTH repositories: backend iciiex/comu-center and frontend mrkavousi/sales-quest-arena. Read backend docs/engineering/game-bff-alignment.md AND frontend docs/bff-integration.md. The frontend already contains a server API client and integration proposal; validate and complete that existing integration rather than reimplementing it. Use the frontend's existing API client and same-origin relative paths. Replace localStorage as authoritative game state with backend API state:
- Existing demo visitor login/session and CSRF.
- Bootstrap profile, missions, config and persisted progress.
- Show XP, coins, level, mission list, completion and leaderboard from backend.
- Submit answers and completion to server; use idempotency key.
- Reload restores canonical server state.
- Use same-origin API paths and credentials: include.
- Never trust client-submitted XP/coins/rewards/level.
- Never write game XP/coins to organizational score ledger.
- Preserve the existing mission catalog and content_version.
- Include loading, empty, retry and error states.

Use the existing React repository at https://github.com/mrkavousi/sales-quest-arena. Build and test the frontend from that repository on a separate feature branch. Ensure the deployment plan configures a same-origin reverse proxy for `/api/v1/game/*` to the FastAPI service and preserves HttpOnly Set-Cookie, CSRF headers and idempotency headers. A static Vercel deployment alone does not provide this proxy; document the exact production routing configuration. Do not fall back to a duplicate Jinja game UI.



### 115–145 min: QA
Run:
```bash
make check
make doctor
make docs-check
```
Add focused tests for dashboard real data, organization scope, XLSX allocation, duplicate/reprocess idempotency, ledger reconciliation, game reward separation, reload persistence and authorization.

The documented sample workbook contract is:
- 6 rows total
- 4 valid
- 1 duplicate
- 1 unmapped user
- process awards 15 organizational points (4 + 2 + 8 + 1) across three mapped visitors
- reprocessing awards 0 additional points

This is the SAMPLE rule, not an approved business policy. Keep it labeled as sample.

### 145–170 min: Neon PostgreSQL + Render deployment
The hosted demo MUST use Neon PostgreSQL as its authoritative application database. Do not deploy hosted demo data to SQLite. Keep SQLite as the local dev/test adapter if feasible; do not break existing local workflows.

#### Database migration requirements
The current codebase is SQLite-specific (sqlite3 connections, qmark placeholders, sqlite.Row assumptions and SQLite schema initialization). This is a real compatibility migration, not just changing an environment variable.
- Inspect app/db.py, schema, all SQL call sites, tests and transaction boundaries first.
- Implement the smallest safe dual-backend design: DATABASE_URL selects PostgreSQL in hosted demo; absent DATABASE_URL uses existing SQLite locally.
- Prefer psycopg 3 with dict_row (or a small, tested compatibility adapter) and add the dependency to pyproject.toml. Keep SQL parameterization; never interpolate user input.
- Handle placeholder differences, row access, transaction/commit semantics, integrity errors, generated IDs, schema DDL, indexes and constraints explicitly. Do not use brittle global SQL string replacement without tests.
- Add an idempotent PostgreSQL schema initialization/migration path. It must be safe on repeated deploys and must not drop, truncate, or reset existing data.
- Keep domain logic backend-neutral where practical. If a full PostgreSQL port cannot be completed safely in this timebox, report exactly what remains and do not ship a broken deployment.
- Add tests for PostgreSQL adapter behavior and run integration smoke tests against a real Neon branch if credentials are available. Do not fabricate integration results.
- Never print DATABASE_URL or credentials in logs, test output, issue comments or docs.

#### Neon setup
Use an existing Neon project/branch only if it is clearly the intended project for this app. Otherwise report that a Neon project/branch and connection string must be supplied; do not create or modify an unrelated project.
- Render environment variable DATABASE_URL = Neon pooled connection string (use the pooled hostname / -pooler endpoint for the app runtime).
- Use a separate direct Neon connection string for schema migration only if the migration tooling requires it; do not expose it to the browser.
- Require SSL (sslmode=require) and verify the actual connection settings.
- Do not commit secrets, .env files or connection strings.
- Set KILOOS_ENV=demo and KILOOS_SECRET as a generated secret.
- Set KILOOS_EVIDENCE_DIR under durable storage.
- Configure appropriate CORS/session trusted origins if frontend is cross-origin and set the health check path based on the actual route.

#### Evidence file storage
Neon PostgreSQL stores relational data, not uploaded evidence files. Existing private evidence uploads must remain durable and private:
- For this demo, use a Render persistent disk mounted at /var/data for KILOOS_EVIDENCE_DIR, OR use a verified private object-storage integration already configured in the repo.
- Do not remove evidence requirements or expose private evidence as public static assets.
- If a Render persistent disk is required for evidence, note that it may require a paid Render service. The database itself must not depend on that disk.

Inspect the actual app factory and settings before choosing commands. Existing known start command candidate:
`uvicorn app.main:create_app --factory --host 0.0.0.0 --port $PORT`
Only use this if it matches the actual app structure.

Render service must deploy from branch demo/2026-11-18-three-hour-sprint initially. Do not auto-deploy main or merge without verification. Use Render GitHub integration. If integration, billing, permissions, Neon credentials or required permissions are missing, stop and report the exact manual step; never claim it is deployed.
If a render.yaml is appropriate, create it with non-secret environment configuration and generateValue for secrets where supported. DATABASE_URL must be configured as a secret in Render dashboard, never hardcoded in YAML or repository.

### 170–180 min: handoff
Update docs/handoffs/current-state.md, docs/delivery/demo-script.md and CHANGELOG.md. Report:
- implemented features and exact files
- tests actually run and results
- branch and commit SHA
- Render service and public HTTPS URL, only if confirmed
- demo accounts/login instructions (never invent credentials)
- sample workbook flow and expected reconciliation
- known limitations and blocked steps

## Definition of done

- Admin dashboard operational and DB-backed.
- XLSX import awards correct organizational points with reconciliation.
- Duplicate sales and reprocessing cannot double-award.
- User score history traceable.
- Game frontend uses backend-authoritative state and survives refresh.
- Game XP/coins remain separate from organizational points.
- Tests pass.
- Render URL responds over HTTPS and smoke tests pass.

## Priority if time runs short

1. Public app runs reliably with persistent data.
2. Excel import and point allocation.
3. Admin dashboard and user/score visibility.
4. Game integration.
5. Reports and visual polish.

Start immediately. Keep all work on the specified demo branch.