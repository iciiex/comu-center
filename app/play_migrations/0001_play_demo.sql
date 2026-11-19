-- Demo-only schema. This migration is never applied to the Kiloos Club database.
CREATE TABLE IF NOT EXISTS play_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS play_families (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS play_accounts (
    id TEXT PRIMARY KEY,
    family_id TEXT REFERENCES play_families(id),
    role TEXT NOT NULL CHECK (role IN ('admin', 'visitor', 'member')),
    name TEXT NOT NULL,
    avatar TEXT NOT NULL,
    age TEXT NOT NULL DEFAULT 'adult' CHECK (age IN ('adult', 'child')),
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    region TEXT NOT NULL DEFAULT '',
    monthly_target INTEGER NOT NULL DEFAULT 0 CHECK (monthly_target >= 0),
    created_at INTEGER NOT NULL,
    CHECK ((role = 'admin' AND family_id IS NULL) OR (role <> 'admin' AND family_id IS NOT NULL)),
    CHECK (role = 'member' OR age = 'adult')
);
CREATE UNIQUE INDEX IF NOT EXISTS play_one_visitor_per_family ON play_accounts(family_id)
    WHERE role = 'visitor';
CREATE TABLE IF NOT EXISTS play_sessions (
    token_hash TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES play_accounts(id),
    expires_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS play_token_rules (
    version INTEGER PRIMARY KEY,
    unit INTEGER NOT NULL CHECK (unit > 0),
    per_unit INTEGER NOT NULL CHECK (per_unit > 0),
    effective_at INTEGER NOT NULL,
    actor_id TEXT NOT NULL REFERENCES play_accounts(id)
);
CREATE TABLE IF NOT EXISTS play_campaigns (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    starts_on TEXT NOT NULL,
    ends_on TEXT NOT NULL,
    active INTEGER NOT NULL CHECK (active IN (0, 1)),
    bonus INTEGER NOT NULL CHECK (bonus >= 0),
    CHECK (starts_on <= ends_on)
);
CREATE TABLE IF NOT EXISTS play_campaign_members (
    campaign_id TEXT NOT NULL REFERENCES play_campaigns(id),
    account_id TEXT NOT NULL REFERENCES play_accounts(id),
    PRIMARY KEY (campaign_id, account_id)
);
CREATE TABLE IF NOT EXISTS play_sales (
    id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL UNIQUE,
    visitor_id TEXT NOT NULL REFERENCES play_accounts(id),
    campaign_id TEXT REFERENCES play_campaigns(id),
    amount INTEGER NOT NULL CHECK (amount > 0),
    note TEXT NOT NULL,
    sold_on TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    approved_at INTEGER,
    approved_by TEXT REFERENCES play_accounts(id),
    rule_version INTEGER REFERENCES play_token_rules(version),
    token_amount INTEGER NOT NULL DEFAULT 0 CHECK (token_amount >= 0),
    campaign_bonus INTEGER NOT NULL DEFAULT 0 CHECK (campaign_bonus >= 0)
);
CREATE TABLE IF NOT EXISTS play_wallet_events (
    id TEXT PRIMARY KEY,
    family_id TEXT NOT NULL REFERENCES play_families(id),
    kind TEXT NOT NULL CHECK (kind IN ('sale', 'entry', 'issue', 'deduct', 'correct')),
    source_id TEXT NOT NULL,
    amount INTEGER NOT NULL CHECK (amount <> 0),
    created_at INTEGER NOT NULL,
    reason TEXT NOT NULL,
    actor_id TEXT REFERENCES play_accounts(id),
    UNIQUE (kind, source_id)
);
CREATE INDEX IF NOT EXISTS play_wallet_by_family ON play_wallet_events(family_id, created_at);
CREATE TABLE IF NOT EXISTS play_notices (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES play_accounts(id),
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    read_at INTEGER
);
CREATE TABLE IF NOT EXISTS play_games (
    key TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    enabled INTEGER NOT NULL CHECK (enabled IN (0, 1)),
    cost INTEGER NOT NULL CHECK (cost >= 0),
    reward INTEGER NOT NULL CHECK (reward >= 0),
    min_players INTEGER NOT NULL CHECK (min_players >= 2),
    max_players INTEGER NOT NULL CHECK (max_players BETWEEN min_players AND 8),
    duration INTEGER NOT NULL CHECK (duration BETWEEN 10 AND 300),
    rounds INTEGER NOT NULL CHECK (rounds BETWEEN 1 AND 8)
);
CREATE TABLE IF NOT EXISTS play_cards (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL CHECK (kind IN ('customer', 'product', 'feature', 'limitation', 'event')),
    label TEXT NOT NULL,
    detail TEXT NOT NULL,
    archived INTEGER NOT NULL DEFAULT 0 CHECK (archived IN (0, 1))
);
CREATE TABLE IF NOT EXISTS play_questions (
    id TEXT PRIMARY KEY,
    prompt TEXT NOT NULL,
    category TEXT NOT NULL,
    difficulty TEXT NOT NULL CHECK (difficulty IN ('easy', 'medium', 'hard')),
    options_json TEXT NOT NULL,
    answer INTEGER NOT NULL CHECK (answer BETWEEN 0 AND 3),
    archived INTEGER NOT NULL DEFAULT 0 CHECK (archived IN (0, 1))
);
CREATE TABLE IF NOT EXISTS play_words (
    id TEXT PRIMARY KEY,
    word TEXT NOT NULL,
    hint TEXT NOT NULL,
    category TEXT NOT NULL,
    forbidden_json TEXT NOT NULL,
    archived INTEGER NOT NULL DEFAULT 0 CHECK (archived IN (0, 1))
);
CREATE TABLE IF NOT EXISTS play_rooms (
    id TEXT PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    request_id TEXT NOT NULL UNIQUE,
    family_id TEXT NOT NULL REFERENCES play_families(id),
    host_id TEXT NOT NULL REFERENCES play_accounts(id),
    game_key TEXT NOT NULL REFERENCES play_games(key),
    options_json TEXT NOT NULL,
    state_json TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS play_rooms_by_family ON play_rooms(family_id, created_at);
CREATE TABLE IF NOT EXISTS play_room_members (
    room_id TEXT NOT NULL REFERENCES play_rooms(id),
    account_id TEXT NOT NULL REFERENCES play_accounts(id),
    ready INTEGER NOT NULL DEFAULT 0 CHECK (ready IN (0, 1)),
    joined_at INTEGER NOT NULL,
    PRIMARY KEY (room_id, account_id)
);
CREATE TABLE IF NOT EXISTS play_results (
    id TEXT PRIMARY KEY,
    room_id TEXT REFERENCES play_rooms(id),
    family_id TEXT NOT NULL REFERENCES play_families(id),
    game_key TEXT NOT NULL REFERENCES play_games(key),
    round_no INTEGER NOT NULL,
    details_json TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    UNIQUE (room_id, round_no)
);
CREATE INDEX IF NOT EXISTS play_results_by_family ON play_results(family_id, created_at);
CREATE TABLE IF NOT EXISTS play_scores (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES play_accounts(id),
    family_id TEXT NOT NULL REFERENCES play_families(id),
    source_type TEXT NOT NULL CHECK (source_type IN ('game', 'mission', 'sales_mission')),
    source_id TEXT NOT NULL,
    amount INTEGER NOT NULL CHECK (amount >= 0),
    created_at INTEGER NOT NULL,
    UNIQUE (account_id, source_type, source_id)
);
CREATE INDEX IF NOT EXISTS play_scores_by_family ON play_scores(family_id, created_at);
CREATE TABLE IF NOT EXISTS play_missions (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    audience TEXT NOT NULL CHECK (audience IN ('visitor', 'member')),
    metric TEXT NOT NULL CHECK (metric IN ('games', 'sales', 'amount')),
    goal INTEGER NOT NULL CHECK (goal >= 1),
    points INTEGER NOT NULL CHECK (points >= 0),
    campaign_id TEXT REFERENCES play_campaigns(id),
    starts_on TEXT NOT NULL,
    ends_on TEXT NOT NULL,
    active INTEGER NOT NULL CHECK (active IN (0, 1)),
    CHECK (starts_on <= ends_on)
);
CREATE TABLE IF NOT EXISTS play_claims (
    mission_id TEXT NOT NULL REFERENCES play_missions(id),
    account_id TEXT NOT NULL REFERENCES play_accounts(id),
    created_at INTEGER NOT NULL,
    PRIMARY KEY (mission_id, account_id)
);
CREATE TABLE IF NOT EXISTS play_rewards (
    code TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    icon TEXT NOT NULL,
    active INTEGER NOT NULL CHECK (active IN (0, 1))
);
CREATE TABLE IF NOT EXISTS play_competitions (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('rank', 'community')),
    target INTEGER NOT NULL CHECK (target > 0),
    reward_code TEXT REFERENCES play_rewards(code),
    starts_on TEXT NOT NULL,
    ends_on TEXT NOT NULL,
    active INTEGER NOT NULL CHECK (active IN (0, 1)),
    CHECK (starts_on <= ends_on)
);
CREATE TABLE IF NOT EXISTS play_badges (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES play_accounts(id),
    code TEXT NOT NULL REFERENCES play_rewards(code),
    source_id TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    UNIQUE (account_id, code, source_id)
);
CREATE TABLE IF NOT EXISTS play_invites (
    code TEXT PRIMARY KEY,
    family_id TEXT NOT NULL REFERENCES play_families(id),
    created_by TEXT NOT NULL REFERENCES play_accounts(id),
    age TEXT NOT NULL CHECK (age IN ('adult', 'child')),
    expires_at INTEGER NOT NULL,
    used_by TEXT REFERENCES play_accounts(id),
    revoked INTEGER NOT NULL DEFAULT 0 CHECK (revoked IN (0, 1))
);
CREATE TABLE IF NOT EXISTS play_audit (
    id TEXT PRIMARY KEY,
    actor_id TEXT REFERENCES play_accounts(id),
    action TEXT NOT NULL,
    summary TEXT NOT NULL,
    created_at INTEGER NOT NULL
);
