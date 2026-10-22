# Database migrations

**Status: proposed, not yet executed by the application.** The foundation core is
in-memory; the PostgreSQL persistence adapter is PoC task 2 (see
`docs/roadmap.md`). `0001_initial.sql` is the reviewed starting point for that
work so the domain contracts and the eventual schema evolve together.

Discipline (from day one):

1. Migrations are append-only and numbered; never edit an applied migration.
2. Every migration is reviewed with its rollback/forward-fix plan.
3. Apply with the migration tool chosen in PoC task 2 (candidate: Alembic, or
   plain ordered SQL applied in a transaction — decide then, record an ADR).
4. Back up before migrating any environment that holds real data
   (`docs/operations/backup-and-recovery.md`).
5. Product isolation is structural: every operational row carries `product_id`,
   and uniqueness constraints are scoped by product/channel account.
