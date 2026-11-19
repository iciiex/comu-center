# API Specification (implemented surface)

- Status: **IMPLEMENTED (prototype)** — subset of the target contract in the source spec (doc 07).
- Mode: P · Last updated: 2026-11-18
- Generated route table (guard, CSRF, handler, template, tests): `docs/agent-guide/code-map.md` §2;
  call chain of each route: §3; every error code and where it is raised: §8
- Auth: versioned signed legacy cookie; a URL token is only a legacy demo fallback. Play uses a
  separate opaque cookie and authentication rules ([Play API](kilos-play.md)).
- Response type: HTML pages for the legacy app; `/health` and `/api/v1/game` return JSON.

## Authentication modes

Both demo modes require `KILOOS_ENV=dev` or `test` and a separate random
`KILOOS_DEMO_OPERATOR_KEY` (32+ characters). Use a synthetic dataset and a controlled HTTPS host.

| Legacy surface | `play` (only Play on this host) | `legacy` (explicit isolated Club demo) | `off` (default) / non-dev/test |
|---|---|---|---|
| `GET /`, `GET /login` | `303 /play/` or `303 /play/entrance`, no `s` propagation | Seed picker; only active rows matching the seeded organization, mobiles, names and roles | No picker; verified cookie goes to home, otherwise login responds `401` |
| `POST /demo-login` | `404` | Seed `user_id` only; admin/operator also require `operator_key`, HTTPS or direct loopback | `404` |
| `GET /api/v1/game/demo-users`, `POST /api/v1/game/demo-login` | `404` | Seed visitors only, no mobile numbers or staff sessions | `404` |
| `POST /logout`, `POST /api/v1/game/logout` | `404` — separate Play logout uses `POST /play/action` | Legacy session transport and CSRF unchanged | CSRF-checked verified cookie only |
| Legacy protected pages/APIs | `404`; no legacy DB handle opened | Existing user/role/org guards | Existing guards, cookie only; no prototype login issuer |
| `?s=` / pre-remediation cookie | Ignored / rejected | Versioned HTML session fallback only; old passwordless signatures rejected | Query ignored for HTML and rejected by game BFF; old passwordless signatures rejected |

`/login` redirects before querying any accounts in Play mode; other legacy handlers are not dispatched.
The standard cookie verifier is not an OTP or an identity provider. No production credential issuer is
implemented; OD-01 remains open.

## Session transport (D-002)

`kiloos_session` is `base64url("<user_id>.<issued_at>.<hmac>")`, HttpOnly, and Secure over HTTPS.
The legacy demo and non-demo session signers are separated (`Settings.legacy_session_secret`), so old
pre-remediation cookies and demo tokens cannot verify as non-demo sessions. TTL defaults to 12 hours
(`KILOOS_SESSION_TTL`). Outside the legacy demo, a known development signing key cannot authenticate.

Only in intentionally isolated `legacy` mode does `POST /demo-login` redirect with `?s=<token>`.
That signed token takes precedence over the cookie and travels through internal HTML links and forms
for cookie-blocked previews. **Do not use it on a public host**: URLs can remain in logs and history,
and a previously issued URL is not revoked by clearing the cookie. BFF routes never accept `?s=`.

## CSRF

Every state-changing browser form request (all `POST`s except `/demo-login` and the legacy-demo-only
`/api/v1/game/demo-login`) must carry a hidden `csrf` field whose value is
`HMAC-SHA256(legacy_session_secret, "csrf:" + session_token)`. Login posts enforce origin checks. The game BFF instead accepts this value in
`X-CSRF-Token`; URL session tokens are forbidden on BFF routes. Missing or mismatched → `403`; anonymous
HTML `POST` → `303 /login`, anonymous BFF calls → JSON `401`. Implemented as a route dependency (`csrf_guard`),
so multipart uploads stay intact.

## Rate limiting

`POST /demo-login` and `POST /api/v1/game/demo-login` (legacy demo only) share a per-IP limit controlled by
`KILOOS_LOGIN_RATE_LIMIT` and `KILOOS_LOGIN_RATE_WINDOW` (defaults 10 / 60 seconds). HTML login returns a
`429` page; game login returns JSON `429`. The counter is in-process memory: a demo guard, not a multi-worker limiter.

## Security headers

`X-Content-Type-Options: nosniff` · `Referrer-Policy: no-referrer` · `X-Permitted-Cross-Domain-Policies: none` ·
`Content-Security-Policy: default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; form-action 'self'; base-uri 'self'; frame-ancestors *`.

`X-Frame-Options` / `frame-ancestors` are deliberately permissive because the shared preview embeds the app
in an iframe. Narrow both before real users.

---


## Sales Quest Arena BFF (prototype, separate game economy)

These JSON routes are implemented under `/api/v1/game`; details, content snapshot and frontend integration
requirements are in [`game-bff-alignment.md`](game-bff-alignment.md). Game-state routes require an authenticated
visitor account; anonymous requests receive JSON `401`. `/demo-users` and `/demo-login` are available only in the explicitly opted-in legacy demo.
URL session tokens (`?s=`) are rejected. Mutations require `X-CSRF-Token` from `/bootstrap`; completion additionally
requires `Idempotency-Key`.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/game/demo-users` | Legacy demo only: list active seed visitors (no mobile numbers) |
| POST | `/api/v1/game/demo-login` | Legacy demo only: JSON login, sets HttpOnly cookie + returns CSRF header |
| POST | `/api/v1/game/logout` | CSRF-checked JSON logout |
| GET | `/api/v1/game/bootstrap` | Versioned catalog/config + user game projection + CSRF token |
| GET | `/api/v1/game/progress` | Refresh canonical server-owned game state |
| GET | `/api/v1/game/history?limit=&cursor=` | User-scoped completion history |
| PATCH | `/api/v1/game/profile` | Set display name/avatar |
| PUT/DELETE | `/api/v1/game/missions/{id}/draft` | Save or discard a validated draft |
| POST | `/api/v1/game/missions/{id}/completions` | Validate answers, score server-side, atomically persist and deduplicate |

Game XP/coins are stored in `game_progress` / `game_completions` and never touch organizational `score_events`.
The catalog is pinned to a frontend source commit. The current demo login/session layer is still prototype-only;
the React frontend has not yet been wired to these endpoints.

## Public

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness + mode banner |
| GET | `/login` | See authentication modes above |
| POST | `/demo-login` | Legacy demo form `user_id` (`operator_key` for staff) → sets cookie, `303 → /home?s=<token>` or `/admin/submissions?s=<token>` |
| POST | `/logout` | CSRF-checked; clears cookie, `303 → /login` |

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
| GET | `/admin/submissions?status=submitted\|approved\|rejected&page=N` | Review queue, 20 per page (`KILOOS_QUEUE_PAGE_SIZE`) |
| GET | `/admin/submissions/{id}` | Review screen |
| POST | `/admin/submissions/{id}/review` | Form `decision=approve\|reject`, `reason` |
| POST | `/admin/score-events/{event_id}/reverse` | **admin only**; form `reason` → negative correction event |

- `reject` without `reason` → `409` + error message, nothing changes.
- `approve` is idempotent at the score layer, but the **state machine** rejects a second decision (`409 ALREADY_REVIEWED`).
- Approval creates exactly one `score_event` in the same transaction as the status/audit write
  (see `scoring-engine.md`). A scoring configuration error rolls back and renders a Persian `409`.

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
| GET | `/admin/sales` | Sales import list (status, counts, points) |
| GET | `/admin/sales/sample` | Download the SAMPLE demo workbook (`sales-sample.xlsx`) |
| GET/POST | `/admin/sales/new` · `/admin/sales` | Upload XLSX (multipart `file`) → validates, never scores |
| GET | `/admin/sales/{id}` | Rows, row-level errors, reconciliation |
| POST | `/admin/sales/{id}/process` | Score valid rows; idempotent (`?processed=<new events>`) |

Mission form fields: `title`, `description`, `points` (0–10000), `max_per_user` (1–50),
`starts_on` / `ends_on` (`YYYY-MM-DD`, interpreted as UTC day bounds).

## Error codes (domain layer)

| Code | HTTP | Meaning |
|---|---|---|
| `MAX_ATTEMPTS_REACHED` | 409 | سقف انجام مأموریت |
| `EVIDENCE_REQUIRED` | 422 | شاهد تصویری الزامی |
| `ALREADY_REVIEWED` | 409 | تصمیم دوم روی یک submission |
| `INVALID_DECISION` | 409 | مقدار decision نامعتبر |
| `REASON_REQUIRED` | 409 | رد بدون دلیل |
| `INVALID_DATE` / `INVALID_WINDOW` | 422 | بازه نامعتبر |
| `TITLE_REQUIRED` / `DESCRIPTION_REQUIRED` | 422 | فیلد اجباری |
| `INVALID_POINTS` / `INVALID_MAX` | 422 | محدوده عددی |
| `NOT_DRAFT` | 409 | انتشار مأموریت غیرپیش‌نویس |
| `NO_ACTIVE_RULE_VERSION` | 409 | قانون فعال برای رویداد وجود ندارد؛ تأیید انجام نشد و rollback شد |
| `REASON_REQUIRED` | 409 | اصلاح امتیاز بدون دلیل |
| `ALREADY_REVERSED` | 409 | اصلاح دوم روی همان رویداد |
| `CANNOT_REVERSE_CORRECTION` | 409 | اصلاح یک رویداد اصلاحی |
| `IMPORT_REJECTED` | 409 | پردازش import ردشده |
| `IMPORT_BUSY` / `IMPORT_FAILED` | 409 | پردازش هم‌زمان یا خطای پردازش import |

## Authorization rules

- All queries filter by the caller's `organization_id` (server-side).
- Visitor: own submissions/evidence only.
- Operator: org queue + evidence; **no** mission editing.
- Admin: mission CRUD + publish/archive, score corrections, **and the sales import**; org-scoped.
  Sales import (EP-07) is admin-only by decision (D-005); operators cannot upload or process.
- Correction of an event outside the admin's organization → `403`; unknown event → `404`; no CSRF → `403`.
- Mission events are scoped by mission organization; sales events by the owner user's organization.
  Success redirects to `/submissions/{id}?reversed=1` for missions and `/admin/sales/{import_id}?reversed=1`
  for sales records.

## Known gaps

- No general mobile REST API yet. `/api/v1/game` is a prototype-specific BFF for Sales Quest Arena, not the full planned mobile API.
- `?s=` session transport leaks the token into URLs; demo-only until OD-01 (see D-002).
- Rate limiting and the session store are in-process memory (single worker only).
- Evidence retention exists as a manual command (`python -m app.maintenance purge-evidence`), no scheduler.
- Mission/leaderboard lists are unpaginated (queue is paginated); sales rows are capped at 200 per view.
- Sales import accepts one XLSX contract (SAMPLE) — no column mapping UI, no CSV, no scheduled import.
- No CSP report collector; policy is applied but unmonitored.
