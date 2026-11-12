# Tribal Gamification API Contract (proposal)

- Status: **PROPOSED — design review only; implemented backend subset: fail-closed bootstrap sentinel plus tenant-scoped read-only organization-unit list/detail. No write/data-management endpoints exist.**
- API base: `/api/v1/tribal` (same-origin BFF; cookie session + CSRF; JSON only).
- Depends on: [`tribal-gamification-plan.md`](../architecture/tribal-gamification-plan.md).
- Time rules: server stores UTC instants; campaign/day boundaries use `Asia/Tehran`.
- Feature flag: `KILOOS_TRIBAL_GAMIFICATION_ENABLED`, default OFF, process-configured (not yet admin-managed). The authenticated `GET /api/v1/tribal/bootstrap` sentinel returns JSON 404 `FEATURE_DISABLED` while off and JSON 503 `MODULE_NOT_CONFIGURED` while on. This is only a fail-closed gate; it does not imply that any Tribal API/data/authz contract is deployed. Other Tribal endpoints do not exist yet.

This contract deliberately describes route families and stable semantics, not the unresolved metric DSL or final import columns. Freeze concrete OpenAPI schemas only after the data owners and scoring rules are approved.

## 1. Shared contract

### Authentication and security

- All user/module routes require an authenticated active user; identity is derived from the session, never a client-supplied user ID.
- Use first-party HttpOnly cookie sessions. Never put session tokens in query parameters, URL fragments, localStorage or offline queue payloads.
- State-changing JSON requests require CSRF (`X-CSRF-Token`) and an `Idempotency-Key` for report/import/review operations that can be retried.
- Existing dev/test demo login is not a production authentication contract.
- Every response is tenant- and membership-scoped server-side. The UI cannot elevate roles by sending role/unit IDs.
- Enforce `tribal_gamification` server-side for every endpoint, not only navigation.

### Common response/error format

Success uses JSON. Proposed error envelope:

```json
{
  "error": {
    "code": "MISSION_LOCKED",
    "message": "This mission is not available to your membership.",
    "request_id": "server-correlation-id",
    "fields": {}
  }
}
```

Use stable machine-readable codes; messages may be localized by frontend. Expected statuses: `400` malformed request, `401` unauthenticated, `403` authenticated but unauthorized, `404` unknown or deliberately concealed out-of-scope resource, `409` invalid state/version/idempotency conflict, `413` import too large, `422` field/business validation, `429` throttled.

### Common resource conventions

- IDs are opaque stable strings; imported records also retain `source_system` + `external_id`.
- `version` / `etag` on mutable configuration for optimistic concurrency; stale update → `409 VERSION_CONFLICT`.
- `created_at`, `received_at`, `approved_at` are RFC3339 UTC instants. `business_date`/period is computed on server using `Asia/Tehran`, not the device clock.
- Lists are paginated (`limit`, opaque `cursor`); defaults/maxima are policy settings, not frontend assumptions.
- Ranking DTOs include only fields allowed by effective visibility policy.

## 2. Player and organization reads

| Method + path | Auth/scope | Response purpose |
|---|---|---|
| `GET /bootstrap` | Active member | `api_version`, feature/config version, server time/timezone, own memberships/roles/capabilities, display labels, visibility policy, pending sync/review counts and links to enabled module sections |
| `GET /me/memberships` | Self | Current and, if permitted, historical unit membership(s), scoped roles and validity windows |
| `GET /org-units?parent_id=&type=&q=` | Units visible to caller | Search/tree children; returns configured display labels, counts only if policy allows, cursor |
| `GET /org-units/{unit_id}` | Unit scope | Clan/unit profile with permitted name/flag/area/manager/count/rank/score/campaigns/badges |
| `GET /org-units/{unit_id}/members?cursor=` | Unit scope + visibility policy | Visible members; default public fields are name, avatar, points, rank only |

A unit ID in the URL is a selector, not proof of permission. Cross-tenant/sibling access must be rejected or concealed consistently.

## 3. Campaigns and mission runs

| Method + path | Auth/scope | Response/purpose |
|---|---|---|
| `GET /campaigns?status=&unit_id=&cursor=` | Audience membership | Visible active/past campaigns and campaign version |
| `GET /campaigns/{campaign_id}` | Campaign audience | Campaign overview, Tehran period, applicable missions and current progress |
| `GET /missions?campaign_id=&scope=&cursor=` | Assignment/audience | Mission versions available to caller; schemas/selectors and review expectation |
| `POST /mission-runs` | Assigned member | Create/resume a run for a published mission version; `Idempotency-Key` required |
| `PUT /mission-runs/{run_id}` | Run owner | Save validated draft answers; no score/approval is created |
| `POST /mission-runs/{run_id}/submit` | Run owner | Submit completed answers; server stamps `received_at`, checks version/required reference IDs and moves to `pending_review` |
| `GET /mission-runs/{run_id}` | Owner or permitted reviewer | Run state, submitted values, review state and permitted feedback |
| `POST /mission-runs/{run_id}/review` | Admin or scoped supervisor reviewer | `{decision: approve|reject, reason?}`; approve/reject, audit and any score award are one transaction |
| `GET /me/mission-runs?status=&cursor=` | Self | Own drafts, pending sync confirmations, pending review, approved/rejected reports |

### Offline queue semantics

The PWA retains unsent reports in a durable local outbox with a client-generated stable ID. On reconnect it submits each item with that value as `Idempotency-Key`; a successful response returns the server run ID and `received_at`. Replaying the same key/body returns the existing result; same key/different body → `409 IDEMPOTENCY_KEY_REUSED`.

A client-provided `completed_at` may be included for display/audit context only. It does not determine campaign day, streak, eligibility or award. `received_at` in the server response determines the Tehran business date. UI states must distinguish local `pending_sync` from server `pending_review` and final `approved`/`rejected`. No provisional client score is authoritative.

### Selectors and validation

Mission form schema can expose allowed selectors such as `product_id`, `price_list_id`, `customer_id`, quantity, visit outcome and note. The server validates IDs against active tenant/source data, effective dates, mission version and caller scope. Invalid or stale references produce field-level `422` errors; the frontend must not submit labels as trusted identifiers. The exact fields and verification source belong to each approved mission version.

## 4. Review workload

| Method + path | Auth/scope | Purpose |
|---|---|---|
| `GET /reviews?unit_id=&status=pending_review&cursor=` | Admin or assigned supervisor | Work queue for only authorized organizational scopes |
| `GET /reviews/{run_id}` | Same reviewer scope | Review detail and source references |
| `POST /mission-runs/{run_id}/review` | Same reviewer scope | Approval/rejection; append-only review history, decision reason, actor and time |

Unauthorized reviewer → `403` (or concealed `404` according to approved resource-existence policy). Second review, review of non-pending run or stale version → `409`. Self-approval is recommended to be forbidden but awaits explicit policy confirmation.

On approval, award creation, run status, audit and outbox event must commit atomically. Rejection creates no award. If the same request is replayed, do not create duplicate review or score events.

## 5. League and ranking reads

| Method + path | Auth/scope | Purpose |
|---|---|---|
| `GET /leagues?unit_id=&cursor=` | Member visibility | League definitions currently visible to user |
| `GET /leagues/{league_id}` | League audience | League settings summary, current period and allowed metric explanations |
| `GET /leagues/{league_id}/rankings?subject_type=&unit_id=&cursor=` | Visibility policy + scope | Paged ranked subjects; only permitted player/unit fields |
| `GET /leagues/{league_id}/rankings/me` | Self | Caller rank and metric breakdown when eligible |
| `GET /leagues/{league_id}/periods/{period_id}/breakdown/{subject_id}` | Visibility policy + scope | Auditable components and rule-set version, not just a total |

Admin wizard writes are below. Ranking reads must be backed by period snapshots or indexed aggregates once query-plan/load tests show the need; this design does not assume the current on-read legacy leaderboard can serve Tribal metrics.

## 6. Badges and achievements

| Method + path | Auth/scope | Purpose |
|---|---|---|
| `GET /me/badges` | Self | Earned/eligible personal badges with award time and source |
| `GET /org-units/{unit_id}/badges` | Unit scope + visibility | Unit awards and achievements |

Awards are server-evaluated, versioned and idempotent. The UI displays the backend definition/translation key and provenance; it does not unlock badges client-side.

## 7. Admin/back-office APIs

All writes require admin capability or explicitly granted scoped-management capability; all are audited and version-checked.

| Method + path family | Purpose |
|---|---|
| `/admin/imports` | Create upload batch, inspect validation report, preview rows, confirm/cancel import; supports versioned Excel templates for users/units/memberships/products/customers/price lists/targets |
| `/admin/org-unit-types`, `/admin/org-units` | Configure hierarchy types/display labels, create/edit/disable units, centrally manage names/flags and effective memberships |
| `/admin/roles`, `/admin/role-assignments`, `/admin/visibility-policies` | Grant scoped reviewer/manager permissions and configure visible fields/scopes |
| `/admin/campaigns`, `/admin/campaigns/{id}/versions` | Draft/publish/archive campaign versions, period, targets and audience |
| `/admin/missions`, `/admin/missions/{id}/versions` | Configure scope, structured fields/selectors, validation, reviewer requirement and mission content |
| `/admin/scoring/metric-catalog`, `/admin/scoring/rule-sets` | Choose allowed metrics, set configurable weights/normalization, validate required input availability, preview then publish version |
| `/admin/leagues`, `/admin/leagues/{id}/periods` | Guided league definition: subjects, campaign/period, scoring rule set, eligible units, visibility, optional movement policy |
| `/admin/badges` | Configure badge definitions and versioned criteria |
| `/admin/feature-flags/tribal-gamification` | Enable/disable module; audited; disabled means APIs reject even if directly called |

Do not expose arbitrary code/formula fields or unrestricted SQL in the scoring wizard. Only approved backend metric implementations can be selected.

## 8. Proposed DTO outlines

### Bootstrap

```json
{
  "api_version": "1",
  "feature": {"enabled": true, "config_version": "..."},
  "server_time": "...Z",
  "timezone": "Asia/Tehran",
  "player": {"id": "...", "display_name": "...", "avatar": "..."},
  "memberships": [{"unit_id": "...", "unit_label": "...", "role_labels": ["..."]}],
  "capabilities": ["tribal.read", "mission.submit"],
  "visibility": {"player_fields": ["name", "avatar", "points", "rank"], "scope": "organization"},
  "pending": {"sync": 0, "review": 0}
}
```

### Submitted mission report

```json
{
  "run_id": "...",
  "mission_id": "...",
  "mission_version": 1,
  "status": "pending_review",
  "received_at": "...Z",
  "business_date": "YYYY-MM-DD",
  "review_scope_id": "...",
  "score_status": "not_awarded"
}
```

`review_scope_id` is server-derived, not trusted from request payload. API fields and exact statuses are subject to review before OpenAPI is frozen.

## 9. Frontend route/screen proposal

Keep current `#/arena`, `#/missions`, `#/history`, `#/profile`, `#/play` intact. Add a gated `#/tribal` module with overview, organization tree, unit/clan profile, campaigns/missions, review queue for authorized reviewers, league wizard for admins, rankings and badges. Use server-returned capabilities for affordances, but rely on API authorization. Preserve current localStorage game save; Tribal outbox uses a separate durable store and a visible pending/retry/reject state.

## 10. Contract review gates (before implementation)

- Approve conceptual ERD and table ownership; map the existing `users.organization_id` model to imported memberships without forced/destructive migration.
- Freeze Excel template versions and stable external key rules; identify source systems and data owners.
- Approve each mission's validation fields/source and supervisor scope/self-approval policy.
- Specify metric definitions, formula inputs, weights, period, missing-data/zero-denominator behavior, tie-break and correction policy.
- Specify league period and promotion/relegation semantics, even if a first league disables movement.
- Approve visible fields/scope controls, customer-data retention and feature flag ownership.
- Confirm offline server-receipt attribution and no official client-side award.

Until these gates pass, every route/table/formula above remains a proposal and must not be treated as a deployed API contract.
