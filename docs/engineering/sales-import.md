# Sales Import (EP-07) — implemented slice

- Status: **IMPLEMENTED (prototype)** · Mode: P · Last updated: 2026-11-09
- Access: **admin only** (operator/visitor → 403)
- Format: **XLSX** (employer decision, D-005) via `openpyxl` read-only
- Data: contract and formula are **SAMPLE** until OD-03 / OD-04 are approved

> The playbook (`.agent/playbooks/sales-import.md`) is the source of the rules. This document
> describes what the code actually does so the next agent does not invent behaviour.

## Lifecycle

```
upload ──► validated ──► processing ──► completed
   │                          └──────► failed
   └──► rejected (file-level problem: bad xlsx, missing headers, too many rows, duplicate file)
```

- **Upload never scores.** It validates file and rows and stores both.
- **Process is explicit** (`POST /admin/sales/{id}/process`) and idempotent: it only touches rows
  still in `valid`; a second run reports `processed=0` and writes nothing.
- A rejected file is not processable; a failed import keeps the error message for inspection.

## Contract (SAMPLE)

| Column | Required | Rule |
|---|---|---|
| `external_id` | ✅ | unique per organization; a repeat is a `duplicate`, not an error that blocks the file |
| `user_external_id` | ✅ | must exist in `sales_user_map` for the org — **never** matched by phone number |
| `sale_date` | ✅ | `YYYY-MM-DD` (or Excel date cell); not in the future |
| `sku_code` | ✅ | stored as-is; SKU multipliers are OD-05 (not implemented) |
| `quantity` | ✅ | numeric > 0 |
| `amount` | ✅ | numeric ≥ 0 |
| `customer_external_id` | ❌ | stored |
| `branch_code` | ❌ | stored |

Headers are matched case-insensitively after trimming. Missing required headers reject the file and
list them. Blank rows are skipped. Limits: 5 MiB, 5,000 data rows (`KILOOS_SALES_MAX_BYTES`,
`KILOOS_SALES_MAX_ROWS`).

## Row outcomes

| Status | Meaning | Scored? |
|---|---|---|
| `valid` | passed every check | on process |
| `invalid` | data problem (see codes) | no |
| `duplicate` | same id in this file or a previous import | no |
| `scored` | a score attempt was made | yes (unless amount < one unit) |

Codes: `E_EXTERNAL_ID`, `E_USER_ID`, `E_DUPLICATE_IN_FILE`, `E_DUPLICATE_EXISTING`, `E_USER_MAPPING`,
`E_DATE`, `E_FUTURE_DATE`, `E_QUANTITY`, `E_AMOUNT`, `E_SKU`. Messages are Persian and shown with the
row number; codes stay internal.

A bad row never rejects the file: the others are still processed and the report shows the row number.

## Dedupe

| Scenario | Behaviour |
|---|---|
| same file uploaded twice | `ux_sales_imports_fingerprint` → 409 with the existing import id |
| same `external_id` in the same file | row `duplicate` (`E_DUPLICATE_IN_FILE`) |
| same `external_id` in another import | row `duplicate` (`E_DUPLICATE_EXISTING`) |
| re-running process | rows already `scored` are skipped; `score.record:<id>` keeps scoring idempotent |

`ux_sales_records_external` is **partial** (`WHERE status IN ('valid','scored')`) so invalid and
duplicate rows can still be stored for the report.

## Scoring

Active rule `SALES_AMOUNT_SAMPLE` (SAMPLE): `floor(amount / unit_size) * points`, where
`unit_size` and `points` come from `scoring_rule_versions` (seeded 1,000,000 → 1 point).
Amounts below one unit produce **no event** (the row is still marked `scored`).

Each event: `source_type='sales_record'`, `idempotency_key='sales.record:<id>'`, explain payload with
`rule_code`, `rule_version`, `unit_size`, `amount`, `units`, `points`, `is_sample=true`.
Event + ledger + wallet + outbox are written in one transaction (`scoring._persist_award`).

The rule version is selected **at processing time** (not at `sale_date`). That choice is recorded in
D-005 and must be revisited if back-dated imports become normal.

## Reconciliation (shown on the detail page)

```
row_count == valid + invalid + duplicate + scored
sum(score_events.points for the import) == sales_imports.points_sum
```

A mismatch is displayed as a red warning; it is never hidden.

## Demo

```bash
python -m app.sample_sales            # writes var/sales-sample.xlsx (SAMPLE)
```
Upload it at `/admin/sales/new` as «نگار تهرانی» (admin): 6 rows → 4 valid, 1 duplicate, 1 unmapped
user; processing awards 15 points (4 + 2 + 8 + 1) across the three mapped visitors.

## Not implemented (explicit)

- XLSX → CSV conversion, multi-sheet imports, column mapping UI
- partial corrections of sales events (use the score correction flow per event)
- SKU multipliers, targets, caps (OD-05)
- scheduled/automated imports and ERP integration (OD-11)
- deleting an import (evidence-style retention decision is still open)
