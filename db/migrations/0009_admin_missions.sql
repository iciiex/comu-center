-- 0009 — Administrator-managed missions (DEMO).
-- admin_missions: missions an administrator creates (completed through the normal game path).
-- mission_settings: activation and assignment for any mission (catalog, sales or custom).
CREATE TABLE IF NOT EXISTS admin_missions (
    id               TEXT PRIMARY KEY,
    organization_id  TEXT NOT NULL REFERENCES organizations(id),
    title            TEXT NOT NULL,
    description      TEXT NOT NULL,
    category         TEXT NOT NULL,
    kind             TEXT NOT NULL,
    xp_reward        INTEGER NOT NULL CHECK (xp_reward BETWEEN 10 AND 500),
    created_by       TEXT NOT NULL REFERENCES users(id),
    created_at       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS mission_settings (
    organization_id  TEXT NOT NULL REFERENCES organizations(id),
    mission_id       TEXT NOT NULL,
    status           TEXT NOT NULL CHECK (status IN ('active', 'inactive')),
    scope            TEXT NOT NULL DEFAULT 'all' CHECK (scope IN ('all', 'branch', 'team', 'user')),
    scope_value      TEXT,
    updated_by       TEXT REFERENCES users(id),
    updated_at       TEXT NOT NULL,
    PRIMARY KEY (organization_id, mission_id)
);
