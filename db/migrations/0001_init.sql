-- Kiloos Club — prototype schema (SQLite)
-- MODE: P. PostgreSQL/NUMERIC migration is a later, evidence-driven step (ADR-0001, PROPOSED).
-- Invariants:
--   * score_events is append-only: no UPDATE/DELETE in application code.
--   * wallet balance is a projection of score_events + point_transactions.
--   * money/points use NUMERIC affinity, never float.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS organizations (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id               TEXT PRIMARY KEY,
    organization_id  TEXT NOT NULL REFERENCES organizations(id),
    full_name        TEXT NOT NULL,
    mobile           TEXT NOT NULL,
    role             TEXT NOT NULL CHECK (role IN ('visitor', 'operator', 'admin')),
    is_active        INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at       TEXT NOT NULL,
    UNIQUE (organization_id, mobile)
);

CREATE TABLE IF NOT EXISTS missions (
    id               TEXT PRIMARY KEY,
    organization_id  TEXT NOT NULL REFERENCES organizations(id),
    title            TEXT NOT NULL,
    description      TEXT NOT NULL,
    mission_type     TEXT NOT NULL DEFAULT 'photo_submission',
    points           INTEGER NOT NULL DEFAULT 0,
    starts_at        TEXT NOT NULL,
    ends_at          TEXT NOT NULL,
    max_per_user     INTEGER NOT NULL DEFAULT 1,
    requires_review  INTEGER NOT NULL DEFAULT 1 CHECK (requires_review IN (0, 1)),
    status           TEXT NOT NULL CHECK (status IN ('draft', 'active', 'archived')),
    rule_code        TEXT NOT NULL,
    created_at       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scoring_rule_versions (
    id                TEXT PRIMARY KEY,
    rule_code         TEXT NOT NULL,
    version           INTEGER NOT NULL,
    calculation_type  TEXT NOT NULL,
    points            INTEGER NOT NULL,
    effective_from    TEXT NOT NULL,
    effective_to      TEXT,
    status            TEXT NOT NULL CHECK (status IN ('published', 'retired')),
    is_sample         INTEGER NOT NULL DEFAULT 1 CHECK (is_sample IN (0, 1)),
    UNIQUE (rule_code, version)
);

CREATE TABLE IF NOT EXISTS submissions (
    id                TEXT PRIMARY KEY,
    mission_id        TEXT NOT NULL REFERENCES missions(id),
    user_id           TEXT NOT NULL REFERENCES users(id),
    status            TEXT NOT NULL CHECK (status IN ('submitted', 'approved', 'rejected')),
    note              TEXT NOT NULL DEFAULT '',
    request_id        TEXT NOT NULL,
    created_at        TEXT NOT NULL,
    reviewed_at       TEXT,
    reviewed_by       TEXT REFERENCES users(id),
    rejection_reason  TEXT,
    UNIQUE (user_id, request_id)
);

CREATE TABLE IF NOT EXISTS submission_evidences (
    id             TEXT PRIMARY KEY,
    submission_id  TEXT NOT NULL REFERENCES submissions(id),
    file_name      TEXT NOT NULL,
    content_type   TEXT NOT NULL,
    storage_path   TEXT NOT NULL,
    sha256         TEXT NOT NULL,
    created_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS score_events (
    id                TEXT PRIMARY KEY,
    user_id           TEXT NOT NULL REFERENCES users(id),
    source_type       TEXT NOT NULL,
    source_id         TEXT NOT NULL,
    rule_code         TEXT NOT NULL,
    rule_version_id   TEXT NOT NULL REFERENCES scoring_rule_versions(id),
    points            NUMERIC NOT NULL,
    occurred_at       TEXT NOT NULL,
    idempotency_key   TEXT NOT NULL UNIQUE,
    corrects_event_id TEXT REFERENCES score_events(id),
    reason            TEXT,
    explain_json      TEXT NOT NULL,
    created_at        TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_score_events_source
    ON score_events (source_type, source_id, rule_code, rule_version_id)
    WHERE corrects_event_id IS NULL;

CREATE TABLE IF NOT EXISTS point_transactions (
    id              TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL REFERENCES users(id),
    score_event_id  TEXT NOT NULL REFERENCES score_events(id),
    amount          NUMERIC NOT NULL,
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS point_wallets (
    user_id     TEXT PRIMARY KEY REFERENCES users(id),
    balance     NUMERIC NOT NULL DEFAULT 0,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS competitions (
    id               TEXT PRIMARY KEY,
    organization_id  TEXT NOT NULL REFERENCES organizations(id),
    title            TEXT NOT NULL,
    starts_at        TEXT NOT NULL,
    ends_at          TEXT NOT NULL,
    is_sample        INTEGER NOT NULL DEFAULT 1 CHECK (is_sample IN (0, 1))
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id           TEXT PRIMARY KEY,
    actor_id     TEXT,
    action       TEXT NOT NULL,
    entity_type  TEXT NOT NULL,
    entity_id    TEXT NOT NULL,
    detail_json  TEXT NOT NULL DEFAULT '{}',
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS outbox_events (
    id            TEXT PRIMARY KEY,
    event_type    TEXT NOT NULL,
    payload_json  TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    published_at  TEXT
);

CREATE INDEX IF NOT EXISTS ix_submissions_status ON submissions (status, created_at);
CREATE INDEX IF NOT EXISTS ix_score_events_user ON score_events (user_id, occurred_at);
CREATE INDEX IF NOT EXISTS ix_submissions_user_mission ON submissions (user_id, mission_id);
