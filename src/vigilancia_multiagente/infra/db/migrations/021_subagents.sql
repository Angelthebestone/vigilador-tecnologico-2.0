-- Migration 021: subagents — Spec 021 F4a.E / FR-051
-- Tracks recursive agent spawns for observability + budget enforcement.
-- Idempotent: safe to run multiple times.

CREATE TABLE IF NOT EXISTS subagents (
    id                  UUID PRIMARY KEY,
    tenant_id           UUID NOT NULL,
    parent_session_id   UUID NOT NULL,
    parent_agent_id     TEXT,
    depth               INTEGER NOT NULL DEFAULT 0 CHECK (depth >= 0),
    role                TEXT NOT NULL,
    spawn_reason        TEXT,
    status              TEXT NOT NULL DEFAULT 'ACTIVE'
                            CHECK (status IN ('ACTIVE', 'COMPLETED', 'FAILED')),
    last_progress_at    TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at        TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_subagents_tenant_session
    ON subagents (tenant_id, parent_session_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_subagents_parent_agent
    ON subagents (parent_agent_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_subagents_status
    ON subagents (status, last_progress_at DESC);
