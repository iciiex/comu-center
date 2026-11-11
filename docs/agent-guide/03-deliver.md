# 03 — Deliver

A task is finished when the next agent can continue without the conversation
(`AGENTS.md` §13). This page is the checklist that gets you there.

- Mode: P (Prototype) · Last reviewed: 2026-11-11
- Before: [02-continue.md](02-continue.md) · Index: [README.md](README.md)

## 1. Gate: run these and read the output

```bash
make docs      # regenerate code-map.md and traceability.md
make check     # ruff + pytest
make doctor    # structure, decision statuses, handoff freshness, secret patterns
make graph     # only when code, schema or documents changed in a way others will query
```

| Command | Must show | If it does not |
|---|---|---|
| `make docs` | `wrote:` or `unchanged:` for both files | An `error:` line names a curated link to a symbol or backlog row that no longer exists; fix `.agent/context/traceability.json` |
| `make check` | `All checks passed!` and no failed test | Fix it. Do not skip, mark `xfail` or delete a test to get green |
| `make doctor` | `0 fail` | The message names the file and the rule |
| `make graph` | `graph: N nodes, M edges …` | See [knowledge-graph.md](knowledge-graph.md) § Limits |

"Tested" means the command ran and you saw the result (`AGENTS.md` §10). Report the real
line, for example `pytest → 58 passed, 1 warning in 6.20s`. If something could not run, say
what, why, and what you did instead.

CI (`.github/workflows/ci.yml`) runs install, `ruff check app tests`, `pytest` and an
app-boot check on every pull request. Its secret scan step cannot fail (backlog A10), so
`make doctor` is the only real secret check today.

## 2. Check the behaviour yourself

- Walk the changed flow in a browser (`make run`) or with `TestClient`, as each role that can
  reach it, and as one that must not.
- For a UI change look at: empty state, error state, RTL layout, Persian digits, and the page
  opened with `?s=` in the URL.
- For a change on the demo path, replay the affected steps of
  [`docs/delivery/demo-script.md`](../delivery/demo-script.md).

## 3. Update the documents

In the same change as the code (`AGENTS.md` §12). The mapping from change to file is in
[02-continue.md](02-continue.md) §4. Always:

| File | What to write |
|---|---|
| `docs/handoffs/current-state.md` | Move finished items to "Working features", remove fixed "Known issues", add new ones, replace the verification block with today's real output, set the next tasks |
| `CHANGELOG.md` | One line per user-visible or contract change under `[Unreleased]`, with the ids |
| `docs/delivery/backlog.md` | Set the row's status; add a row for anything you found and did not fix |
| `.agent/context/traceability.json` | New code or tests for a requirement, or a changed state |
| The specification that describes what you changed | The new behaviour, not a promise |

`make doctor` enforces this shape for `docs/handoffs/current-state.md`:

- a line `Last updated: YYYY-MM-DD`, not older than 21 days;
- a line `- Mode: P` (or `H`, `S`);
- the headings `## Working features`, `## In progress`, `## Known issues`,
  `## Next recommended tasks`, `## Tests and verification`.

It also checks that markdown links in `docs/README.md` resolve, that every `OD` and `D` block
has a valid status, and that no tracked text file contains a private key or a token pattern.

### Statuses you may write

`APPROVED` · `PROPOSED` · `ASSUMPTION` · `OPEN` · `IMPLEMENTED` · `DEPRECATED` (`AGENTS.md` §3).
Implemented is not approved. Only the client's recorded confirmation in
`docs/decisions/decision-log.md` makes anything `APPROVED`; an agent never writes that status
on its own authority.

## 4. Commit and pull request

- Work on the branch you were given. One slice per pull request.
- Commit subjects in the history follow Conventional Commits with a scope, and the body ends
  with the ids: `feat(sales): …`, `fix(scoring): …`, `docs(agent-guide): …`, then
  `Refs: D-005, EP-07`.
- Pull request body: `.agent/templates/pr.md` (what changed, why, contract, test output,
  documents, risk and rollback).
- Review checklist: `.agent/playbooks/review-and-handoff.md` §۱.
- Never commit `var/`, `.env`, a virtualenv, real personal data or a secret.

## 5. Hand off

Reply with this block (`AGENTS.md` §13). Every line states a fact you verified.

```text
MODE: P
TASK: …
STATUS: Done | Partial | Blocked
CHANGED: files
CONTRACT: API / DB / rule change, or «هیچ»
VERIFIED: commands + real results
DECISIONS: new APPROVED / ASSUMPTION / OPEN
RISKS: …
NEXT: the exact file or backlog row to start from
```

For a long task, or when the next agent is someone else, also update
[`docs/handoffs/handover.md`](../handoffs/handover.md) (structure:
`.agent/templates/handoff.md`).

The 30-second rule (`.agent/playbooks/review-and-handoff.md`): from `current-state.md` alone,
the next agent can tell where the project is, what works, what is mocked, which decisions are
open and where to start.

## 6. Final self-check

- [ ] The requirement is named by id and has an acceptance check.
- [ ] Negative tests exist for access (wrong role, other organization, missing CSRF).
- [ ] A score-producing path is idempotent, transactional and audited, and a test proves it.
- [ ] Sample values are labelled `SAMPLE`; nothing unapproved is stated as a fact.
- [ ] `make docs`, `make check` and `make doctor` were run after the last edit.
- [ ] `current-state.md`, `CHANGELOG.md` and the backlog say what is true now.
- [ ] Anything left unfinished is written down with the condition for finishing it.
