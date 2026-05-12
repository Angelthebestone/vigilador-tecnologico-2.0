CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS research_sessions (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL,
    user_query TEXT NOT NULL,
    scope JSONB NULL,
    clarification_set_id UUID NULL,
    approved_plan_id UUID NULL,
    final_report_id UUID NULL,
    execution_time_seconds DOUBLE PRECISION NULL,
    error_code TEXT NULL,
    error_message TEXT NULL
);

CREATE TABLE IF NOT EXISTS research_plans (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES research_sessions(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    branches JSONB NOT NULL,
    global_constraints JSONB NOT NULL DEFAULT '{}'::jsonb,
    requires_approval BOOLEAN NOT NULL DEFAULT TRUE,
    approved_at TIMESTAMPTZ NULL
);

CREATE INDEX IF NOT EXISTS research_plans_session_version_idx
    ON research_plans (session_id, version DESC);

CREATE TABLE IF NOT EXISTS branch_results (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES research_sessions(id) ON DELETE CASCADE,
    branch_type TEXT NOT NULL,
    queries_executed JSONB NOT NULL,
    findings JSONB NOT NULL,
    sources JSONB NOT NULL,
    started_at TIMESTAMPTZ NULL,
    completed_at TIMESTAMPTZ NULL,
    coverage_score DOUBLE PRECISION NULL,
    confidence_score DOUBLE PRECISION NULL,
    errors JSONB NOT NULL DEFAULT '[]'::jsonb
);

CREATE INDEX IF NOT EXISTS branch_results_session_idx
    ON branch_results (session_id, completed_at DESC NULLS LAST);

CREATE TABLE IF NOT EXISTS research_reports (
    session_id UUID PRIMARY KEY REFERENCES research_sessions(id) ON DELETE CASCADE,
    report_markdown TEXT NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS iteration_records (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES research_sessions(id) ON DELETE CASCADE,
    branch_type TEXT NOT NULL,
    payload JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS semantic_relations (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES research_sessions(id) ON DELETE CASCADE,
    payload JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS provider_telemetry (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES research_sessions(id) ON DELETE CASCADE,
    payload JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS embedding_vectors (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES research_sessions(id) ON DELETE CASCADE,
    content_type TEXT NOT NULL,
    content_ref_id TEXT NOT NULL,
    vector VECTOR(768) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (session_id, content_type, content_ref_id)
);
