-- Spec 009 — Vigilador 3.0 MVP Foundation (enterprise/)
-- 5 tablas enterprise. tenant_id UUID en todas (single-tenant en MVP,
-- schema preparado para multi-tenancy). Aplicada por MigrationRunner del 2.0
-- (SQL crudo, no Alembic). Idempotente vía IF NOT EXISTS.

-- Estado de salud de cada tool (escrito por HealthMonitor, leído por ToolRegistry).
CREATE TABLE IF NOT EXISTS tool_health (
    name TEXT PRIMARY KEY,
    tenant_id UUID NOT NULL,
    status TEXT NOT NULL DEFAULT 'UNKNOWN',
    last_check TIMESTAMPTZ NULL,
    fail_count INTEGER NOT NULL DEFAULT 0,
    last_error TEXT NULL,
    domain TEXT NULL,
    requires_key BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS tool_health_tenant_id_idx ON tool_health (tenant_id);
CREATE INDEX IF NOT EXISTS tool_health_name_idx ON tool_health (name);

-- Credenciales OAuth encriptadas (Fernet) por proveedor.
CREATE TABLE IF NOT EXISTS oauth_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    provider TEXT NOT NULL,
    token_encrypted TEXT NOT NULL,
    refresh_token_encrypted TEXT NULL,
    expires_at TIMESTAMPTZ NULL,
    scopes JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, provider)
);

CREATE INDEX IF NOT EXISTS oauth_credentials_tenant_id_idx ON oauth_credentials (tenant_id);
CREATE INDEX IF NOT EXISTS oauth_credentials_provider_idx ON oauth_credentials (provider);

-- Subagentes (jerarquía de ejecución; pausa/reanudación).
CREATE TABLE IF NOT EXISTS subagents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    parent_session_id UUID NULL,
    depth INTEGER NOT NULL DEFAULT 0,
    role TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    pause_reason TEXT NULL,
    resume_token TEXT NULL,
    last_progress_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ NULL
);

CREATE INDEX IF NOT EXISTS subagents_tenant_id_idx ON subagents (tenant_id);

-- Aprobaciones pendientes (human-in-the-loop).
CREATE TABLE IF NOT EXISTS pending_approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    kind TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    requested_by_agent TEXT NULL,
    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status TEXT NOT NULL DEFAULT 'PENDING'
);

CREATE INDEX IF NOT EXISTS pending_approvals_tenant_id_idx ON pending_approvals (tenant_id);

-- Perfil de la empresa (onboarding).
CREATE TABLE IF NOT EXISTS company_profile (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    name TEXT NOT NULL,
    sector TEXT NULL,
    country TEXT NULL,
    department TEXT NULL,
    municipality TEXT NULL,
    timezone TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id)
);

CREATE INDEX IF NOT EXISTS company_profile_tenant_id_idx ON company_profile (tenant_id);
