# Solution Architecture (prototype)

- Status: **PARTIAL / PROPOSED** — macro spec is doc 03; implementation is a modular monolith.
- Mode: P

## Implemented shape
```text
Browser (RTL, mobile-first)
   │  HTML forms / multipart
FastAPI app (app/main.py)
   ├─ access layer (signed session token as cookie or `?s=`, CSRF, role + org scope)
   ├─ domain services (repo.py, scoring.py, sales.py)
   ├─ SQLite (db/migrations/*.sql, applied at startup)
   └─ local evidence storage (var/evidence, private)
```

## Domain boundaries kept
Identity/Access · Organization (single tenant) · Mission · Submission/Verification · Scoring ·
Wallet (projection) · Competition/Leaderboard · Audit · Outbox.

## Explicit non-decisions
- Production backend/mobile stack: `OPEN` (ADR-0001 is prototype-only).
- No microservices, no queue worker, no cache — none justified by evidence yet.
- Outbox exists but no publisher/consumer yet.

## Next
Decide production stack (ADR-0002), PostgreSQL, object storage, and the async worker boundary
only after load evidence and MS-02 feedback.
