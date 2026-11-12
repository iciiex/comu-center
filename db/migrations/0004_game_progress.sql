-- 0004 — Sales Quest Arena game state (separate from organizational score ledger)
-- Game XP/coins are sample game progression and never create score_events.
CREATE TABLE IF NOT EXISTS game_progress (
    user_id     TEXT PRIMARY KEY REFERENCES users(id),
    state_json  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS game_completions (
    id               TEXT PRIMARY KEY,
    user_id          TEXT NOT NULL REFERENCES users(id),
    mission_id       TEXT NOT NULL,
    idempotency_key  TEXT NOT NULL,
    request_sha256   TEXT NOT NULL,
    response_json    TEXT NOT NULL,
    completed_at     TEXT NOT NULL,
    UNIQUE (user_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS ix_game_completions_user_time
    ON game_completions (user_id, completed_at DESC, id DESC);
