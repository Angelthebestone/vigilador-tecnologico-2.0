CREATE TABLE IF NOT EXISTS source_trust (
    source_id TEXT PRIMARY KEY,
    source_type TEXT NOT NULL DEFAULT 'domain',
    current_score INTEGER NOT NULL DEFAULT 50,
    confirmation_count INTEGER NOT NULL DEFAULT 0,
    contradiction_count INTEGER NOT NULL DEFAULT 0,
    last_accessed TIMESTAMPTZ NULL,
    score_history JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS source_trust_score_idx
    ON source_trust (current_score DESC);
