# Database ERD & Schema (prototype)

- Status: **IMPLEMENTED (prototype)** for SQLite — `db/migrations/0001_init.sql` through `0006_game_demo_store.sql`
- Generated table-by-table view (columns, readers, writers): `docs/agent-guide/code-map.md` §5
- Target production engine: `OPEN` (ADR-0001). This schema is intentionally portable to PostgreSQL.
- Mode: P

---

## Relations (macro)

```text
organizations 1—* users
organizations 1—* missions 1—* scoring_rule_versions (by rule_code)
users         1—* submissions *—1 missions
submissions   1—* submission_evidences
submissions   1—0..1 score_events (source_type='mission_submission', source_id=submission.id)
score_events  1—1 point_transactions
users         1—1 point_wallets (projection)
organizations 1—* competitions
users         1—1 game_progress (personal game projection)
users         1—* game_completions (idempotent, append-only run records)
organizations 1—* org_unit_types 1—* org_units (parent_id is a same-tenant adjacency tree)
org_unit_types *—* org_unit_types (configured allowed parent types)
users         1—* org_memberships *—1 org_units (effective-dated, tenant-scoped)
users         1—* game_store_purchases 1—0..1 game_coin_transactions (demo game economy only)
*             → audit_logs / outbox_events
```

## Tables

| Table | Purpose | Key invariants |
|---|---|---|
| `organizations` | Tenant/organization | one seeded org in prototype |
| `users` | Identity + role + org | `UNIQUE(organization_id, mobile)`, role ∈ visitor/operator/admin |
| `missions` | Mission definition | `status ∈ draft/active/archived`, `max_per_user`, `rule_code` |
| `scoring_rule_versions` | Versioned scoring rules | `UNIQUE(rule_code, version)`; validity window; `is_sample=1` |
| `submissions` | Execution record | `UNIQUE(user_id, request_id)`; status machine |
| `submission_evidences` | Evidence files | sha256, content type, storage path |
| `score_events` | Append-only scoring ledger | `UNIQUE(idempotency_key)`; partial unique on `(source_type, source_id, rule_code, rule_version_id)` |
| `point_transactions` | Point ledger | 1 row per score event in the prototype |
| `point_wallets` | Balance projection | `balance = Σ point_transactions.amount` |
| `competitions` | Competition period | org-scoped, `is_sample` |
| `game_progress` | Sales Quest personal progression projection | one JSON state per user; separate from organizational points |
| `game_completions` | Server-validated game run history/idempotency | unique `(user_id, idempotency_key)`; no FK to organizational score ledger |
| `org_unit_types` | Configurable, tenant-specific unit labels/codes | unique `(organization_id, code)`; no fixed Tribal taxonomy |
| `org_unit_type_parent_types` | Allowed type-to-parent-type configuration | both types must belong to the same tenant |
| `org_units` | Generic organization tree nodes | same-tenant parent/type FKs; external key unique per tenant |
| `org_memberships` | Effective-dated user-to-unit relation | composite same-tenant user/unit FKs; source key idempotency |
| `game_store_purchases` | Demo Sales Quest offer purchase | unique `(user_id, idempotency_key)` and `(user_id, offer_id)`; sample virtual coins only |
| `game_coin_transactions` | Append-only demo-store spend record | signed integer amount, unique purchase source; separate from organizational points |
| `audit_logs` | Admin/domain actions | append-only |
| `outbox_events` | Transactional outbox | written in the same tx as the score event |

## Why these constraints

```sql
-- Idempotency: replaying an approval returns the original event.
CREATE UNIQUE INDEX ux_score_events_source
    ON score_events (source_type, source_id, rule_code, rule_version_id)
    WHERE corrects_event_id IS NULL;

-- One correction per event (migration 0002).
CREATE UNIQUE INDEX ux_score_events_corrects
    ON score_events (corrects_event_id)
    WHERE corrects_event_id IS NOT NULL;

-- Submit retry safety (double click / flaky network).
UNIQUE (user_id, request_id)  -- submissions

-- Rule versioning.
UNIQUE (rule_code, version)   -- scoring_rule_versions
```

## Data rules

- `score_events` is **append-only**: no UPDATE/DELETE in application code. A correction is another row
  with negative points and `corrects_event_id` set (see `scoring-engine.md`).
- Wallet is a projection, not the source of truth; recompute = `SUM(point_transactions.amount)`.
- `points`/`amount` declared `NUMERIC` (SQLite stores integers exactly; no float).
- Timestamps are ISO-8601 UTC (`+00:00`); display converts to Jalali (`app/jalali.py`).
- Soft delete is not implemented yet; historical rows are never removed by the app.

## Sales import tables (0003)

```
sales_imports 1──n sales_records
sales_user_map (organization_id, user_external_id) → users.id   -- explicit mapping only
```

- `sales_imports` keeps the file fingerprint (`UNIQUE (organization_id, file_sha256)`), lifecycle
  status, per-status counts, `points_sum` and `finished_at`.
- `sales_records` keeps one row per spreadsheet line with `row_number`, raw cells (`raw_json`),
  normalized values, status and error message. `ux_sales_records_external` is partial
  (`WHERE status IN ('valid','scored')`) so duplicates/invalid rows remain reportable.
- `scoring_rule_versions.unit_size` (added in 0003) is the divisor of the SAMPLE per-amount rule; it is
  data, not code.

## Migrations

- `db/migrations/*.sql` run at startup (`app.db.apply_migrations`), once each, in filename order:
  `0001_init.sql`, `0002_score_corrections.sql`, `0003_sales_import.sql`, `0004_game_progress.sql`, `0005_tribal_org_foundation.sql`, `0006_game_demo_store.sql`.
- `schema_migrations (name, applied_at)` records what ran, because 0003 needs a real `ALTER TABLE`
  that is not idempotent. Existing databases pick up the record automatically (0001/0002 are idempotent).
- The runner has no checksums or downgrades — it is a prototype stopgap; never edit an applied file.
- Before production: explicit versioned runner (Alembic/Knex), PostgreSQL, tested rollback path.
  Destructive migrations require backup + restore plan (AGENTS.md §6).

## Known gaps

- Partial unique index is SQLite/PostgreSQL compatible; MySQL is not supported.
- No `mission_audiences` table yet (missions are org-wide) — required for OD-02 targeting.
- No `submission_reviews` history table: one review per submission in the prototype; the audit log
  records the decision. A separate review-history table is a Harden-phase task.
- No table for teams or organization levels (MVP-10, OD-02) and none for notifications (EP-11).
- `sales_user_map` is filled by the seed only; there is no screen to manage it (backlog C1).
- Migration 0005 adds only generic org-unit types, same-tenant hierarchy, and effective-dated memberships as a Tribal foundation.
  It does not implement import, access grants, overlap validation, reports, scoring, leagues, or badges; those remain proposed.
- Migration 0006 records demo game-store purchases/spends only. Existing game coin earnings remain in the game progress projection;
  this is not a complete coin ledger or a production commerce system.
