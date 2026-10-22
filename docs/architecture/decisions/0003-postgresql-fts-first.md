# ADR-0003: PostgreSQL for operational data; full-text search before vectors

Status: accepted as direction; persistence not yet implemented (schema proposed
in `db/migrations/0001_initial.sql`).

**Context.** Messages, conversations, knowledge, and audit need one durable,
transactional store; conversation control needs atomic compare-and-swap on
`control_version`; FAQ retrieval needs "good enough" search on a small,
curated corpus.

**Decision.** PostgreSQL 16. Knowledge retrieval starts with Postgres
full-text search + the eligibility filter. Add pgvector only when measured
FAQ misses justify semantic retrieval (new ADR with evaluation data).
Background work starts as a simple DB-backed job/outbox pattern before any
broker is introduced.

**Consequences.** + One system to back up/secure; + transactions protect the
handover race; + permissive PostgreSQL License; − FTS quality for
Persian/other languages must be validated in the PoC (stemming/tokenization) —
recorded as an open question, not assumed.

**Alternatives rejected (for now).** Dedicated vector DB (operational cost
without evidence); SQLite for anything beyond throwaway local tests;
Mongo/document store (weaker fit for relational invariants).
