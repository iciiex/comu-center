# Sales Quest Arena — Backend-for-Frontend Alignment

- Status: **PARTIALLY IMPLEMENTED (prototype)** — read/bootstrap, profile, draft, progress, history, completion and demo game-store routes exist; frontend integration remains separate.
- Mode: P · Updated: 2026-11-12
- Frontend reviewed: public `mrkavousi/sales-quest-arena`, branch `main`.
- Related: [`api-spec.md`](api-spec.md), [`backlog.md`](../delivery/backlog.md), [open decisions](../decisions/open-decisions.md).

## Agreement for this integration

1. The backend is authoritative for game progress and rewards. The browser submits answers, never an authoritative `PlayerProgress`, XP, coin, level, streak, or achievement result.
2. Game XP/coins are a separate game economy and **must not write to** the existing organizational `score_events`, wallet, or sales ledger. Those remain governed by Kiloos mission approval and sales import.
3. Current Sales Quest reward/level values (100 XP + 20 coins per completion, +50 daily, +30 order, level thresholds) are game-source defaults, not approved business policy. Keep them labelled SAMPLE/configurable until product approval.

## Frontend facts and compatibility gap

The game is a React 18 + TypeScript + Vite app. Its pure logic and models live under `src/game/`; `src/state/GameContext.tsx` calls `completeMission()` in the browser and persists the resulting object through `src/game/storage.ts` to `localStorage` (`sales-quest-arena:progress:v1`). Missions, step schemas, rewards, unlock rules, levels, streak and achievements are static client code.

The README suggests replacing three storage functions with API calls, but the current seam is synchronous: `loadProgress()` is called in a lazy `useState` initializer, and `saveProgress()`/`clearProgress()` return booleans synchronously. A network-backed integration therefore also needs an async boot/loading state and async mutation/error handling in the frontend; swapping only those three implementations is insufficient. `finishMission()` currently runs the reward engine client-side, so this path must be changed to consume the server's completion response.

The existing FastAPI app is a server-rendered prototype with a demo-user picker and a different mission model (mission + evidence submission + operator review + organizational points). It does not have `/api/v1`, game XP/coin state, or the frontend's multi-step mission schemas. Do not silently map an Arena game completion to an approved Kiloos mission or a sales score event.

## API contract (same-origin BFF)

The versioned content snapshot lives at `app/game_catalog.json`, pinned to frontend commit
`7de8a5a0a0da…`. It contains the six mission definitions, step/option allowlists, categories, reward/level
configuration and achievement metadata. Refresh it only as an intentional contract update, then update its
source SHA and tests.

All routes are under `/api/v1/game`. Game-state routes require a visitor session (anonymous calls receive JSON `401`); demo-user selection/login is explicitly public but dev/test-only and rate-limited. Implemented routes: The frontend should call relative URLs; deploy behind the same origin or a same-origin reverse proxy. Use the existing signed session cookie for identity. JSON requests must receive JSON `401` (not the HTML `/login` redirect), and state changes require CSRF validation. Do not put session tokens in URLs or localStorage.

| Method + route | Purpose | Contract notes |
|---|---|---|
| `GET /demo-users` | List active visitor accounts for the demo picker | Dev/test only; hides mobile numbers. |
| `POST /demo-login` | JSON `{user_id}` login, sets HttpOnly session cookie and returns CSRF header | Dev/test only; rate-limited; does not accept roles or arbitrary identity fields. |
| `POST /logout` | Clear the session cookie | Requires CSRF and a visitor session. |
| `GET /bootstrap` | One-request startup payload: player profile, current progress, game config, mission content, server date key, CSRF token | Requires session; response has `api_version` and `content_version`. Missions/config are server-owned snapshots to prevent frontend/backend rule drift. |
| `PATCH /profile` | Save onboarding/profile `{name, avatar}` | Allowlisted avatar IDs, name length ≤24; identity always comes from session. |
| `PUT /missions/{mission_id}/draft` | Save resumable draft `{step_index, answers}` | Validate mission and step IDs/types; scoped to current user. |
| `DELETE /missions/{mission_id}/draft` | Discard draft | Idempotent. |
| `POST /missions/{mission_id}/completions` | Complete a run `{answers}` with required `Idempotency-Key` | Server checks unlock/completion rules, computes rewards, progression, streak, daily challenge, levels and achievements in one transaction; replay returns the original completion response and awards nothing twice. |
| `GET /history?limit=&cursor=` | Paginated completion history | Newest first; user-scoped. |
| `GET /progress` | Refresh the canonical progress projection | User-scoped; useful after reconnect/multi-tab changes. |
| `GET /store` | List demo store offers and current game coin balance | User-scoped; currency is `game_coins`; offers are explicitly sample/demo. |
| `POST /store/purchases` | Purchase one offer `{offer_id}` with `Idempotency-Key` | CSRF-protected and atomic; deducts game coins and unlocks its special mission once. No Kiloos points or Tribal ledger writes. |

The demo store is intentionally small and temporary: two sample special missions cloned from existing mission schemas,
priced at 40 and 60 game coins. Purchase rows and negative coin transactions are auditable and unique per user/offer;
retries with the same key replay the result. The original six mission list remains unchanged; purchased missions are
returned separately as `special_missions`. No real-money, inventory, redemption fulfillment, or cash-out behavior exists.

### Completion request / response sketch

```http
POST /api/v1/game/missions/customer-visit-challenge/completions
Idempotency-Key: <client-generated UUID>
Content-Type: application/json
X-CSRF-Token: <token from bootstrap>

{"answers":{"customer_type":"new","outcome":"order_received","rating":5,"note":"Call Friday"}}
```

Success returns the persisted completion/history entry and the canonical updated progress, including reward lines and level/achievement changes. Reuse of a key with a different request body returns `409 IDEMPOTENCY_KEY_REUSED`; repeating the same request returns the original result. Validation errors are JSON `422`, locked/unknown mission or invalid game state are stable JSON `409`/`404`, anonymous requests are JSON `401`, and cross-user data access is `404`.

### Persistence boundary

Use separate game tables/projections (suggested: `game_player_profiles`, `game_progress`, `game_completions`, `game_idempotency`) keyed by `users.id`; never accept a whole client-supplied state document as a write. Keep an append-only completion record and update a projection transactionally. Organizational points remain entirely separate. Use SQLite-safe atomic transactions and add migration/indexes with tests before exposing writes.

## Source-to-contract mapping

| Frontend concept | Server responsibility |
|---|---|
| `Mission` / `MissionStep` / `requiredSteps` | Serve a versioned canonical mission catalog; validate IDs, types, option IDs and required answers against it. |
| `PlayerProgress.player` | Persist editable game display name/avatar for the signed-in user; account identity and role remain server-owned. |
| `drafts` | Save only a validated per-user draft, not reward state. |
| `completeMission()` | Port the reward/progression rules to backend-owned logic; client receives server result and replaces local projection. |
| `xp`, `coins`, `streak`, `daily`, `missions`, `achievements`, `history` | Server-derived projection; never client-authoritative. |
| `GAME_CONFIG` | Server-served versioned config; initial values remain SAMPLE pending business approval. |
| `localStorage` | Migration/fallback only during transition. Do not upload/import arbitrary saved XP as authoritative. |
| Kiloos `score_events` / sales scoring | Separate domain. No implicit bridge from game XP/coins. |

## Delivery sequence / acceptance

1. **DONE (backend):** freeze/version the six-mission config snapshot from frontend commit `7de8a5a0a0da…`.
2. **DONE (backend):** add game tables, server-side validators/reward engine and transaction/idempotency tests.
3. **DONE (backend):** add JSON auth/CSRF/error handling and read routes; enforce visitor role and per-user scoping.
4. **DONE (backend):** add profile/draft/completion writes; test daily bonus once, replay, unlocks, invalid answers and ledger separation.
5. **OPEN (frontend):** update React app for async boot/loading, demo identity selection or another approved auth flow, API client,
   server-owned finish response, retry/error states and E2E coverage.
6. **OPEN (integration):** run cross-repository contract/E2E tests; only then disable localStorage as the source of truth.

DoD for the integrated slice: contract version is explicit; server ignores/rejects client-supplied reward/progression fields; completion is atomic and idempotent; unauthenticated/CSRF/invalid/unlocked/cross-user cases have tested JSON responses; XP/coins do not affect Kiloos points; frontend reload/resume/retry works against the API; docs and current-state handoff record executed test results.

## Not decided / not included

- Production login (OD-01), real org/team model, live CRM-verified visits/orders, approved reward economics and competition rules are not settled by this integration.
- A client-reported `order_received` choice is an in-game claim, not verified sales evidence. It must not award organizational sales points.
- This contract does not implement admin configuration, team competitions, notifications, or production deployment.
