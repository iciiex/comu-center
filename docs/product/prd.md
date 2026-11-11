# Product Requirements Document (working copy)

- Status: **PARTIAL** — requirements live in the source spec (doc 02); this file tracks deltas.
- Source: Google Drive → «Kiloos Club — Product Strategy & Scope» v0.1.
- Mode: P

## Implementation status (engineering judgement, 2026-11-11)

The status of every requirement, with the code and tests that carry it and the known gaps, is in
`docs/agent-guide/traceability.md` (generated from `.agent/context/traceability.json`). If this
summary and that file disagree, that file wins. No requirement is client-approved.

| State | Requirements |
|---|---|
| Implemented and tested | MVP-03 (dashboard), MVP-04 (mission management), MVP-05 (submission + evidence), MVP-06 (review), MVP-07 (scoring), MVP-13 (score history); BR-002 … BR-006, BR-011, BR-014 |
| Works with a `SAMPLE` contract or number | MVP-08 (sales import); BR-007 |
| Partial | MVP-09 (individual leaderboard only), MVP-11 (three admin sections); BR-001, BR-008, BR-009, BR-010, BR-012, BR-013 |
| Demo only | MVP-01 (user picker without credentials, OD-01) |
| Missing | MVP-02 (profile), MVP-10 (group competition), MVP-12 (reports) |

## Open questions
OD-01 … OD-12 — `docs/decisions/open-decisions.md`.

## Rule
No new requirement is "done" without an acceptance criterion and an ID. Numbers are `PROPOSED`
until approved in the decision log.
