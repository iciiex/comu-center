# Migrations

Prototype policy (MODE: P):

- Every `NNNN_*.sql` file in this folder is applied once, in filename order, when the app starts
  (`app/db.py::apply_migrations`). Applied file names are recorded in `schema_migrations`.
- Current files: `0001_init.sql` (base schema), `0002_score_corrections.sql` (one correction per
  score event), `0003_sales_import.sql` (sales import tables and `scoring_rule_versions.unit_size`).
- The runner wraps each file in one transaction. Do not write `BEGIN` or `COMMIT` inside a file.
- Never edit or rename an applied file; add the next number. The runner has no checksums and no
  downgrades: it is a prototype stopgap.
- `make seed` deletes the database for demo resets.
- Tables, columns and who reads or writes them: `docs/agent-guide/code-map.md` §5.
  Recipe for a schema change: `docs/agent-guide/02-continue.md`.

Before production (Harden):

1. Adopt a versioned migration runner with explicit up/down and checksums.
2. Move to PostgreSQL; the schema is written to be portable (UUID text keys, NUMERIC points,
   partial unique index, ISO timestamps).
3. No destructive migration without a tested backup/restore and a rollback plan.

Rules that must survive any migration:

- `score_events` is append-only.
- `point_wallets.balance` is a projection of `point_transactions`, never the source of truth.
- `scoring_rule_versions` is versioned; changes never rewrite history.
