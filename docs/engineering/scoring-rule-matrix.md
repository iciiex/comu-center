# Scoring Rule Matrix (working)

- Status: **SAMPLE** — no rule is approved.
- Mode: P

| Rule code | Event | Calculation | Sample points | Status |
|---|---|---|---|---|
| `MISSION_SAMPLE_01` | mission.approved (photo) | fixed | 10 | SAMPLE |
| `MISSION_SAMPLE_02` | mission.approved (photo) | fixed | 15 | SAMPLE |
| `MISSION_SAMPLE_03` | mission.approved (photo, expired demo) | fixed | 5 | SAMPLE |
| `MISSION_SAMPLE_04` | mission.approved (draft demo) | fixed | 20 | SAMPLE |

Implemented: `fixed`. Proposed but not implemented: `per_unit`, `percentage`, `target_achievement`,
`tiered`, `multiplier`.

Weighting proposal from doc 06-A (missions 20% / sales 50% / target 20% / special 10%) is **PROPOSED**
and not applied anywhere in code.

Before implementation of any new rule: decision in the decision log + golden test case.
