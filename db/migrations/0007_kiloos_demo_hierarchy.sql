-- 0007 — Kiloos demo integration: org hierarchy, brands, targets, sales brand/origin,
-- and the PROPOSED rule used by the sales-driven game mission.
--
-- Everything added here is data-origin aware: rows are tagged 'sample' (synthetic, seeded or
-- imported from a workbook that declares itself SAMPLE) or 'imported' (real file).
-- Nothing here is an approved business policy (see docs/decisions/open-decisions.md OD-13..15).

ALTER TABLE sales_imports ADD COLUMN data_origin TEXT NOT NULL DEFAULT 'imported';
ALTER TABLE sales_imports ADD COLUMN targets_json TEXT;
ALTER TABLE sales_imports ADD COLUMN source_sheet TEXT;
ALTER TABLE sales_records ADD COLUMN brand_code TEXT;
ALTER TABLE sales_records ADD COLUMN data_origin TEXT NOT NULL DEFAULT 'imported';

CREATE TABLE IF NOT EXISTS brands (
    organization_id TEXT NOT NULL REFERENCES organizations(id),
    code            TEXT NOT NULL,
    name            TEXT NOT NULL,
    data_origin     TEXT NOT NULL DEFAULT 'sample',
    PRIMARY KEY (organization_id, code)
);

CREATE TABLE IF NOT EXISTS branches (
    organization_id TEXT NOT NULL REFERENCES organizations(id),
    code            TEXT NOT NULL,
    name            TEXT NOT NULL,
    data_origin     TEXT NOT NULL DEFAULT 'sample',
    PRIMARY KEY (organization_id, code)
);

-- One row per employee that takes part in the hierarchy
-- Organization -> Brand -> Branch -> Manager -> Head -> Supervisor -> Sales representative.
-- The brand axis lives on sales rows and targets (a rep can sell several brands).
CREATE TABLE IF NOT EXISTS employee_positions (
    user_id           TEXT PRIMARY KEY REFERENCES users(id),
    organization_id   TEXT NOT NULL REFERENCES organizations(id),
    employee_code     TEXT NOT NULL,
    position          TEXT NOT NULL
        CHECK (position IN ('management', 'branch_manager', 'supervisor', 'rep')),
    title             TEXT NOT NULL,
    branch_code       TEXT,
    supervisor_id     TEXT REFERENCES users(id),
    branch_manager_id TEXT REFERENCES users(id),
    head_id           TEXT REFERENCES users(id),
    data_origin       TEXT NOT NULL DEFAULT 'sample',
    UNIQUE (organization_id, employee_code)
);

CREATE INDEX IF NOT EXISTS ix_employee_positions_branch
    ON employee_positions (organization_id, branch_code, position);
CREATE INDEX IF NOT EXISTS ix_employee_positions_supervisor
    ON employee_positions (supervisor_id);

CREATE TABLE IF NOT EXISTS sales_targets (
    id              TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id),
    user_id         TEXT NOT NULL REFERENCES users(id),
    brand_code      TEXT NOT NULL,
    period          TEXT NOT NULL CHECK (length(period) = 7),
    amount          NUMERIC NOT NULL CHECK (amount >= 0),
    import_id       TEXT REFERENCES sales_imports(id),
    data_origin     TEXT NOT NULL DEFAULT 'sample',
    updated_at      TEXT NOT NULL,
    UNIQUE (organization_id, user_id, brand_code, period)
);

CREATE INDEX IF NOT EXISTS ix_sales_records_perf
    ON sales_records (organization_id, status, sale_date, user_id);

-- PROPOSED demo rule (NOT approved): completing the "Target Sprint" game mission after the
-- server verified >= 80% attainment of processed sales awards a fixed number of organizational
-- points, once per period. Kept as a SAMPLE rule version so it is visible in explain payloads.
INSERT OR IGNORE INTO scoring_rule_versions
    (id, rule_code, version, calculation_type, points, unit_size,
     effective_from, effective_to, status, is_sample)
VALUES
    ('rule-game-sales-target-80-proposed-v1', 'GAME_SALES_TARGET_80_PROPOSED', 1, 'fixed', 100, 1,
     '2026-01-01T00:00:00+00:00', NULL, 'published', 1);
