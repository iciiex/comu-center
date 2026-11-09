-- 0003 — sales import (EP-07)
--
-- Contract (SAMPLE until OD-03/OD-04 are approved):
--   external_id, user_external_id, sale_date, sku_code, quantity, amount
--   optional: customer_external_id, branch_code
--
-- Two-step lifecycle: upload validates and stores rows (never scores), then an
-- explicit process step turns valid rows into score events.

ALTER TABLE scoring_rule_versions ADD COLUMN unit_size NUMERIC NOT NULL DEFAULT 1;

CREATE TABLE IF NOT EXISTS sales_imports (
    id              TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id),
    uploaded_by     TEXT NOT NULL REFERENCES users(id),
    file_name       TEXT NOT NULL,
    file_sha256     TEXT NOT NULL,
    status          TEXT NOT NULL
        CHECK (status IN ('uploaded', 'validated', 'processing', 'completed', 'rejected', 'failed')),
    row_count       INTEGER NOT NULL DEFAULT 0,
    valid_count     INTEGER NOT NULL DEFAULT 0,
    invalid_count   INTEGER NOT NULL DEFAULT 0,
    duplicate_count INTEGER NOT NULL DEFAULT 0,
    created_count   INTEGER NOT NULL DEFAULT 0,
    points_sum      NUMERIC NOT NULL DEFAULT 0,
    error_message   TEXT,
    created_at      TEXT NOT NULL,
    finished_at     TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_sales_imports_fingerprint
    ON sales_imports (organization_id, file_sha256);

CREATE TABLE IF NOT EXISTS sales_records (
    id                   TEXT PRIMARY KEY,
    import_id            TEXT NOT NULL REFERENCES sales_imports(id),
    organization_id      TEXT NOT NULL REFERENCES organizations(id),
    row_number           INTEGER NOT NULL,
    external_id          TEXT NOT NULL,
    user_external_id     TEXT NOT NULL,
    user_id              TEXT REFERENCES users(id),
    sale_date            TEXT,
    sku_code             TEXT,
    quantity             NUMERIC,
    amount               NUMERIC,
    customer_external_id TEXT,
    branch_code          TEXT,
    raw_json             TEXT NOT NULL DEFAULT '{}',
    status               TEXT NOT NULL
        CHECK (status IN ('valid', 'invalid', 'duplicate', 'scored')),
    error_code           TEXT,
    error_message        TEXT,
    created_at           TEXT NOT NULL
);

-- Only rows that carry points claim the external id; invalid/duplicate rows are
-- kept (with their row number and message) so the report can show them.
CREATE UNIQUE INDEX IF NOT EXISTS ux_sales_records_external
    ON sales_records (organization_id, external_id)
    WHERE status IN ('valid', 'scored');

CREATE INDEX IF NOT EXISTS ix_sales_records_import
    ON sales_records (import_id, status);

-- Explicit mapping (never guessed from a phone number), SAMPLE rows in the seed.
CREATE TABLE IF NOT EXISTS sales_user_map (
    organization_id  TEXT NOT NULL REFERENCES organizations(id),
    user_external_id TEXT NOT NULL,
    user_id          TEXT NOT NULL REFERENCES users(id),
    created_at       TEXT NOT NULL,
    PRIMARY KEY (organization_id, user_external_id)
);
