-- Migration 010: PI Quarantine table (FR-009, FR-018, FR-019)
-- Idempotent: safe to apply multiple times.

CREATE TABLE IF NOT EXISTS pi_quarantine (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    source VARCHAR(512),
    content_excerpt TEXT,
    detected_patterns JSONB NOT NULL DEFAULT '[]'::jsonb,
    severity VARCHAR(10) NOT NULL DEFAULT 'LOW',
    quarantined_at TIMESTAMP WITH TIME ZONE NOT NULL,
    approved_at TIMESTAMP WITH TIME ZONE,
    approved_by VARCHAR(256)
);

-- Indices (idempotent via IF NOT EXISTS)
CREATE INDEX IF NOT EXISTS idx_pi_quarantine_tenant_id ON pi_quarantine (tenant_id);
CREATE INDEX IF NOT EXISTS idx_pi_quarantine_quarantined_at ON pi_quarantine (quarantined_at DESC);

-- Reversibility (commented; uncomment to rollback):
-- DROP TABLE IF EXISTS pi_quarantine;
