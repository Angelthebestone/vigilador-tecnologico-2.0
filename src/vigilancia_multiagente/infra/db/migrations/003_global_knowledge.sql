CREATE TABLE IF NOT EXISTS global_knowledge (
    session_id UUID PRIMARY KEY REFERENCES research_sessions(id) ON DELETE CASCADE,
    query_summary TEXT NOT NULL,
    findings_graph JSONB,
    embedding VECTOR(768),
    entities JSONB,
    source_scores JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NULL
);

CREATE INDEX IF NOT EXISTS global_knowledge_created_at_idx
    ON global_knowledge (created_at DESC);

CREATE INDEX IF NOT EXISTS global_knowledge_expires_at_idx
    ON global_knowledge (expires_at);

CREATE INDEX IF NOT EXISTS global_knowledge_embedding_idx
    ON global_knowledge USING ivfflat (embedding vector_cosine_ops)
    WHERE embedding IS NOT NULL;
