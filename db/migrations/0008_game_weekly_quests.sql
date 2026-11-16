-- 0008 — Weekly quests (DEMO), claimed on the server. Quest content is a versioned backend catalog
-- (app/game_quests_catalog.json); these rows record each claim once per user, quest and ISO week.
-- Rewards are GAME XP only: organizational points and any money stay in their own ledgers.
CREATE TABLE IF NOT EXISTS game_quest_claims (
    id                TEXT PRIMARY KEY,
    user_id           TEXT NOT NULL REFERENCES users(id),
    week_key          TEXT NOT NULL,
    quest_id          TEXT NOT NULL,
    xp_awarded        INTEGER NOT NULL CHECK (xp_awarded >= 0),
    idempotency_key   TEXT NOT NULL,
    request_sha256    TEXT NOT NULL,
    response_json     TEXT NOT NULL,
    claimed_at        TEXT NOT NULL,
    UNIQUE (user_id, idempotency_key),
    UNIQUE (user_id, week_key, quest_id)
);

CREATE INDEX IF NOT EXISTS ix_game_quest_claims_user_time
    ON game_quest_claims (user_id, claimed_at DESC, id DESC);
