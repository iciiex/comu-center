# Migrations

Prototype policy (MODE: P):

- `0001_init.sql` is the complete schema and runs at app startup (idempotent `CREATE ... IF NOT EXISTS`).
- There is **no** migration runner yet. Adding `0002_*.sql` without one is not supported; use
  `make seed` for demo resets.

Before production (Harden):

1. Adopt a versioned migration runner with explicit up/down.
2. Move to PostgreSQL; the schema is written to be portable (UUID text keys, NUMERIC points,
   partial unique index, ISO timestamps).
3. No destructive migration without a tested backup/restore and a rollback plan.

Rules that must survive any migration:

- `score_events` is append-only.
- `point_wallets.balance` is a projection of `point_transactions`, never the source of truth.
- `scoring_rule_versions` is versioned; changes never rewrite history.
