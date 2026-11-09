# ADR-0001: FastAPI + SQLite for the prototype

- Status: **PROPOSED**
- Date: 2026-11-09
- Owners: Architecture + Backend (proposal); approval: Product & Technology Lead
- Related: OD-12, doc 03 §10.3 (technology options), `decision-log.md` D-001

## Context

MS-01 (prototype) is due 2026-11-18 — nine days from this decision. The source specification lists
technology **options** (Flutter/React Native, React/Vue, Laravel/Spring Boot, PostgreSQL) but the
backend/mobile stack is explicitly an open decision, not an approved one.

The prototype must prove the end-to-end loop (mission → evidence → review → score → wallet → leaderboard)
and be demonstrable from a clean checkout. Whatever we pick now must not become an accidental platform
commitment.

## Options

| Option | Pros | Cons | Reversible? |
|---|---|---|---|
| **A. Python + FastAPI + SQLite + server-rendered Jinja** | Fastest path to a runnable end-to-end demo in the available environment; explicit SQL close to the target schema; portable to PostgreSQL | Not the spec's example stack; SQLite concurrency limits; server-rendered UI is not the target mobile app | Yes — domain rules and SQL are framework-agnostic |
| B. Laravel + MySQL | Matches one spec option; strong admin tooling | No existing code; slower first slice in this environment; team stack unconfirmed | Yes, but higher sunk cost |
| C. Spring Boot + PostgreSQL | Matches another spec option; strong typing | Heaviest setup for a 9-day prototype | Yes, high sunk cost |
| D. Do nothing / slide MS-01 | No tech risk | Misses the demo milestone; no feedback loop | No |

## Decision

Adopt **Option A for MODE: P only**:

- FastAPI app (`app/`), Jinja templates with RTL Persian UI, SQLite via explicit SQL (`db/migrations/`).
- The scoring contract, schema shape, idempotency and audit rules are written as portable domain logic,
  not framework features.
- This ADR does **not** choose the production mobile/backend stack. That remains `OPEN` and requires
  ADR-0002 after MS-02 feedback and OD-12.

## Consequences

- Positive: runnable prototype now; the demo path is real (not static mockups); tests cover scoring and access.
- Negative: SQLite is single-writer-ish; server-rendered UI is throwaway for the mobile target; Python
  stack may differ from the eventual team stack.
- Neutral: schema uses `NUMERIC`, UUID text keys, ISO timestamps, and partial unique indexes to ease a
  PostgreSQL move.

## Follow-up

- If the production stack is not Python: keep `app/scoring.py`, the schema and the tests as the
  executable specification; port the HTTP/UI layer.
- Before real users: PostgreSQL, explicit migration runner, OTP provider, CSRF, rate limiting,
  object storage for evidence, retention policy.
- Revisit trigger: MS-02 feedback or any decision on OD-12 (capacity/concurrency).
