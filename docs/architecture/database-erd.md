# Database ERD & Schema (prototype)

- Status: **IMPLEMENTED** for SQLite — `db/migrations/0001_init.sql`
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
| `audit_logs` | Admin/domain actions | append-only |
| `outbox_events` | Transactional outbox | written in the same tx as the score event |

## Why these constraints

```sql
-- Idempotency: replaying an approval returns the original event.
CREATE UNIQUE INDEX ux_score_events_source
    ON score_events (source_type, source_id, rule_code, rule_version_id)
    WHERE corrects_event_id IS NULL;

-- Submit retry safety (double click / flaky network).
UNIQUE (user_id, request_id)  -- submissions

-- Rule versioning.
UNIQUE (rule_code, version)   -- scoring_rule_versions
```

## Data rules

- `score_events` is **append-only**: no UPDATE/DELETE in application code.
- Wallet is a projection, not the source of truth; recompute = `SUM(point_transactions.amount)`.
- `points`/`amount` declared `NUMERIC` (SQLite stores integers exactly; no float).
- Timestamps are ISO-8601 UTC (`+00:00`); display converts to Jalali (`app/jalali.py`).
- Soft delete is not implemented yet; historical rows are never removed by the app.

## Migrations

- `0001_init.sql` is idempotent (`CREATE TABLE IF NOT EXISTS`) and runs at startup for the prototype.
- Before production: switch to an explicit migration runner, PostgreSQL, and a tested rollback path.
  Destructive migrations require backup + restore plan (AGENTS.md §6).

## Known gaps

- Partial unique index is SQLite/PostgreSQL compatible; MySQL is not supported.
- No `mission_audiences` table yet (missions are org-wide) — required for OD-02 targeting.
- No `submission_reviews` history table: one review per submission in the prototype; the audit log
  records the decision. A separate review-history table is a Harden-phase task.
- No `sales_*` tables yet (EP-07 not implemented).
