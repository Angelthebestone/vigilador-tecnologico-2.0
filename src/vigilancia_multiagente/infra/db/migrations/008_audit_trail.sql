-- Migration 008: Audit Trail - agent_modifications table
-- Idempotent: safe to run multiple times

CREATE TABLE IF NOT EXISTS agent_modifications (
    id              UUID PRIMARY KEY,
    tenant_id       UUID NOT NULL,
    target_file     TEXT NOT NULL,
    target_kind     TEXT NOT NULL,
    diff            TEXT NOT NULL,
    diff_summary    TEXT,
    applied_at      TIMESTAMPTZ NOT NULL,
    rollback_token  TEXT NOT NULL UNIQUE,
    agent_id        TEXT NOT NULL,
    session_id      UUID,
    triggered_by    TEXT NOT NULL,
    justification   TEXT,
    status          TEXT NOT NULL DEFAULT 'applied',
    reverted_at     TIMESTAMPTZ,
    reverted_by     TEXT,
    superseded_by   UUID REFERENCES agent_modifications(id)
);

CREATE INDEX IF NOT EXISTS idx_agent_modifications_tenant_applied
    ON agent_modifications (tenant_id, applied_at DESC);

CREATE INDEX IF NOT EXISTS idx_agent_modifications_target_applied
    ON agent_modifications (target_file, applied_at DESC);

CREATE INDEX IF NOT EXISTS idx_agent_modifications_rollback_token
    ON agent_modifications (rollback_token);
