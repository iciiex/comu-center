# Solution Architecture (prototype)

- Status: **PARTIAL / PROPOSED** — macro spec is doc 03; implementation is a modular monolith.
- Mode: P

## Implemented shape
```text
Browser (RTL, mobile-first; React PWA game + server-rendered admin/visitor pages)
   │  Same-origin HTML forms / multipart + JSON `/api/v1/game` BFF
FastAPI app (app/main.py)
   ├─ access layer (signed cookie or demo-only `?s=`, CSRF, current roles + org scope)
   ├─ domain services (repo.py, scoring.py, sales.py, game.py)
   ├─ SQLite (db/migrations/*.sql, applied at startup)
   └─ local evidence storage (var/evidence, private)

Tribal foundation: generic org-unit/membership tables are added in migration 0005. A default-off bootstrap
sentinel fails closed; tenant-scoped read-only org-unit list/detail APIs are implemented when explicitly enabled.
No Tribal writes/scoring/workflows are implemented. See `tribal-gamification-plan.md`
and `../engineering/tribal-api-contract.md`.
```

## Domain boundaries kept
Identity/Access · Organization (single tenant) · Mission · Submission/Verification · Organizational Scoring ·
Wallet (projection) · Competition/Leaderboard · Audit · Outbox · Sales Quest personal game progression (separate ledger).
Tribal organization tree/scoring/leagues are proposed only; do not conflate them with either current score domain.

## Explicit non-decisions
- Production backend/mobile stack: `OPEN` (ADR-0001 is prototype-only).
- No microservices, no queue worker, no cache — none justified by evidence yet.
- Outbox exists but no publisher/consumer yet.

## Next
Decide production stack (ADR-0002), PostgreSQL, object storage, and the async worker boundary
only after load evidence and MS-02 feedback.
