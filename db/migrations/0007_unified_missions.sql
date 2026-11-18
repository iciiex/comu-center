-- 0007 — Unified missions: the `missions` table becomes the single source for the game.
-- Additive only (D-009 PROPOSED). Existing rows keep working: new mission columns default to
-- neutral values (0 XP / 0 coins), no data is deleted or rewritten.
ALTER TABLE missions ADD COLUMN instructions TEXT NOT NULL DEFAULT '';
ALTER TABLE missions ADD COLUMN category TEXT NOT NULL DEFAULT 'customer_visit';
ALTER TABLE missions ADD COLUMN difficulty TEXT NOT NULL DEFAULT 'easy';
ALTER TABLE missions ADD COLUMN estimated_minutes INTEGER NOT NULL DEFAULT 5;
ALTER TABLE missions ADD COLUMN game_xp INTEGER NOT NULL DEFAULT 0;
ALTER TABLE missions ADD COLUMN game_coins INTEGER NOT NULL DEFAULT 0;
ALTER TABLE missions ADD COLUMN requires_evidence INTEGER NOT NULL DEFAULT 1;
ALTER TABLE missions ADD COLUMN updated_at TEXT;

-- Game reward values are frozen when the request is submitted (user amendment 2).
ALTER TABLE submissions ADD COLUMN source TEXT NOT NULL DEFAULT 'web';
ALTER TABLE submissions ADD COLUMN game_xp_snapshot INTEGER;
ALTER TABLE submissions ADD COLUMN game_coins_snapshot INTEGER;

-- Append-only, idempotent game-economy ledger. Never mixed with score_events / point_transactions.
CREATE TABLE IF NOT EXISTS game_reward_events (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL REFERENCES users(id),
    source_type TEXT NOT NULL CHECK (source_type IN ('mission_submission')),
    source_id   TEXT NOT NULL REFERENCES submissions(id),
    mission_id  TEXT NOT NULL REFERENCES missions(id),
    xp          INTEGER NOT NULL CHECK (xp >= 0),
    coins       INTEGER NOT NULL CHECK (coins >= 0),
    created_at  TEXT NOT NULL,
    UNIQUE (source_type, source_id)
);
CREATE INDEX IF NOT EXISTS ix_game_reward_events_user_time
    ON game_reward_events (user_id, created_at DESC, id DESC);
