# Agent Guide

Everything an agent needs to **start**, **continue** and **deliver** work in this repository,
without searching for it.

- Mode: P (Prototype) · Last reviewed: 2026-11-11
- Binding rules live in [`AGENTS.md`](../../AGENTS.md). This guide does not add rules; it tells
  you where things are and how the existing rules apply to this code.
- If this guide and the code disagree, the code is right. Fix the guide in the same change.

## The three phases

| Phase | Read | Time |
|---|---|---|
| **Start** — set up, verify, understand the shape | [01-start.md](01-start.md) | 10 min |
| **Continue** — patterns and step-by-step recipes | [02-continue.md](02-continue.md) | as needed |
| **Deliver** — checks, documents, changelog, handoff | [03-deliver.md](03-deliver.md) | 5 min, at the end |

## Lookup files

| File | Use it to answer | Maintained by |
|---|---|---|
| [code-map.md](code-map.md) | Which function handles this route? Which tables does it touch? Which tests reach it? | generated (`make docs`) |
| [traceability.md](traceability.md) | Where is `BR-005` implemented and tested? What breaks when `OD-04` is decided? | generated (`make docs`) from curated links |
| [troubleshooting.md](troubleshooting.md) | Why does this fail? Known traps in this code and this sandbox. | by hand |
| [knowledge-graph.md](knowledge-graph.md) | How to query the graph in `graphify-out/` and how far to trust it. | by hand; graph by `make graph` |

## Find anything

| I need… | Go to |
|---|---|
| The current state: what works, what is broken, what is next | [`docs/handoffs/current-state.md`](../handoffs/current-state.md) |
| The whole picture in one read (Persian) | [`docs/handoffs/handover.md`](../handoffs/handover.md) |
| The next task, with evidence and size | [`docs/delivery/backlog.md`](../delivery/backlog.md) |
| What changed, and when | [`CHANGELOG.md`](../../CHANGELOG.md) |
| The handler of a URL, its template, its tests | [code-map.md](code-map.md) §2–§3 |
| Every reader and writer of a table | [code-map.md](code-map.md) §5 |
| Where an error code is raised | [code-map.md](code-map.md) §8 |
| Audit actions, outbox events, idempotency keys | [code-map.md](code-map.md) §9 |
| Environment variables and defaults | [code-map.md](code-map.md) §10, meaning in [`runbook.md`](../operations/runbook.md) |
| The code and tests behind a requirement id | [traceability.md](traceability.md) |
| Product facts and the id catalogue (`MVP`, `BR`, `EP`, `OD`, `MS`) | [`.agent/CONTEXT.md`](../../.agent/CONTEXT.md) |
| What is approved (nothing yet) and what is proposed | [`docs/decisions/decision-log.md`](../decisions/decision-log.md) |
| Questions that only the client can answer | [`docs/decisions/open-decisions.md`](../decisions/open-decisions.md) |
| HTTP contract, session and CSRF rules | [`docs/engineering/api-spec.md`](../engineering/api-spec.md) |
| Scoring rules and guarantees | [`docs/engineering/scoring-engine.md`](../engineering/scoring-engine.md), [`.agent/playbooks/scoring-and-rules.md`](../../.agent/playbooks/scoring-and-rules.md) |
| Sales import behaviour | [`docs/engineering/sales-import.md`](../engineering/sales-import.md), [`.agent/playbooks/sales-import.md`](../../.agent/playbooks/sales-import.md) |
| Schema and migration rules | [`docs/architecture/database-erd.md`](../architecture/database-erd.md), [`db/migrations/README.md`](../../db/migrations/README.md) |
| How to run, reset, back up | [`docs/operations/runbook.md`](../operations/runbook.md) |
| The demo, click by click (Persian) | [`docs/delivery/demo-script.md`](../delivery/demo-script.md) |
| What is tested and what is not | [`docs/quality/qa-test-strategy.md`](../quality/qa-test-strategy.md) |
| Templates for a slice plan, PR, ADR, open decision | [`.agent/templates/`](../../.agent/templates) |

## Commands you will use

```bash
make setup        # once: virtualenv + dependencies
make run          # http://0.0.0.0:8000 with reload
make check        # ruff + pytest (includes the generated-docs check)
make docs         # regenerate code-map.md and traceability.md after a code change
make docs-check   # same check the tests run, plus the state of the knowledge graph
make doctor       # repository health: structure, decisions, handoff freshness, secrets
make seed         # delete var/kiloos.db and reseed the demo data
make graph        # rebuild graphify-out/ (needs network on first use)
```

## Keeping this guide true

- `code-map.md` and `traceability.md` are generated. Never edit them by hand; run `make docs`.
  `tests/test_docs.py` fails while they are stale, so `make check` tells you.
- Curated requirement links live in `.agent/context/traceability.json`. Update them when a
  requirement gains or loses code or tests. A link to a symbol that no longer exists fails
  the same test.
- The hand-written files state facts that were checked on the review date above. When you
  change behaviour they describe, change them in the same commit (`AGENTS.md` §12).
