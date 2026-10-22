# ADR-0008: SQLite adapter now (contract proof), PostgreSQL stays the target

Status: accepted; implemented and contract-tested. Refines ADR-0003.

**Context.** Roadmap task 2 needs durable storage, but no Docker/PostgreSQL
host exists yet in the delivery environment, and the invariants (idempotent
inserts, `control_version` compare-and-swap, append-only audit, eligibility
filtering) are testable without standing up production infrastructure.

**Decision.** Define storage-agnostic repository/outbox ports
(`ports/repositories.py`) and implement them with a stdlib `sqlite3` adapter
(`adapters/sqlite_store.py`, schema mirroring `db/migrations/0001_initial.sql`).
The PostgreSQL adapter remains the production target (ADR-0003 unchanged) and
must pass these same contract tests (parameterize the fixtures when it lands).
SQLite is approved for local dev, tests, and single-process demos only.

**Consequences.** + Persistence invariants are proven today, restart-safe, with
zero new dependencies; + the outbox/worker exists for task 3 to plug into.
− Two SQL dialects to keep conceptually aligned until Postgres lands; SQLite
keyword scoring is a placeholder for Postgres FTS (Persian tokenization still
an open PoC question); single-writer limits make SQLite unsuitable for the
pilot's concurrent webhook load — do not deploy it as the production store.

**Alternatives rejected.** Writing the Postgres adapter untested (no server to
verify against = fake progress); staying in-memory until infra exists (delays
proving CAS/idempotency where they actually bite — at the storage boundary).
