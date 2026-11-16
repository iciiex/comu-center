# Real-workbook import spike — architecture decision note

MODE: P · Branch `real-import-spike` (from tag `demo-freeze-20261116`) · Status of every decision below: **ASSUMPTION**
(reversible engineering choices). Nothing here is an approved business rule.

## Goal

One vertical slice: **Workbook → Import → Validation → Mapping → Calculation → Reconciliation → Dashboard**
for the monthly marketing-reward workbook (reporting period Shahrivar 1405, Jalali — confirmed; editable in the import
configuration). Source facts: `audit/REAL-WORKBOOK-AUDIT.md`.

## Decisions

| ID | Decision | Why / how to reverse |
|---|---|---|
| AD-1 | Isolation by **git worktree + separate compose project**: `spike/comu-center`, `spike/sales-quest-arena` on branch `real-import-spike`; own image `kiloos-spike:local`, port 8091, volume `spike-data`, DB `/data/spike/kiloos-spike.db`, workbook store `/data/spike/workbooks`. | The demo Dockerfile builds from the demo working trees; checking out another branch there would change the demo build. Reverse: delete `spike/` and `git worktree remove`. |
| AD-2 | New package `app/realimport/`, **feature-flagged** (`KILOOS_REAL_IMPORT=1`), routes `/api/v1/ri/*`, admin-only + CSRF. Flag off ⇒ routes do not exist. | Keeps the demo code path byte-identical in behaviour. |
| AD-3 | **New tables only (`ri_*`)**, migration `0008`. Nothing is written to `sales_records`, `score_events`, `point_transactions` or game state. XP, organisational points and monetary rewards stay separate; rewards are *indicative PROPOSED* numbers, no settlement or payment code. | Demo contract is Rial/date/invoice based and cannot hold carton aggregates. |
| AD-4 | **Pseudonymisation at the API boundary** (HMAC-SHA256 with `KILOOS_PSEUDONYM_KEY`): `V-…` visitor, `E-…` employee, `C-…` customer. Source values are kept only in the isolated DB (requirement: preserve originals). Logs, audit payloads, fixtures and UI never show them. | Tested: no PII marker in any response or log. |
| AD-5 | **Config-driven workbook profile** (sheet roles, normalised Persian header aliases, business key, import config) instead of hard-coded parsing. | The workbook layout is not self-describing (swapped header labels, hidden sheets). |
| AD-6 | **Idempotency** via natural keys: workbook sha256; batch `(workbook, config_hash)`; fact `(batch, sheet, business_key_hash, dup_ordinal)`; calc run `(batch, rule_set, brand, level, input_hash)`. Repeats return the existing record. | Re-upload must never duplicate records or results. |
| AD-7 | Synchronous import (≈28k rows). | Background jobs later if needed. |
| AD-8 | `Decimal` everywhere; fractional and negative cartons preserved; **no carton → Rial conversion**. | Audit §D, §G. |
| AD-9 | Business rules (thresholds, rates, ladders, branch groups, targets) live in `ri_rule_sets` / `ri_branch_group_schemes` / `ri_targets`, versioned and immutable, status `PROPOSED` or `UNCONFIRMED`. The API cannot set `APPROVED`. | Decision register: `decision-register.md`. |

## Layers

1. **Raw** — `ri_workbooks`, `ri_import_batches`, `ri_raw_rows` (source values untouched).
2. **Normalised** — dimensions (period, branch, brand, sales line, customer group, SKU, customer, employee) and
   `ri_visitor_assignments` (**employee ≠ visitor assignment**; one employee may have several; personnel code is never a key) and `ri_sales_facts`.
3. **Organisational mappings** — branch-group schemes (four coexisting definitions, all UNCONFIRMED), mapping issues.
4. **Targets & achievement** — `ri_targets`.
5. **Calculation** — `ri_rule_sets`, `ri_calc_runs`, `ri_calc_results`, `ri_calc_result_inputs`.
6. **Reconciliation & audit** — `ri_reconciliation_checks`, `ri_workbook_references`, `audit_logs`.

## Safety rules enforced in code/tests

Original workbook read-only (mounted `:ro`, copy stored by hash); separate DB/storage; no PII outside the isolated DB;
no rule `APPROVED`; no payment/settlement; demo branches and DB untouched.
