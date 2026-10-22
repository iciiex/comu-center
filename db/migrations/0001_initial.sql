-- 0001_initial.sql — PROPOSED initial schema (PostgreSQL 16).
-- Not yet executed by the application. Mirrors the domain contracts in
-- src/invar_comms/domain/. Review with PoC task 2 before first use.
BEGIN;

CREATE TABLE IF NOT EXISTS products (
    product_id  TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS channel_accounts (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_id          TEXT NOT NULL REFERENCES products(product_id),
    channel             TEXT NOT NULL,               -- 'instagram', ...
    channel_account_id  TEXT NOT NULL,               -- platform-side account id
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (product_id, channel, channel_account_id)
);

CREATE TABLE IF NOT EXISTS contacts (
    id                   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_id           TEXT NOT NULL REFERENCES products(product_id),
    channel              TEXT NOT NULL,
    channel_account_id   TEXT NOT NULL,
    external_contact_id  TEXT NOT NULL,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Contact IDs are unique ONLY within one connected account.
    UNIQUE (product_id, channel, channel_account_id, external_contact_id)
);

CREATE TABLE IF NOT EXISTS conversations (
    conversation_id  TEXT PRIMARY KEY,
    product_id       TEXT NOT NULL REFERENCES products(product_id),
    contact_id       BIGINT NOT NULL REFERENCES contacts(id),
    control_state    TEXT NOT NULL DEFAULT 'ai_active'
                     CHECK (control_state IN ('ai_active','handover_requested','human_active')),
    control_version  INTEGER NOT NULL DEFAULT 0,     -- optimistic-concurrency guard
    human_owner_id   TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_conversations_product ON conversations(product_id);

CREATE TABLE IF NOT EXISTS messages (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    schema_version      INTEGER NOT NULL DEFAULT 1,
    product_id          TEXT NOT NULL REFERENCES products(product_id),
    conversation_id     TEXT NOT NULL REFERENCES conversations(conversation_id),
    channel             TEXT NOT NULL,
    channel_account_id  TEXT NOT NULL,
    external_contact_id TEXT NOT NULL,
    external_event_id   TEXT NOT NULL,
    external_message_id TEXT,
    idempotency_key     TEXT NOT NULL UNIQUE,        -- dedupe redeliveries/retries
    direction           TEXT NOT NULL CHECK (direction IN ('inbound','outbound')),
    content_type        TEXT NOT NULL,
    body_text           TEXT NOT NULL DEFAULT '',
    processing_status   TEXT NOT NULL DEFAULT 'received',
    delivery_status     TEXT NOT NULL DEFAULT 'not_applicable',
    correlation_id      TEXT NOT NULL DEFAULT '',
    occurred_at         TIMESTAMPTZ NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_time
    ON messages(conversation_id, occurred_at);

CREATE TABLE IF NOT EXISTS knowledge_documents (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    document_id   TEXT NOT NULL,
    version       INTEGER NOT NULL CHECK (version >= 1),
    product_id    TEXT NOT NULL REFERENCES products(product_id),
    title         TEXT NOT NULL,
    content       TEXT NOT NULL,
    source        TEXT NOT NULL,
    status        TEXT NOT NULL CHECK (status IN ('draft','in_review','approved','retired')),
    sensitivity   TEXT NOT NULL CHECK (sensitivity IN ('public_faq','internal_only','restricted')),
    approved_by   TEXT,
    approved_at   TIMESTAMPTZ,
    valid_from    TIMESTAMPTZ,
    valid_until   TIMESTAMPTZ,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Full-text search first (ADR-0003); pgvector only when justified.
    search_tsv    TSVECTOR GENERATED ALWAYS AS
                  (to_tsvector('simple', coalesce(title,'') || ' ' || coalesce(content,''))) STORED,
    UNIQUE (product_id, document_id, version),
    CHECK (status <> 'approved' OR (approved_by IS NOT NULL AND approved_at IS NOT NULL)),
    CHECK (valid_from IS NULL OR valid_until IS NULL OR valid_until > valid_from)
);
CREATE INDEX IF NOT EXISTS idx_knowledge_search ON knowledge_documents USING GIN(search_tsv);
CREATE INDEX IF NOT EXISTS idx_knowledge_eligibility
    ON knowledge_documents(product_id, status, sensitivity);

CREATE TABLE IF NOT EXISTS audit_events (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_type      TEXT NOT NULL,
    product_id      TEXT NOT NULL REFERENCES products(product_id),
    conversation_id TEXT NOT NULL,
    actor_id        TEXT NOT NULL,
    detail          TEXT NOT NULL DEFAULT '',
    occurred_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_audit_conversation_time
    ON audit_events(conversation_id, occurred_at);

COMMIT;
