# 02 — Continue

Patterns this code already follows, and step-by-step recipes for the changes you are most
likely to make. Copy the pattern; do not invent a second one (`AGENTS.md` §4, Build).

- Mode: P (Prototype) · Last reviewed: 2026-11-11
- Before: [01-start.md](01-start.md) · After: [03-deliver.md](03-deliver.md) · Index: [README.md](README.md)

## 1. The loop, with this repository's commands

| Step (`AGENTS.md` §4) | Do this here |
|---|---|
| Read | `docs/handoffs/current-state.md`, then the backlog row |
| Locate | Find the ids in [traceability.md](traceability.md); find the code in [code-map.md](code-map.md) §3 (route) or §5 (table) |
| Decide | Check `docs/decisions/open-decisions.md` for the ids you found. A business rule that is not approved is an `ASSUMPTION`: implement the reversible option and record the question |
| Slice | One vertical slice: route + rule + SQL + template + test. Plan with `.agent/templates/slice-plan.md` |
| Build | Follow §2 and the recipe in §3 |
| Prove | `make check`, then run the flow in a browser or with `TestClient` |
| Handoff | [03-deliver.md](03-deliver.md) |

Find what a change touches before you make it:

```bash
grep -n "review_submission" docs/agent-guide/code-map.md     # callers, tables, tests
.venv/graph/bin/graphify affected "review_submission"        # same question, from the graph
```

## 2. Patterns

All routes are closures inside `create_app()` in `app/main.py`. They share the helpers
`page`, `go`, `conn_dep`, `require_user`, `require_staff`, `require_admin` and `csrf_guard`.

### 2.1 A page (GET)

```python
@app.get("/score", response_class=HTMLResponse)
def score_page(
    request: Request,
    user: CurrentUser = Depends(require_user),
    conn: sqlite3.Connection = Depends(conn_dep),
):
    return page(
        request,
        "score.html",
        {"active": "score", "balance": repo.wallet_balance(conn, user.id), ...},
        user=user,
    )
```

- Pass `user=user`; otherwise the header and navigation render as signed out.
- `active` selects the highlighted navigation item.
- Paths starting with `/admin` get the wide layout and the admin navigation (`base.html`).

### 2.2 An action (POST)

```python
@app.post("/admin/missions/{mission_id}/publish", dependencies=[Depends(csrf_guard)])
def admin_mission_publish(
    mission_id: str,
    request: Request,
    user: CurrentUser = Depends(require_admin),
    conn: sqlite3.Connection = Depends(conn_dep),
) -> RedirectResponse:
    mission = repo.mission_by_id(conn, mission_id, user.organization_id)   # scoped lookup
    if mission is None:
        raise HTTPException(status_code=404, detail="مأموریت یافت نشد.")
    try:
        repo.publish_mission(conn, mission, user)
    except DomainError as exc:
        raise HTTPException(status_code=409, detail=exc.message) from exc
    return go(f"/admin/missions/{mission_id}?published=1", request)
```

Every POST needs all five: the CSRF dependency, an access dependency, an organization check,
a domain call that raises `DomainError`, and a 303 redirect through `go()` so `?s=` survives.
Success banners are driven by a query flag (`?published=1`) that `base.html` turns into text.

### 2.3 A domain write (`app/repo.py`)

```python
def publish_mission(conn: sqlite3.Connection, mission: sqlite3.Row, actor) -> None:
    if mission["status"] != "draft":
        raise DomainError("NOT_DRAFT", "فقط مأموریت پیش‌نویس قابل انتشار است.")
    with conn:                                                        # one transaction
        conn.execute("UPDATE missions SET status = 'active' WHERE id = ?", (mission["id"],))
        audit(conn, actor.id, "mission.published", "mission", mission["id"])
```

- Validate first, then open the transaction. The audit row goes inside the same `with conn:`.
- `DomainError(CODE, persian_message)`: the code is stable and upper-case; the message is
  shown to the user as is.
- For a state change that two people can race on, put the expected state in the `WHERE`
  clause and check `cursor.rowcount` (see `repo.review_submission`).
- **`with conn:` does not nest.** The inner block commits everything the outer block has done
  so far. If a function must take part in a caller's transaction, it must not open its own:
  `scoring.award_sales_record` is written that way (caller: `repo.process_sales_import`,
  which uses `BEGIN IMMEDIATE` … `commit()`); `scoring.award_mission_approval` is also
  caller-owned now, and `repo.review_submission` wraps status + audit + award in one `with conn:`.

### 2.4 A score-producing path (`app/scoring.py`)

Every path that creates points does these five things, in this order:

1. Build a deterministic idempotency key from the source: `f"mission.approved:{submission_id}"`.
2. Return the existing event when the key is already present (`_existing`).
3. Look up the rule version that is in force (`find_rule_version`); no version →
   `ScoringError("NO_ACTIVE_RULE_VERSION")`. Never read points from code or from the mission row.
4. Build the `explain` payload: `rule_code`, `rule_version`, `calculation_type`, `conditions`,
   `input`, `output`, `is_sample`.
5. Call `_persist_award(...)`, which writes the event, the ledger entry, the wallet projection
   and the outbox row. The caller owns the transaction.

Rules for the engine are in `.agent/playbooks/scoring-and-rules.md`; the implemented contract
is `docs/engineering/scoring-engine.md`.

### 2.5 A form in a template

```html
<form method="post" action="{{ url('/admin/missions/' ~ mission['id'] ~ '/publish') }}">
  <input type="hidden" name="csrf" value="{{ csrf }}">
  <button class="btn btn--sm" type="submit">انتشار</button>
</form>
```

- Wrap **every** internal link and form action in `url(...)`. A bare `/path` drops the `?s=`
  session and signs the user out inside the embedded preview.
- Every POST form carries the hidden `csrf` field.
- Filters: `|fa` Persian digits, `|jdate` Jalali date, `|jdatetime` Jalali date and time.
- Text is Persian, layout is RTL, and each page handles its empty state (`{% else %}` branch).
- Classes come from `app/static/style.css`; there is no JavaScript and no build step.

### 2.6 A test

```python
from tests.conftest import ADMIN, VISITOR, login, post, row_id

def test_admin_publishes_a_draft(client: TestClient, settings: Settings, db) -> None:
    login(client, settings, ADMIN)
    mission_id = row_id(settings, "SELECT id FROM missions WHERE status = 'draft'", ())
    response = post(client, settings, f"/admin/missions/{mission_id}/publish")
    assert response.status_code == 200                     # redirects are followed
    row = db.execute("SELECT status FROM missions WHERE id = ?", (mission_id,)).fetchone()
    assert row["status"] == "active"
```

| Helper | Use |
|---|---|
| fixture `settings` | `Settings` with a temporary database and evidence directory |
| fixture `client` | `TestClient` on a freshly seeded app |
| fixture `db` | read connection to the same database, for assertions |
| `login(client, settings, MOBILE)` | sign in as a seeded user: `VISITOR`, `OTHER_VISITOR`, `OPERATOR`, `ADMIN` |
| `post(client, settings, path, data=…, files=…)` | POST with a valid CSRF value; `follow_redirects=False` to inspect the 303 |
| `row_id(settings, sql, params)` | first column of the first row |
| `app.seed.PNG_1PX` | valid image bytes for an evidence upload |

Assert on the database, not only on the page. For anything that awards points, assert the
count of `score_events`, the wallet balance, and that a second call creates nothing.

## 3. Recipes

### R1 — Add a page

1. Add the handler to `app/main.py` next to its neighbours (pattern 2.1).
2. Add the query to `app/repo.py`; take the organization as a parameter and filter by it.
3. Create `app/templates/<name>.html` extending `base.html`; include the empty state.
4. Link to it with `url(...)`.
5. Test: 200 for the allowed role, 303 to `/login` without a session, 403 for a wrong role,
   and 403 or 404 for another organization's data.
6. `make docs`. Update `docs/engineering/api-spec.md` and `docs/product/ux-ui-spec.md` or
   `docs/product/admin-panel-spec.md`.

### R2 — Add an action

1. Write the rule and the SQL in `app/repo.py` (pattern 2.3) with a new `DomainError` code and
   an `audit(...)` row.
2. Add the POST handler (pattern 2.2) and the form (pattern 2.5).
3. Tests: the happy path, each `DomainError`, missing CSRF → 403, wrong role → 403, other
   organization → 403 or 404, and the same request twice.
4. `make docs`. Update `docs/engineering/api-spec.md` (route, form fields, status codes).

### R3 — Change the schema

1. Add `db/migrations/NNNN_<what>.sql` with the next number. Files run once each, in filename
   order, recorded in `schema_migrations`.
2. Do not write `BEGIN` or `COMMIT` in the file: `app.db.apply_migrations` wraps the whole
   file and its bookkeeping row in one transaction.
3. Never edit a migration that has been merged; add a new one.
4. Keep it portable to PostgreSQL: text UUID keys, `NUMERIC` for points and money, ISO
   timestamps with offset, explicit `CHECK` lists.
5. Seed data for the new table goes in `app/seed.py`, marked SAMPLE.
6. `make seed` locally (the runner applies new files to an existing database too, but demo
   data is only seeded into an empty one).
7. `make docs`. Update `docs/architecture/database-erd.md` and `db/migrations/README.md`.

### R4 — Change scoring behaviour

Stop first: a change to a scoring rule, a point value or who may score needs a decision
(`AGENTS.md` §3). If none is approved, implement the reversible option as `ASSUMPTION` and
register the question (R8).

1. Read `.agent/playbooks/scoring-and-rules.md` and `docs/engineering/scoring-engine.md`.
2. Values live in `scoring_rule_versions` (`points`, `unit_size`, `effective_from`,
   `is_sample`). A new value is a new version; old events keep the version they were scored
   with.
3. A new source of points follows pattern 2.4 with its own key prefix and `source_type`.
4. Tests: exact points for known input, a second run creates nothing, wallet equals ledger,
   and the explain payload names the rule and version.
5. Update `docs/engineering/scoring-engine.md`, `docs/engineering/scoring-rule-matrix.md`
   and, for a new decision, `docs/decisions/decision-log.md` as `PROPOSED`.

### R5 — Add a setting

1. Add the field with its default to `Settings` in `app/config.py` and read it in `from_env`
   as `KILOOS_<NAME>` (use `_int_env` for positive integers).
2. Read it through `settings.<field>` inside `create_app`; never call `os.getenv` elsewhere.
3. Add the variable to the table in `docs/operations/runbook.md` and, when a developer must
   set it, to `.env.example`.
4. `make docs` (code-map §10 lists it).

The app reads the process environment only. It does not load a `.env` file; export the
variables or pass them on the command line.

### R6 — Record a decision or an open question

- A question for the client: add an `OD-xx` block to `docs/decisions/open-decisions.md`
  using `.agent/templates/open-decision.md`, status `OPEN`, with options, impact and a
  recommendation.
- An engineering choice: add a `D-0xx` block to `docs/decisions/decision-log.md` with status
  `PROPOSED`. Only the client's recorded confirmation makes it `APPROVED`.
- An architecture choice: add an ADR under `docs/architecture/decisions/` from
  `.agent/templates/adr.md`.
- `make doctor` validates the status values and that seeded `OD` ids still exist.

### R7 — Fix a defect from the backlog

1. Read the row's «جزئیات» section in `docs/delivery/backlog.md`: reproduction, cause, proposal.
2. Write the failing test first, from the reproduction.
3. Fix it with the smallest change that follows the patterns above.
4. Set the row's status to `DONE` and move the item out of "Known issues" in
   `docs/handoffs/current-state.md`.
5. Add the fix to `CHANGELOG.md` under `[Unreleased]`.

### R8 — Keep the map and the traceability current

- After any change to routes, SQL, templates, tests, constants or settings: `make docs`.
- When a requirement gains or loses code or tests, edit its entry in
  `.agent/context/traceability.json` (`state`, `code`, `tests`, `note`, `backlog`), then
  `make docs`. Symbols are written as `app/repo.py::review_submission`.
- When the change is large or you are about to hand off: `make graph`.

## 4. Which document to update for which change

`AGENTS.md` §12 gives the rule; these are the real files.

| You changed | Update |
|---|---|
| A route, form field or status code | `docs/engineering/api-spec.md` |
| A table, column or index | `docs/architecture/database-erd.md`, `db/migrations/README.md` |
| Scoring logic or a rule value | `docs/engineering/scoring-engine.md`, `docs/engineering/scoring-rule-matrix.md`, `docs/decisions/decision-log.md` |
| Sales import behaviour | `docs/engineering/sales-import.md`, `docs/operations/runbook.md` |
| A visitor screen | `docs/product/ux-ui-spec.md` |
| An admin screen, role or permission | `docs/product/admin-panel-spec.md`, `docs/product/prd.md` |
| Module boundaries or a dependency | `docs/architecture/solution-architecture.md`, `docs/architecture/technical-design.md`, an ADR |
| Configuration, operations, deployment | `docs/operations/runbook.md`, `docs/architecture/deployment-architecture.md` |
| Tests or release criteria | `docs/quality/qa-test-strategy.md` |
| Scope, plan or priorities | `docs/delivery/backlog.md`, `docs/delivery/execution-plan.md` |
| The demo path | `docs/delivery/demo-script.md` |
| Anything at all | `docs/handoffs/current-state.md`, `CHANGELOG.md`, and `make docs` |

## 5. Boundaries

- Out of MVP scope (`AGENTS.md` §7): real money wallet, token purchase or cash-out, live ERP
  integration, other group companies, end-customer login. Do not build or propose these.
- No new framework, queue, cache or service without measured evidence (`AGENTS.md` §14).
- In mode P: one tenant, demo login, one photo mission type, manual review, sample fixed
  points. Hardening work (group D in the backlog) starts only after P→H is recorded in
  `docs/decisions/decision-log.md`.
