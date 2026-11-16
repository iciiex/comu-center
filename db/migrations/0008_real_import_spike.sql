-- 0008 — real-workbook import SPIKE (branch real-import-spike). New tables only (prefix ri_).
--
-- Nothing here touches sales_records / score_events / point_transactions / game state:
-- XP, organizational points and monetary rewards stay separate (rule 9), and there is no
-- settlement or payment structure (rule 10). Quantities are cartons stored as TEXT decimals
-- (exact, fractional and negative values preserved). Every business rule lives in data and is
-- PROPOSED or UNCONFIRMED; the CHECK constraints below intentionally do not allow 'APPROVED'
-- (approval needs the business owner and a later migration).

-- ------------------------------------------------------------------ 1. raw layer
CREATE TABLE IF NOT EXISTS ri_workbooks (
    id              TEXT PRIMARY KEY,
    sha256          TEXT NOT NULL UNIQUE,
    file_name       TEXT NOT NULL,
    size_bytes      INTEGER NOT NULL,
    storage_path    TEXT NOT NULL,
    inspection_json TEXT NOT NULL,
    data_origin     TEXT NOT NULL CHECK (data_origin IN ('synthetic', 'real')),
    uploaded_by     TEXT REFERENCES users(id),
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ri_import_batches (
    id              TEXT PRIMARY KEY,
    workbook_id     TEXT NOT NULL REFERENCES ri_workbooks(id),
    period_calendar TEXT NOT NULL DEFAULT 'jalali' CHECK (period_calendar = 'jalali'),
    period_year     INTEGER NOT NULL,
    period_month    INTEGER NOT NULL CHECK (period_month BETWEEN 1 AND 12),
    config_json     TEXT NOT NULL,
    config_hash     TEXT NOT NULL,
    status          TEXT NOT NULL CHECK (status IN ('inspected', 'validated', 'confirmed', 'failed')),
    counts_json     TEXT NOT NULL DEFAULT '{}',
    data_origin     TEXT NOT NULL CHECK (data_origin IN ('synthetic', 'real')),
    created_at      TEXT NOT NULL,
    validated_at    TEXT,
    confirmed_at    TEXT,
    UNIQUE (workbook_id, config_hash)
);

CREATE TABLE IF NOT EXISTS ri_raw_rows (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id   TEXT NOT NULL REFERENCES ri_import_batches(id),
    sheet      TEXT NOT NULL,
    row_number INTEGER NOT NULL,
    row_hash   TEXT NOT NULL,
    raw_json   TEXT NOT NULL,
    UNIQUE (batch_id, sheet, row_number)
);

-- ------------------------------------------------------------ 2. normalised dimensions
-- Each dimension keeps the source spelling next to the normalised matching key.
CREATE TABLE IF NOT EXISTS ri_branches (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    norm_key      TEXT NOT NULL UNIQUE,
    source_value  TEXT NOT NULL,
    variants_json TEXT NOT NULL DEFAULT '[]'
);
CREATE TABLE IF NOT EXISTS ri_brands (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    norm_key      TEXT NOT NULL UNIQUE,
    source_value  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ri_sales_lines (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    norm_key      TEXT NOT NULL UNIQUE,
    source_value  TEXT NOT NULL,
    variants_json TEXT NOT NULL DEFAULT '[]'
);
CREATE TABLE IF NOT EXISTS ri_customer_groups (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    norm_key       TEXT NOT NULL UNIQUE,
    source_value   TEXT NOT NULL,
    main_group     TEXT,                       -- retail | wholesale | horeca | NULL (unmapped)
    mapping_status TEXT NOT NULL DEFAULT 'UNCONFIRMED' CHECK (mapping_status IN ('UNCONFIRMED', 'PROPOSED'))
);
CREATE TABLE IF NOT EXISTS ri_skus (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    code           TEXT NOT NULL UNIQUE,
    name_source    TEXT,
    brand_id       INTEGER REFERENCES ri_brands(id),
    carton_factor  TEXT,
    factor_status  TEXT NOT NULL DEFAULT 'UNCONFIRMED' CHECK (factor_status IN ('UNCONFIRMED', 'PROPOSED'))
);
-- Customers and employees are personal data: source value stays here, the API shows pseudonyms only.
CREATE TABLE IF NOT EXISTS ri_customers (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    norm_key      TEXT NOT NULL UNIQUE,
    source_value  TEXT NOT NULL,
    pseudonym     TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ri_employees (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    person_key       TEXT NOT NULL UNIQUE,     -- normalised personnel code + branch (NOT a visitor key)
    personnel_code   TEXT NOT NULL,
    display_source   TEXT,
    pseudonym        TEXT NOT NULL
);
-- A visitor assignment is one roster row (visitor key). One employee may have several.
CREATE TABLE IF NOT EXISTS ri_visitor_assignments (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id            TEXT NOT NULL REFERENCES ri_import_batches(id),
    visitor_key_source  TEXT NOT NULL,
    visitor_key_norm    TEXT NOT NULL,
    pseudonym           TEXT NOT NULL,
    employee_id         INTEGER REFERENCES ri_employees(id),
    branch_id           INTEGER REFERENCES ri_branches(id),
    sales_line_id       INTEGER REFERENCES ri_sales_lines(id),
    seller_type_source  TEXT,
    seller_type_norm    TEXT,
    supervisor_code     TEXT,
    head_code           TEXT,
    is_active           INTEGER,
    hire_date_source    TEXT,
    UNIQUE (batch_id, visitor_key_norm)
);
CREATE INDEX IF NOT EXISTS ix_ri_va_employee ON ri_visitor_assignments (employee_id);

CREATE TABLE IF NOT EXISTS ri_sales_facts (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id            TEXT NOT NULL REFERENCES ri_import_batches(id),
    source_sheet        TEXT NOT NULL,
    raw_row_id          INTEGER NOT NULL REFERENCES ri_raw_rows(id),
    business_key_hash   TEXT NOT NULL,
    dup_ordinal         INTEGER NOT NULL DEFAULT 0,
    period_year         INTEGER NOT NULL,
    period_month        INTEGER NOT NULL,
    branch_id           INTEGER REFERENCES ri_branches(id),
    visitor_assignment_id INTEGER REFERENCES ri_visitor_assignments(id),
    visitor_key_norm    TEXT,
    customer_group_id   INTEGER REFERENCES ri_customer_groups(id),
    sales_line_id       INTEGER REFERENCES ri_sales_lines(id),
    customer_id         INTEGER REFERENCES ri_customers(id),
    brand_id            INTEGER REFERENCES ri_brands(id),
    sku_id              INTEGER REFERENCES ri_skus(id),
    gross_cartons       TEXT,
    net_cartons         TEXT,
    invoice_count       INTEGER,
    status              TEXT NOT NULL CHECK (status IN ('valid', 'rejected')),
    issues_json         TEXT NOT NULL DEFAULT '[]',
    UNIQUE (batch_id, source_sheet, business_key_hash, dup_ordinal)
);
CREATE INDEX IF NOT EXISTS ix_ri_facts_agg ON ri_sales_facts (batch_id, source_sheet, status, brand_id, branch_id);

-- ------------------------------------------------------- 3. organisational mappings
CREATE TABLE IF NOT EXISTS ri_branch_group_schemes (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    code    TEXT NOT NULL UNIQUE,
    title   TEXT NOT NULL,
    source  TEXT NOT NULL,
    status  TEXT NOT NULL DEFAULT 'UNCONFIRMED' CHECK (status IN ('UNCONFIRMED', 'PROPOSED'))
);
CREATE TABLE IF NOT EXISTS ri_branch_group_members (
    scheme_id  INTEGER NOT NULL REFERENCES ri_branch_group_schemes(id),
    branch_id  INTEGER NOT NULL REFERENCES ri_branches(id),
    group_code TEXT NOT NULL,
    PRIMARY KEY (scheme_id, branch_id)
);
CREATE TABLE IF NOT EXISTS ri_mapping_issues (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id    TEXT NOT NULL REFERENCES ri_import_batches(id),
    issue_type  TEXT NOT NULL,
    severity    TEXT NOT NULL CHECK (severity IN ('info', 'warning', 'error')),
    entity_ref  TEXT NOT NULL,                 -- pseudonym or non-personal code, never a raw name
    detail_json TEXT NOT NULL DEFAULT '{}',
    status      TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'resolved')),
    UNIQUE (batch_id, issue_type, entity_ref)
);

-- ------------------------------------------------------- 4. targets and achievement
CREATE TABLE IF NOT EXISTS ri_targets (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id      TEXT NOT NULL REFERENCES ri_import_batches(id),
    brand_id      INTEGER NOT NULL REFERENCES ri_brands(id),
    org_level     TEXT NOT NULL,
    entity_key    TEXT NOT NULL,               -- e.g. "<branch norm>|<line norm>" for branch managers
    target_cartons TEXT NOT NULL,
    source        TEXT NOT NULL,               -- workbook_hardcoded:<sheet> | manual
    status        TEXT NOT NULL DEFAULT 'UNCONFIRMED' CHECK (status IN ('UNCONFIRMED', 'PROPOSED')),
    extra_json    TEXT NOT NULL DEFAULT '{}',  -- per-entity parameters read from the workbook (e.g. ladder amounts)
    UNIQUE (batch_id, brand_id, org_level, entity_key)
);

-- ------------------------------------------------------------------ 5. calculation
CREATE TABLE IF NOT EXISTS ri_rule_sets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    code        TEXT NOT NULL,
    version     INTEGER NOT NULL,
    rule_type   TEXT NOT NULL,
    org_level   TEXT NOT NULL,
    brand_code  TEXT NOT NULL,
    params_json TEXT NOT NULL,                 -- immutable once referenced by a run
    status      TEXT NOT NULL CHECK (status IN ('PROPOSED', 'UNCONFIRMED')),
    notes       TEXT,
    created_at  TEXT NOT NULL,
    UNIQUE (code, version)
);
CREATE TABLE IF NOT EXISTS ri_calc_runs (
    id            TEXT PRIMARY KEY,
    batch_id      TEXT NOT NULL REFERENCES ri_import_batches(id),
    rule_set_id   INTEGER NOT NULL REFERENCES ri_rule_sets(id),
    brand_id      INTEGER NOT NULL REFERENCES ri_brands(id),
    org_level     TEXT NOT NULL,
    input_basis   TEXT NOT NULL,
    input_hash    TEXT NOT NULL,
    status        TEXT NOT NULL CHECK (status IN ('completed', 'error')),
    result_count  INTEGER NOT NULL DEFAULT 0,
    error_count   INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL,
    UNIQUE (batch_id, rule_set_id, brand_id, org_level, input_hash)
);
CREATE TABLE IF NOT EXISTS ri_calc_results (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          TEXT NOT NULL REFERENCES ri_calc_runs(id),
    batch_id        TEXT NOT NULL REFERENCES ri_import_batches(id),
    rule_set_id     INTEGER NOT NULL REFERENCES ri_rule_sets(id),
    rule_version    INTEGER NOT NULL,
    brand_id        INTEGER NOT NULL REFERENCES ri_brands(id),
    period_year     INTEGER NOT NULL,
    period_month    INTEGER NOT NULL,
    org_level       TEXT NOT NULL,
    entity_key      TEXT NOT NULL,
    entity_label    TEXT NOT NULL,
    input_quantity  TEXT NOT NULL,
    target          TEXT,
    achievement     TEXT,
    reward_rials    TEXT,                      -- INDICATIVE, PROPOSED; never a payment instruction
    rule_status     TEXT NOT NULL CHECK (rule_status IN ('PROPOSED', 'UNCONFIRMED')),
    result_status   TEXT NOT NULL CHECK (result_status IN ('ok', 'error')),
    error_message   TEXT,
    explain_json    TEXT NOT NULL,
    calculated_at   TEXT NOT NULL,
    UNIQUE (run_id, entity_key)
);
CREATE TABLE IF NOT EXISTS ri_calc_result_inputs (
    result_id INTEGER NOT NULL REFERENCES ri_calc_results(id),
    fact_id   INTEGER NOT NULL REFERENCES ri_sales_facts(id),
    PRIMARY KEY (result_id, fact_id)
);

-- ------------------------------------------------------ 6. reconciliation and decisions
CREATE TABLE IF NOT EXISTS ri_workbook_references (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id     TEXT NOT NULL REFERENCES ri_import_batches(id),
    ref_code     TEXT NOT NULL,
    description  TEXT NOT NULL,
    brand_code   TEXT,
    org_level    TEXT,
    value        TEXT NOT NULL,
    unit         TEXT NOT NULL,
    source_sheet TEXT,
    UNIQUE (batch_id, ref_code)
);
CREATE TABLE IF NOT EXISTS ri_reconciliation_checks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id        TEXT NOT NULL REFERENCES ri_import_batches(id),
    run_id          TEXT REFERENCES ri_calc_runs(id),
    check_code      TEXT NOT NULL,
    title           TEXT NOT NULL,
    reference_value TEXT,
    prototype_value TEXT,
    abs_variance    TEXT,
    pct_variance    TEXT,
    matched         INTEGER,
    missing         INTEGER,
    duplicates      INTEGER,
    unresolved      INTEGER,
    status          TEXT NOT NULL CHECK (status IN ('match', 'explained', 'warning', 'error')),
    explanation     TEXT NOT NULL DEFAULT '',
    detail_json     TEXT NOT NULL DEFAULT '{}',
    created_at      TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_ri_checks
    ON ri_reconciliation_checks (batch_id, COALESCE(run_id, ''), check_code);

CREATE TABLE IF NOT EXISTS ri_business_decisions (
    id          TEXT PRIMARY KEY,              -- BD-01 ...
    question    TEXT NOT NULL,
    assumption  TEXT,
    impact      TEXT NOT NULL,
    status      TEXT NOT NULL CHECK (status IN ('OPEN', 'ASSUMPTION', 'PROPOSED', 'CONFIRMED')),
    approver    TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
