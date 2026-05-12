CREATE TABLE IF NOT EXISTS graph_snapshots (
    session_id UUID PRIMARY KEY REFERENCES research_sessions(id) ON DELETE CASCADE,
    nodes JSONB NOT NULL DEFAULT '[]'::jsonb,
    edges JSONB NOT NULL DEFAULT '[]'::jsonb,
    analytics JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS graph_snapshots_updated_at_idx
    ON graph_snapshots (updated_at DESC);

CREATE INDEX IF NOT EXISTS graph_snapshots_analytics_gin_idx
    ON graph_snapshots USING GIN (analytics);
