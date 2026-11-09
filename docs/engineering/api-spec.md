# API Specification (implemented surface)

- Status: **IMPLEMENTED (prototype)** — subset of the target contract in the source spec (doc 07).
- Mode: P · Last updated: 2026-11-09
- Auth: signed session cookie (`kiloos_session`, HttpOnly, SameSite=Lax). Demo login only (OD-01).
- Response type: HTML pages for the app; `GET /health` returns JSON. Machine-readable schema: `GET /api/docs` (OpenAPI).

> Planned REST surface `POST /api/v1/...` is **not** implemented yet; this document describes what exists so
> the next agent does not invent endpoints or break the contract.

---

## Public

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness + mode banner |
| GET | `/login` | Demo user picker |
| POST | `/demo-login` | Form `user_id` → sets session, 303 to `/home` or `/admin/submissions` |
| POST | `/logout` | Clears session |

`GET /health`:

```json
{"status":"ok","mode":"P","env":"dev","demo_data":true,"message":"Prototype — sample data only"}
```

## Visitor

| Method | Path | Purpose |
|---|---|---|
| GET | `/home` | Wallet, rank, active missions, recent activity |
| GET | `/missions` | Active + eligible missions (BR-001) |
| GET | `/missions/{mission_id}` | Detail + submission form; 404 if not active/eligible |
| POST | `/missions/{mission_id}/submissions` | Multipart: `request_id`, `note`, `evidence` |
| GET | `/submissions/{submission_id}` | Status + evidence + score explanation |
| GET | `/score` | Balance + score history |
| GET | `/leaderboard` | Period leaderboard + my rank |
| GET | `/evidence/{evidence_id}` | Private evidence file (owner or staff, same org) |

### POST /missions/{id}/submissions

- `request_id` (required, client-generated UUID): idempotency key for the user's submit action.
- `note` (≤500 chars), `evidence` (required, `image/jpeg|png|webp`, ≤4 MiB).
- Success: `303 → /submissions/{id}` with status `submitted` (or `approved` when review is not required).
- Errors: `404` mission not eligible · `422` invalid evidence · `409` max attempts reached (BR-002).

## Staff (operator/admin, same organization)

| Method | Path | Purpose |
|---|---|---|
| GET | `/admin/submissions?status=submitted\|approved\|rejected` | Review queue |
| GET | `/admin/submissions/{id}` | Review screen |
| POST | `/admin/submissions/{id}/review` | Form `decision=approve\|reject`, `reason` |

- `reject` without `reason` → `409` + error message, nothing changes.
- `approve` is idempotent at the score layer, but the **state machine** rejects a second decision (`409 ALREADY_REVIEWED`).
- Approval creates exactly one `score_event` (see `scoring-engine.md`).

## Admin (admin only)

| Method | Path | Purpose |
|---|---|---|
| GET | `/admin/missions` | All missions in org |
| GET | `/admin/missions/new` | Create form |
| POST | `/admin/missions/new` | Create draft + rule version 1 |
| GET | `/admin/missions/{id}` | Edit form |
| POST | `/admin/missions/{id}` | Update; points change publishes a new rule version |
| POST | `/admin/missions/{id}/publish` | `draft → active` (409 otherwise) |
| POST | `/admin/missions/{id}/archive` | `→ archived` |

Mission form fields: `title`, `description`, `points` (0–10000), `max_per_user` (1–50),
`starts_on` / `ends_on` (`YYYY-MM-DD`, interpreted as UTC day bounds).

## Error codes (domain layer)

| Code | HTTP | Meaning |
|---|---|---|
| `MAX_ATTEMPTS_REACHED` | 409 | سقف انجام مأموریت |
| `EVIDENCE_REQUIRED` | 422 | شاهد تصویری الزامی |
| `ALREADY_REVIEWED` | 409 | تصمیم دوم روی یک submission |
| `INVALID_DECISION` | 422 | مقدار decision نامعتبر |
| `REASON_REQUIRED` | 409 | رد بدون دلیل |
| `INVALID_DATE` / `INVALID_WINDOW` | 422 | بازه نامعتبر |
| `TITLE_REQUIRED` / `DESCRIPTION_REQUIRED` | 422 | فیلد اجباری |
| `INVALID_POINTS` / `INVALID_MAX` | 422 | محدوده عددی |
| `NOT_DRAFT` | 409 | انتشار مأموریت غیرپیش‌نویس |
| `NO_ACTIVE_RULE_VERSION` | 500 | قانون فعال برای رویداد وجود ندارد (خطای پیکربندی) |

## Authorization rules

- All queries filter by the caller's `organization_id` (server-side).
- Visitor: own submissions/evidence only.
- Operator: org queue + evidence; **no** mission editing.
- Admin: mission CRUD + publish/archive; org-scoped.

## Known gaps

- No REST/JSON API for mobile clients yet (planned `/api/v1`, `Idempotency-Key` header).
- No CSRF token beyond `SameSite=Lax` cookies; required before real users.
- No pagination; queues are org-sized (prototype scale only).
