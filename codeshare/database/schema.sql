-- CodeShare schema. Run this in the Neon or Supabase SQL editor if you prefer
-- to initialize the database manually. The FastAPI app also creates this table
-- automatically when it first connects.
CREATE TABLE IF NOT EXISTS snippets (
    id VARCHAR(20) PRIMARY KEY,
    title VARCHAR(120) NOT NULL,
    language VARCHAR(30) NOT NULL DEFAULT 'plaintext',
    code TEXT NOT NULL,
    edit_token_hash CHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    views BIGINT NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_snippets_created_at ON snippets (created_at DESC);
