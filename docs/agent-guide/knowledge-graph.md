# Knowledge Graph

The repository's knowledge as one graph: code, schema, tests, templates, requirement ids,
decisions and documents, with the links between them. Use it to answer "what is connected to
this?" in one command instead of a chain of searches.

- Mode: P (Prototype) · Last reviewed: 2026-11-11
- Index: [README.md](README.md)

## 1. What is in `graphify-out/`

| File | What it is | Use it for |
|---|---|---|
| `graph.json` | The graph: nodes, links, communities (node-link JSON) | Queries (§3) and scripts (§4) |
| `GRAPH_REPORT.md` | Summary: communities, most-connected nodes, gaps | A first look at the shape of the system |
| `graph.html` | Interactive view for a browser | Exploring by eye; it loads one script from `unpkg.com`, so it needs internet access |
| `BUILD_INFO.json` | Build date, tool version, counts per edge kind, fingerprint of the sources | Checking what the graph was built from |

The graph is committed, so queries work on a fresh checkout without building anything.

## 2. How it is built, and what that means for trust

`make graph` runs `.agent/tools/knowledge_map.py --graph`. No language model is involved and
nothing leaves the machine. Two layers are merged:

| Layer | Source | Edge confidence |
|---|---|---|
| Structure | [graphify](https://github.com/Graphify-Labs/graphify) parses Python and SQL with tree-sitter and reads markdown headings | `EXTRACTED`; graphify marks its own cross-file guesses `INFERRED` |
| Project links | `knowledge_map.py` adds what graphify cannot see: routes and their handlers, templates and their forms, SQL reads and writes per function, HTTP requests made by tests, and every `MVP`/`BR`/`EP`/`OD`/`D`/`ADR`/`MS` id with the places that mention it | `EXTRACTED` |
| Curated links | `.agent/context/traceability.json`: which code implements a requirement and which tests verify it | `INFERRED`, score 0.85 — a reviewed judgement, not a parse result |

Read the labels this way:

- `EXTRACTED` — found in the source text. Reliable as a pointer; still read the code.
- `INFERRED` — a judgement or a guess. Confirm it before you act on it.
- A missing edge proves nothing. The parser does not see dynamic calls, SQL built at run
  time, or meaning in prose.

## 3. Queries

Run from the repository root; the commands read `graphify-out/graph.json` relative to the
current directory. `make graph` installs the tool into `.venv/graph` on first use.

```bash
G=.venv/graph/bin/graphify

$G explain "BR-005"                         # a node and everything attached to it
$G explain "review_submission"
$G explain "POST /admin/submissions/{submission_id}/review"
$G path "POST /admin/sales/{import_id}/process" "score_events"   # how two things connect
$G affected "review_submission"             # what depends on it: callers, routes, templates, tests
$G affected "score_events" --depth 1        # every function and test that touches a table
$G query "sales import duplicate" --budget 1500   # neighbourhood of the matching nodes
$G god-nodes                                # the most connected nodes
```

Real output, shortened:

```text
$ graphify path "POST /admin/sales/{import_id}/process" "score_events"
Shortest path (4 hops):
  POST /admin/sales/{import_id}/process --calls--> admin_sales_process()
  --calls--> process_sales_import() --calls--> award_sales_record() --uses--> score_events

$ graphify affected "review_submission" --depth 3
- admin_decide() [calls] app/main.py
- POST /admin/submissions/{submission_id}/review [calls] app/main.py
- admin_review.html [references] app/templates/admin_review.html
- awarded_submission() [calls] tests/test_corrections.py
- test_approve_redirect_keeps_queue_filter() [calls] tests/test_flow.py
- test_full_flow_approval_scores_once() [calls] tests/test_flow.py
- test_reject_requires_reason_and_awards_nothing() [calls] tests/test_flow.py
```

Names you can ask for:

| Kind | Write it as |
|---|---|
| Function, class, test | `review_submission`, `Settings`, `test_wallet_matches_ledger` |
| Table, index | `score_events`, `ux_score_events_corrects` |
| Route | `GET /score`, `POST /admin/submissions/{submission_id}/review` (exactly as in code-map §2) |
| Template | `admin_review.html` |
| Requirement, decision, milestone | `MVP-07`, `BR-005`, `EP-07`, `OD-04`, `D-004`, `ADR-0001`, `MS-01` |
| Document section | its heading text, or a prefix of it |

Lookup order is exact label or id, then prefix, then substring. Exit codes: `0` answered,
`3` the name is ambiguous (the candidates and their ids are printed; retry with an id),
`4` nothing matched. To limit a name to one file, write `app/repo.py::audit`.

## 4. Scripting against `graph.json`

`explain` prints the relation (`uses`) but not its kind. The kind is in each link's `context`
field: `sql_read`, `sql_write`, `route_handler`, `renders`, `form_action`, `http_test`,
`verifies`, `curated`, `mention`, `call`, `import` and a few more (counts per kind are in
`BUILD_INFO.json`). Example: who writes a table.

```bash
python3 - <<'EOF'
import json
g = json.load(open("graphify-out/graph.json"))
label = {n["id"]: n["label"] for n in g["nodes"]}
for e in g["links"]:
    ends = {label[e["source"]], label[e["target"]]}
    if e.get("context") == "sql_write" and "point_wallets" in ends:
        print(sorted(ends - {"point_wallets"})[0], "—", e["source_file"])
EOF
# _persist_award() — app/scoring.py
# reverse_event() — app/scoring.py
```

Node fields: `id`, `label`, `file_type` (`code`, `document`, `concept`, `rationale`),
`source_file`, `source_location`, `community`. Link fields: `source`, `target`, `relation`,
`context`, `confidence`, `confidence_score`, `source_file`, `source_location`.

## 5. Graph or generated map?

| Question | Fastest answer |
|---|---|
| Which handler, template, tables and tests belong to this route? | [code-map.md](code-map.md) §3 |
| Who reads or writes this table, by operation? | [code-map.md](code-map.md) §5 |
| Where is this requirement implemented and tested? Which backlog rows touch it? | [traceability.md](traceability.md) |
| What breaks if I change this function? | `graphify affected` |
| How are these two things related? | `graphify path` |
| What is everything connected to this id, across code and documents? | `graphify explain` |
| What are the main parts of the system? | `graphify-out/GRAPH_REPORT.md` |

The two generated maps are always current: `tests/test_docs.py` fails when they are stale.
The graph can lag behind (§6).

## 6. Keeping it current

```bash
make docs-check   # prints: knowledge graph: up to date | STALE | not built
make graph        # rebuilds only when the sources changed
.venv/graph/bin/python .agent/tools/knowledge_map.py --graph --force   # rebuild regardless
```

- Rebuild before a handoff and after a change that others will query: new routes, tables,
  requirement links or documents.
- The fingerprint in `BUILD_INFO.json` covers the code, tests, migrations, templates,
  markdown documents, `traceability.json` and the generator itself.
- The build is deterministic: two builds from the same sources gave byte-identical
  `graph.json`, `graph.html` and `GRAPH_REPORT.md` (checked on 2026-11-11). The report and
  `BUILD_INFO.json` carry the build date, so a rebuild on another day changes those lines.
- First use needs network access to PyPI to install `graphifyy[sql]`, pinned in the
  `Makefile` (`GRAPHIFY_VERSION`) and in `knowledge_map.py` (`GRAPHIFY_PIN`). Change both
  together, rebuild, and review the diff of `GRAPH_REPORT.md`.

## 7. Limits

- **Do not run `graphify update`, `graphify extract`, `graphify cluster-only` or
  `graphify watch` here.** They rebuild `graphify-out/` from graphify's own extraction and
  know nothing about the project layer (routes, templates, SQL usage, requirement ids,
  curated links). Always use `make graph`.
- Do not run `graphify codex install`, `graphify hook install` or any other
  `graphify … install` command. The platform installers write a graphify section into
  `AGENTS.md`, which is the binding contract of this repository, and the git hooks rebuild
  the graph without the project layer.
- graphify's semantic extraction of prose and images needs a language-model API key and was
  not used. Documents therefore contribute their heading structure and the ids and links
  written in them, not the meaning of their paragraphs.
- graphify has no parser for Jinja templates; template nodes come from the project layer
  and carry only what `knowledge_map.py` reads: `extends`, links, form actions.
- `graphify query` is a keyword-seeded neighbourhood search with a token budget. It does not
  answer questions; for an exact answer use `explain`, `path`, `affected` or the code map.
- Community names in `GRAPH_REPORT.md` are the label of each cluster's hub node, chosen by
  an algorithm. Treat them as groupings, not as architecture.
- The PyPI package is named `graphifyy`; there is no distribution called `graphify`.
