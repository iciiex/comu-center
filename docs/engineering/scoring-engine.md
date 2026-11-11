# Scoring Engine (prototype)

- Status: **IMPLEMENTED** — `app/scoring.py`
- Mode: P · Last updated: 2026-11-11
- Contract source: spec doc 06/06-A + `.agent/playbooks/scoring-and-rules.md`

---

## Contract

```text
Event (what happened) → Rule Version (under which rule) → Score Event (append-only)
        → Point Transaction (ledger) → Wallet Projection (display only) → Leaderboard
```

Implemented sources of points:

| Source | `source_type` | Idempotency key | Calculation | Function |
|---|---|---|---|---|
| Approved mission submission | `mission_submission` | `mission.approved:{submission_id}` | `fixed` | `award_mission_approval` |
| Processed sales row (`SAMPLE`, D-005) | `sales_record` | `sales.record:{record_id}` | `per_unit_amount` | `award_sales_record` |
| Correction of one event (D-004) | same as the original | `score.reversed:{event_id}` | negative of the original | `reverse_event` |

Other proposed event types (`target.achieved`, `team.performance`) are **not** implemented; they
require OD-04/OD-05 and are backlog items.

## Data written on approval (one transaction)

1. `score_events` row: `source_type='mission_submission'`, `source_id=submission.id`,
   `rule_code`, `rule_version_id`, `points`, `occurred_at`, `idempotency_key`, `explain_json`.
2. `point_transactions` row (ledger).
3. `point_wallets` projection upsert (`balance = balance + points`).
4. `outbox_events` row (`score.posted`) — same commit, so no lost event.

Idempotency key: `mission.approved:{submission_id}`.
Second layer: partial unique index on `(source_type, source_id, rule_code, rule_version_id)`.
Third layer: submission state machine (`submitted → approved|rejected` only once).

> Note: the second layer includes `rule_version_id`, so a *recalculation under a new rule* would be
> allowed by the index — but this is intentionally **not** exposed. Recalculation must be an explicit
> correction/reversal flow (Harden phase), never a silent re-award.

## Rule selection

`find_rule_version(rule_code, at)` picks the published version where
`effective_from <= at < effective_to`, highest version wins.

When an admin changes a mission's points:

1. current published version → `retired`, `effective_to = now`
2. new version `n+1` inserted with `effective_from = now`, `published`
3. `missions.points` updated for display
4. `audit_logs` records `mission.updated` with `new_rule_version: true`

Past events keep their `rule_version_id`; their points never change.

## Explainability

`explain_json` example:

```json
{
  "rule_code": "MISSION_SAMPLE_01",
  "rule_version": 1,
  "calculation_type": "fixed",
  "conditions": {"mission_type": "photo_submission", "event": "mission.approved"},
  "input": {"submission_id": "…", "mission_id": "…"},
  "output": {"points": 10},
  "is_sample": true
}
```

The UI renders this under «چرا این امتیاز؟» on the submission page.

## Sales records — SAMPLE per-amount rule

`award_sales_record` scores one validated row of a sales import:

```
points = floor(amount / unit_size) * points_of_active_SALES_AMOUNT_SAMPLE_rule
```

`unit_size` (default 1,000,000) and `points` (default 1) live in `scoring_rule_versions`, so the
formula is configuration, not code. Idempotency key: `sales.record:<record_id>`. Rows below one unit
award nothing and write no event. Rule selection happens at **processing time** (D-005).

## Corrections (reversal events) — D-004

Nothing is ever updated or deleted. A correction is a **new event** with negative points:

| Field | Value |
|---|---|
| `points` | `-original.points` |
| `corrects_event_id` | id of the corrected event |
| `idempotency_key` | `score.reversed:<original_event_id>` |
| `rule_code` / `rule_version_id` | copied from the original (same provenance) |
| `reason` | required free text, written by the admin |
| `explain_json` | `calculation_type='correction'`, `reversal_of`, `reason` |

One transaction writes: the event, a negative `point_transactions` row, the wallet projection,
`outbox_events('score.reversed')`, and `audit_logs('score.reversed', actor=admin)`.

Invariants:

- `ux_score_events_corrects` (partial unique on `corrects_event_id`) makes a second reversal impossible
  at the database level, not just in the UI.
- A correction cannot itself be corrected (`CANNOT_REVERSE_CORRECTION`).
- The wallet may go negative; it is a projection of events (`OD-08`: non-redeemable points).
- The submission keeps `status='approved'`; the correction is a score fact, not a review decision.
- Leaderboard and balance need no special casing: both are sums over `score_events`.

## Test coverage (executed)

`tests/test_scoring.py` + `tests/test_flow.py`:

- exactly one event for a seeded approval; repeated award returns the same event (`created=False`)
- wallet total == ledger total
- explain payload contains rule + version + `is_sample`
- active-version selection after retirement
- HTTP flow: approve → +10 for the visitor, second decision → 409, one event, one audit row, outbox written
- sales: 2.5M + 1M rows → 3 points, wallet +3, second process run creates nothing; sub-unit amount → no event
- reversal: negative event + ledger + wallet + outbox + audit; double reversal 409; reason required;
  admin-only (operator/visitor 403); correction of a correction rejected; org scope enforced;
  `/score` history marks the correction; leaderboard total drops back to 0

Run: `.venv/bin/pytest`. The last recorded result is in `docs/handoffs/current-state.md`; the
tests that cover each function are listed in `docs/agent-guide/code-map.md` §4.

## Not implemented (explicit)

- partial corrections (part of an award), expiry-based reversals, and a correction approval workflow
- tiered/percentage/target/multiplier calculations
- correction of a sales event: the route returns 403 (backlog A2)
- an atomic approve-and-award: the status change and the award are separate transactions (backlog A1)
- recalculation jobs and leaderboard snapshots
- cap/limit rules per period

## Rules that are still `SAMPLE`

All seeded point values (10/15/5/20) are placeholders. They live in `scoring_rule_versions`
and are editable from the admin panel; nothing in code hardcodes them for scoring.
Until OD-04/OD-05 are approved, treat every number as sample data.
