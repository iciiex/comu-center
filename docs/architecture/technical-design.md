# Technical Design (prototype)

- Status: **PARTIAL** — flows implemented as code; expand as features land.
- Mode: P

## Flows
- **Mission view:** `list_active_missions` / `get_mission_for_user` (status + window + org).
- **Submit:** validate evidence → insert submission + evidence (unique request_id) → audit.
- **Review:** state guard (`submitted` only) → status update + audit → scoring on approve.
- **Score:** rule lookup by effective window → transaction (event, ledger, wallet, outbox) → explain JSON.
- **Rule change:** retire current version → publish next version → audit.
- **Leaderboard:** on-read aggregation of valid score events in the active competition window.

## Design rules in code
- UUID text keys, `NUMERIC` points, ISO UTC timestamps.
- Domain errors with stable codes (`app/repo.py:DomainError`).
- No business logic in templates.

## Gaps
- No API versioning layer for mobile clients.
- No idempotency middleware for future REST endpoints.
- Correction/reversal flow not implemented.
