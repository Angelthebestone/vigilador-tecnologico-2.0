-- Spec 007 — Sistema de Evaluacion Inteligente.
-- 6 tablas nuevas (T003) + columnas JSONB opcionales en findings (T004).
-- Aditivas: si los flags VT_EVAL_WS_* estan en false, las tablas quedan
-- vacias y las columnas JSONB nuevas tampoco se escriben. Cero impacto
-- sobre el comportamiento actual del vigilador.

-- WS-A: reputacion de autor (OpenAlex + Crossref).
CREATE TABLE IF NOT EXISTS author_reputation (
    author_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    h_index INTEGER NOT NULL DEFAULT 0,
    total_citations INTEGER NOT NULL DEFAULT 0,
    retraction_count INTEGER NOT NULL DEFAULT 0,
    primary_affiliation TEXT NULL,
    affiliation_type TEXT NOT NULL DEFAULT 'independent',
    domain_weights JSONB NOT NULL DEFAULT '{}'::jsonb,
    last_refreshed TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS author_reputation_last_refreshed_idx
    ON author_reputation (last_refreshed DESC);

-- WS-A: curvas de decaimiento temporal por dominio + tipo de fuente.
CREATE TABLE IF NOT EXISTS temporal_decay_config (
    domain TEXT NOT NULL,
    source_type TEXT NOT NULL,
    half_life_months INTEGER NOT NULL,
    PRIMARY KEY (domain, source_type)
);

-- WS-B: registro de esquemas pydantic por (source_type, domain) versionados.
CREATE TABLE IF NOT EXISTS extraction_schema (
    source_type TEXT NOT NULL,
    domain TEXT NOT NULL,
    json_schema JSONB NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (source_type, domain, version)
);

-- WS-E: golden cases (spec ejecutable) + sus ejecuciones historicas.
CREATE TABLE IF NOT EXISTS golden_case (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT '',
    seed_query TEXT NOT NULL,
    expected_findings JSONB NOT NULL DEFAULT '[]'::jsonb,
    expected_confidence DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    priority TEXT NOT NULL DEFAULT 'p2_normal',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS golden_case_active_idx
    ON golden_case (is_active) WHERE is_active;

CREATE TABLE IF NOT EXISTS golden_case_run (
    id UUID PRIMARY KEY,
    case_id UUID NOT NULL REFERENCES golden_case (id) ON DELETE CASCADE,
    run_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    success BOOLEAN NOT NULL,
    actual_confidence DOUBLE PRECISION NOT NULL,
    delta_vs_expected DOUBLE PRECISION NOT NULL,
    failure_details TEXT NULL
);

CREATE INDEX IF NOT EXISTS golden_case_run_case_run_at_idx
    ON golden_case_run (case_id, run_at DESC);

-- WS-E: curva de calibracion isotonica persistida con versionado.
CREATE TABLE IF NOT EXISTS calibration_curve (
    id UUID PRIMARY KEY,
    model_version TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    samples_count INTEGER NOT NULL,
    mappings JSONB NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE UNIQUE INDEX IF NOT EXISTS calibration_curve_one_active_idx
    ON calibration_curve (is_active) WHERE is_active;

-- T004: columnas JSONB opcionales en findings para entidades efimeras.
-- Cada workstream WS-* poblara su columna cuando su flag este activo. NULL
-- por defecto preserva la semantica anterior cuando el flag esta off.
ALTER TABLE IF EXISTS findings
    ADD COLUMN IF NOT EXISTS assumptions JSONB NULL;

ALTER TABLE IF EXISTS findings
    ADD COLUMN IF NOT EXISTS external_validation JSONB NULL;

ALTER TABLE IF EXISTS findings
    ADD COLUMN IF NOT EXISTS reproducibility JSONB NULL;

ALTER TABLE IF EXISTS findings
    ADD COLUMN IF NOT EXISTS forensic_trace JSONB NULL;

ALTER TABLE IF EXISTS findings
    ADD COLUMN IF NOT EXISTS authenticity JSONB NULL;
