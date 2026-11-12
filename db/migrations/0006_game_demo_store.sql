-- 0006 — Demo game-store purchase audit, separate from organizational points.
-- Offer inventory/content is a versioned backend catalog; these tables record user purchases.
CREATE TABLE IF NOT EXISTS game_store_purchases (
    id                TEXT PRIMARY KEY,
    user_id           TEXT NOT NULL REFERENCES users(id),
    offer_id          TEXT NOT NULL,
    price_coins       INTEGER NOT NULL CHECK (price_coins >= 0),
    idempotency_key   TEXT NOT NULL,
    request_sha256    TEXT NOT NULL,
    response_json     TEXT NOT NULL,
    created_at        TEXT NOT NULL,
    UNIQUE (user_id, idempotency_key),
    UNIQUE (user_id, offer_id)
);

CREATE TABLE IF NOT EXISTS game_coin_transactions (
    id                TEXT PRIMARY KEY,
    user_id           TEXT NOT NULL REFERENCES users(id),
    amount            INTEGER NOT NULL CHECK (amount <> 0),
    transaction_type  TEXT NOT NULL CHECK (transaction_type IN ('store_purchase')),
    source_id         TEXT NOT NULL REFERENCES game_store_purchases(id),
    created_at        TEXT NOT NULL,
    UNIQUE (transaction_type, source_id)
);

CREATE INDEX IF NOT EXISTS ix_game_store_purchases_user_time
    ON game_store_purchases (user_id, created_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS ix_game_coin_transactions_user_time
    ON game_coin_transactions (user_id, created_at DESC, id DESC);
