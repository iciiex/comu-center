# Troubleshooting

Symptoms an agent meets in this repository, the cause, and the fix. Every entry was either
reproduced or read from the code on the review date. Operational issues of a running demo
are in [`docs/operations/runbook.md`](../operations/runbook.md) § Common issues.

- Mode: P (Prototype) · Last reviewed: 2026-11-11
- Index: [README.md](README.md)

## 1. Setup and tooling

| Symptom | Cause | Fix |
|---|---|---|
| `.venv/bin/pytest: No such file or directory` | The virtualenv is not committed; a fresh checkout or sandbox has none | `make setup` |
| `make graph` fails on `pip install` | First use downloads `graphifyy[sql]` from PyPI | Needs network access to `pypi.org` and `files.pythonhosted.org`; the committed graph still answers queries with any existing install |
| `pip install graphify` finds nothing | The distribution is named `graphifyy` | Use `make graph`, which pins the right package |
| `graphify extract .` stops with "no LLM API key found" | Semantic extraction of documents needs a language model | Do not use it here; `make graph` builds without one ([knowledge-graph.md](knowledge-graph.md) §7) |
| `graph.html` opens as an empty page | It loads `vis-network` from `unpkg.com` | Open it in a browser with internet access, or read `GRAPH_REPORT.md` |
| `grep -r` prints "binary file matches" | It reads `__pycache__/*.pyc` | `git grep -n PATTERN` or `grep -rn --include='*.py'` |
| `pkill -f "uvicorn …"` returns an error and the server keeps running | The pattern matches the shell that runs `pkill` | `pkill -f "[u]vicorn app.main:create_app"` |
| `make run` says the address is in use | An earlier server still holds port 8000 | Stop it with the command above |
| A path named in `AGENTS.md` or a role file does not exist (`CONTEXT.md`, `roles/…`, `templates/…`) | The agent kit names paths relative to its own root, which here is `.agent/` | Prefix `.agent/`; full table in [01-start.md](01-start.md) §1 |
| `doctor` prints `run: python3 tools/bootstrap.py --target <repo>` | A required kit file is missing; the hint is written for the original kit folder | Restore the file from git (`git checkout -- <path>`). `.agent/tools/bootstrap.py` cannot run here: it exits 2 with "kit root not found" |
| Variables in `.env` have no effect | The app reads the process environment only; nothing loads `.env` | `KILOOS_ENV=dev KILOOS_SECRET=… make run`, or `export` them |

## 2. Checks that fail

| Symptom | Cause | Fix |
|---|---|---|
| `tests/test_docs.py::test_generated_agent_docs_are_fresh` fails with a diff | Code, tests, templates or documents changed and the generated maps were not regenerated | `make docs`, commit the two files |
| `error: … points to missing symbol app/…::name` | A function or test named in `.agent/context/traceability.json` was renamed or removed | Update that entry, then `make docs` |
| `error: … points to unknown backlog row X9` | The curated links name a backlog id that is not in `docs/delivery/backlog.md` | Add the row or fix the id |
| `test_code_map_lists_exactly_the_routes_the_app_serves` fails | A route is declared in a way the generator does not recognise | Declare it as `@app.get(...)` or `@app.post(...)` inside `create_app`, like the others |
| `ruff` reports `E501` | Line longer than 100 characters | Wrap it; do not add `noqa` |
| `ruff` reports an `S` rule in `app/` | Security lint (bandit rules) is enabled for application code | Fix the cause; SQL takes parameters, never string formatting of values |
| `doctor`: current-state is stale | `Last updated:` is missing, malformed or older than 21 days | Update `docs/handoffs/current-state.md` ([03-deliver.md](03-deliver.md) §3) |
| `doctor`: decision block has an invalid status | An `OD` or `D` block uses a status outside the allowed list | Use `OPEN`, `PROPOSED`, `APPROVED`, … as in `AGENTS.md` §3 |
| `doctor`: secret pattern found | A text file contains a private-key header or a token-shaped string | Remove it; if it is a real secret, it must also be revoked |
| CI is green although a secret was committed | The CI scan step cannot fail (backlog A10) | Run `make doctor` locally until A10 is fixed |

## 3. Writing tests

| Symptom | Cause | Fix |
|---|---|---|
| POST returns 403 «اعتبار فرم منقضی شده است» | The request has no valid `csrf` field | Use `post(client, settings, path, …)` from `tests/conftest.py` |
| POST returns 303 to `/login` | No session | Call `login(client, settings, ADMIN)` first |
| `login()` fails with status 429 | More than 10 logins within 60 seconds on one app instance (rate limit per client address) | Use fewer logins per test, or build `Settings(…, login_rate_limit=1000)` for that test |
| A page returns 404 for a mission that exists | `repo.get_mission_for_user` hides missions that are not `active`, outside their date window or in another organization | Use a seeded active mission, or publish one in the test |
| Second submission returns 409 | The per-user cap (`max_per_user`) is reached; rejected attempts count too (backlog B6-1) | Use the other seeded mission or another visitor |
| `sqlite3.OperationalError: database is locked` | SQLite allows one writer; a second writer waits 5 seconds (`app/db.py::connect`) and then fails | Commit or close the connection that holds the write; in a test, do not leave an uncommitted write on the `db` fixture while the client makes a request |
| One warning: Starlette `TestClient` deprecation | Upstream notice about `httpx` | Harmless; do not silence it globally |

## 4. Changing application code

| Symptom | Cause | Fix |
|---|---|---|
| A rollback did not undo an earlier statement | `with conn:` blocks do not nest: leaving the inner block commits everything done so far | One `with conn:` per unit of work; helpers that join a caller's transaction must not open their own ([02-continue.md](02-continue.md) §2.3) |
| Approving a submission returns 500 and the submission stays `approved` with no points | No rule version is in force for the mission (for example a mission created with a future start) and approval is not atomic | Known defect, backlog A1; do not paper over it in the template |
| The user is signed out after clicking a new link inside the preview | The link was written as a bare path, so the `?s=` session was dropped | Wrap every link and form action in `url(...)`; redirect with `go(...)` |
| A new page shows the signed-out header | `page(...)` was called without `user=user` | Pass the user |
| Reversing a sales score event returns 403 | `repo.score_event_detail` reads the organization through `submissions`, which a sales event does not have | Known defect, backlog A2 |
| Times on screen are 3:30 behind | Stored UTC is rendered without conversion to Asia/Tehran | Known defect, backlog A3; store UTC, convert only for display |
| Leaderboard title changed to «رتبه‌بندی» and totals look different | The seeded competition period ended (it runs from 7 days before to 7 days after seeding) | `make seed`; a period management screen is backlog C2 |
| The app refuses to start: `KILOOS_SECRET must be set outside dev/test` | `KILOOS_ENV` is neither `dev` nor `test` and no secret is set | Set `KILOOS_SECRET` to at least 32 random characters |
| Every session is invalid after a restart | `KILOOS_SECRET` changed | Keep it stable; sign in again |
| A new migration did not run | The file name does not sort after the applied ones, or the name is already in `schema_migrations` | Use the next `NNNN_` number; never rename an applied file |
| A migration fails with "cannot start a transaction within a transaction" | The file contains its own `BEGIN` or `COMMIT` | Remove them; the runner wraps the file |

## 5. Sales import

| Symptom | Cause | Fix |
|---|---|---|
| Upload returns 409 «این فایل قبلاً آپلود شده است» | The same bytes were imported before (`file_sha256`) | Open the existing import |
| Every row is `E_USER_MAPPING` | `sales_user_map` has no entry for those external ids | Mapping is explicit and seeded only; management screen is backlog C1 |
| Processing reports 0 new events | Nothing valid is left, or every amount is below one unit | Expected on a second run; check the row report |
| A Jalali date such as `1405/08/10` is accepted as valid | The date column is read as Gregorian (year 1405) | Known defect, backlog C4; the real file contract is OD-03 |
| No sample file to upload | It is generated, not committed | `.venv/bin/python -m app.sample_sales` writes `var/sales-sample.xlsx` |

## 6. When the documents disagree with the code

The code and executed tests win (`AGENTS.md` §2). Record the conflict in your handoff and
fix the document in the same change. Conflicts already found are listed in
`docs/delivery/backlog.md` § A8; check there before you report one again.
