# Database migrations

**Status: proposed, not yet executed against PostgreSQL.** The repository
contracts are implemented and proven by the SQLite adapter
(`adapters/sqlite_store.py`, ADR-0008) whose schema mirrors this one;
`0001_initial.sql` remains the starting point for the PostgreSQL adapter so
the domain contracts and the production schema evolve together.

Discipline (from day one):

1. Migrations are append-only and numbered; never edit an applied migration.
2. Every migration is reviewed with its rollback/forward-fix plan.
3. Apply with the migration tool chosen in PoC task 2 (candidate: Alembic, or
   plain ordered SQL applied in a transaction — decide then, record an ADR).
4. Back up before migrating any environment that holds real data
   (`docs/operations/backup-and-recovery.md`).
5. Product isolation is structural: every operational row carries `product_id`,
   and uniqueness constraints are scoped by product/channel account.
