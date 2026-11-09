# Scoring Engine (prototype)

- Status: **IMPLEMENTED** — `app/scoring.py`
- Mode: P · Last updated: 2026-11-09
- Contract source: spec doc 06/06-A + `.agent/playbooks/scoring-and-rules.md`

---

## Contract

```text
Event (what happened) → Rule Version (under which rule) → Score Event (append-only)
        → Point Transaction (ledger) → Wallet Projection (display only) → Leaderboard
```

Implemented event type: `mission.approved` (from an approved submission).
Other proposed event types (`sales.record.imported`, `target.achieved`, `team.performance`) are **not**
implemented; they require OD-04/OD-05 and are backlog items.

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

## Test coverage (executed)

`tests/test_scoring.py` + `tests/test_flow.py`:

- exactly one event for a seeded approval; repeated award returns the same event (`created=False`)
- wallet total == ledger total
- explain payload contains rule + version + `is_sample`
- active-version selection after retirement
- HTTP flow: approve → +10 for the visitor, second decision → 409, one event, one audit row, outbox written

Run: `.venv/bin/pytest` → 18 passed.

## Not implemented (explicit)

- correction/reversal events (`corrects_event_id` column exists, flow does not)
- tiered/percentage/target/multiplier calculations
- sales-record scoring
- recalculation jobs and leaderboard snapshots
- cap/limit rules per period

## Rules that are still `SAMPLE`

All seeded point values (10/15/5/20) are placeholders. They live in `scoring_rule_versions`
and are editable from the admin panel; nothing in code hardcodes them for scoring.
Until OD-04/OD-05 are approved, treat every number as sample data.
