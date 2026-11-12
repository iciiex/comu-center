-- 0005 — Generic, tenant-scoped organization hierarchy foundation for Tribal.
-- No fixed hierarchy levels or Tribal-specific unit kinds are encoded here.
-- This migration deliberately does not add roles, scoring, campaigns or report tables.
-- `users.id` is already globally unique; this composite index enables a tenant-safe FK.
CREATE UNIQUE INDEX IF NOT EXISTS ux_users_id_organization
    ON users (id, organization_id);

CREATE TABLE IF NOT EXISTS org_unit_types (
    id                TEXT PRIMARY KEY,
    organization_id   TEXT NOT NULL REFERENCES organizations(id),
    code              TEXT NOT NULL,
    label             TEXT NOT NULL,
    labels_json       TEXT NOT NULL DEFAULT '{}',
    display_order     INTEGER NOT NULL DEFAULT 0,
    is_active         INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at        TEXT NOT NULL,
    UNIQUE (organization_id, code),
    UNIQUE (id, organization_id)
);

CREATE TABLE IF NOT EXISTS org_unit_type_parent_types (
    organization_id   TEXT NOT NULL REFERENCES organizations(id),
    child_type_id     TEXT NOT NULL,
    parent_type_id    TEXT NOT NULL,
    PRIMARY KEY (child_type_id, parent_type_id),
    FOREIGN KEY (child_type_id, organization_id)
        REFERENCES org_unit_types(id, organization_id),
    FOREIGN KEY (parent_type_id, organization_id)
        REFERENCES org_unit_types(id, organization_id),
    CHECK (child_type_id <> parent_type_id)
);

CREATE TABLE IF NOT EXISTS org_units (
    id                TEXT PRIMARY KEY,
    organization_id   TEXT NOT NULL REFERENCES organizations(id),
    type_id           TEXT NOT NULL,
    parent_id         TEXT,
    external_key      TEXT,
    name              TEXT NOT NULL,
    flag_asset_key    TEXT,
    status            TEXT NOT NULL DEFAULT 'active'
                      CHECK (status IN ('active', 'inactive', 'archived')),
    valid_from        TEXT,
    valid_to          TEXT,
    created_at        TEXT NOT NULL,
    updated_at        TEXT NOT NULL,
    UNIQUE (id, organization_id),
    FOREIGN KEY (type_id, organization_id)
        REFERENCES org_unit_types(id, organization_id),
    FOREIGN KEY (parent_id, organization_id)
        REFERENCES org_units(id, organization_id),
    UNIQUE (organization_id, external_key),
    CHECK (parent_id IS NULL OR parent_id <> id),
    CHECK (valid_to IS NULL OR valid_from IS NULL OR valid_to > valid_from)
);

CREATE TABLE IF NOT EXISTS org_memberships (
    id                TEXT PRIMARY KEY,
    organization_id   TEXT NOT NULL REFERENCES organizations(id),
    user_id           TEXT NOT NULL,
    unit_id           TEXT NOT NULL,
    source_system     TEXT,
    external_key      TEXT,
    valid_from        TEXT NOT NULL,
    valid_to          TEXT,
    created_at        TEXT NOT NULL,
    FOREIGN KEY (unit_id, organization_id)
        REFERENCES org_units(id, organization_id),
    FOREIGN KEY (user_id, organization_id)
        REFERENCES users(id, organization_id),
    CHECK (valid_to IS NULL OR valid_to > valid_from),
    CHECK ((source_system IS NULL) = (external_key IS NULL))
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_org_membership_source_key
    ON org_memberships (organization_id, source_system, external_key)
    WHERE source_system IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_org_units_parent
    ON org_units (organization_id, parent_id, status, name);
CREATE INDEX IF NOT EXISTS ix_org_units_type
    ON org_units (organization_id, type_id, status);
CREATE INDEX IF NOT EXISTS ix_org_memberships_user_period
    ON org_memberships (organization_id, user_id, valid_from, valid_to);
CREATE INDEX IF NOT EXISTS ix_org_memberships_unit_period
    ON org_memberships (organization_id, unit_id, valid_from, valid_to);
