-- P1 schema: accounts + sessions (used now); runs + run_stages (created now, driven by P2).
-- Timestamps are unix seconds (BIGINT) to keep the Rust store dependency-light.

CREATE TABLE IF NOT EXISTS users (
    account_id TEXT PRIMARY KEY,
    email      TEXT NOT NULL,
    plan       TEXT NOT NULL DEFAULT '',
    enc_token  TEXT NOT NULL,
    created_at BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    token      TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    created_at BIGINT NOT NULL,
    expires_at BIGINT NOT NULL
);

CREATE INDEX IF NOT EXISTS sessions_account_idx ON sessions (account_id);

CREATE TABLE IF NOT EXISTS runs (
    id         TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    slug       TEXT NOT NULL,
    pitch      TEXT NOT NULL,
    state      TEXT NOT NULL,
    error      TEXT,
    created_at BIGINT NOT NULL
);

CREATE INDEX IF NOT EXISTS runs_account_idx ON runs (account_id, created_at DESC);

CREATE TABLE IF NOT EXISTS run_stages (
    id       BIGSERIAL PRIMARY KEY,
    run_id   TEXT NOT NULL,
    stage_id TEXT NOT NULL,
    verdict  TEXT,
    score    DOUBLE PRECISION,
    ts       BIGINT NOT NULL
);

CREATE INDEX IF NOT EXISTS run_stages_run_idx ON run_stages (run_id, id);
