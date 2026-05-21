# Data Model: Sistema de Evaluacion Inteligente (Spec 007)

Entidades de dominio y sus relaciones. Todas las entidades viven en
`domain/` (frozen dataclasses) o como tablas en `infra/persistence/`
segun corresponda.

---

## WS-A — Source Quality

### `AuthorReputation` (entidad / tabla `author_reputation`)

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `author_id` | str (PK) | ORCID si esta disponible, hash(name+affil) si no |
| `display_name` | str | Nombre canonico |
| `h_index` | int | Indice h derivado de OpenAlex |
| `total_citations` | int | Citaciones acumuladas |
| `retraction_count` | int | Retractaciones registradas |
| `primary_affiliation` | str \| None | Institucion principal |
| `affiliation_type` | enum (`academic`, `industry`, `government`, `independent`) | Para FR-A02 |
| `domain_weights` | json `dict[str, float]` | Peso por dominio tecnologico |
| `last_refreshed` | datetime | Para invalidacion incremental |

**Reglas**:
- `h_index >= 0`; `retraction_count >= 0`.
- `domain_weights` valido contra el catalogo de dominios definidos en
  `config/skills/skill_matrix_default.yaml`.
- `last_refreshed > now() - 30 days` o se considera stale.

### `ConflictOfInterest` (entidad)

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `source_id` | UUID | FK a la fuente analizada |
| `funder_entity` | str | Nombre de la entidad financiadora |
| `funder_type` | enum (`corporate`, `academic`, `government`, `unknown`) | |
| `corporate_ratio` | float `[0, 1]` | proporcion corporativo / total funding |
| `risk_level` | enum (`low`, `medium`, `high`) | Derivado de `corporate_ratio` |

**Reglas**:
- `risk_level = high` si `corporate_ratio >= 0.7`.

### `TemporalDecayConfig` (entidad / tabla `temporal_decay_config`)

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `domain` | str (PK) | Dominio tecnologico (ej `AI`, `MATH`) |
| `half_life_months` | int | Vida media de la fuente en meses |
| `source_type` | enum (`paper`, `patent`, `news`, `blog`) | Por tipo |

### `ClaimExternalValidation` (entidad)

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `claim_id` | UUID | FK a Finding |
| `external_db` | str | Nombre de la base externa consultada |
| `status` | enum (`verified`, `contradicted`, `not_found`) | |
| `evidence_url` | str \| None | URL de la evidencia externa |

### `RetractionRecord` (entidad)

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `source_doi` | str (PK) | DOI retractado |
| `retracted_at` | datetime | |
| `reason` | str | Texto libre |
| `dependent_findings` | list[UUID] | Findings invalidados |

### `ReproducibilityScore` (entidad)

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `finding_id` | UUID (PK) | |
| `has_public_repo` | bool | |
| `has_open_data` | bool | |
| `has_reproducible_env` | bool | Dockerfile / nix / conda |
| `score` | float `[0, 1]` | Composito ponderado |

---

## WS-B — Data Intelligence

### `HybridSearchQuery` (DTO)

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `text` | str | Query original |
| `vector` | list[float] | Embedding precomputado |
| `keywords` | list[str] | Tokens BM25 |
| `vector_weight` | float `[0, 1]` | Default `0.6` |
| `keyword_weight` | float `[0, 1]` | `1 - vector_weight` |

### `DedupedSource` (entidad)

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `canonical_url` | str | URL representante |
| `duplicate_urls` | list[str] | Sindicaciones detectadas |
| `similarity_score` | float `[0, 1]` | Score que activo la fusion |

### `ExtractionSchema` (entidad / tabla `extraction_schema`)

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `source_type` | enum (`paper`, `patent`, `news`, `blog`) | |
| `domain` | str | Dominio tecnologico |
| `json_schema` | json | Pydantic schema serializado |
| `version` | int | Para migracion |

### `ContentAuthenticitySignal` (entidad)

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `source_id` | UUID | FK a SourceRef |
| `ai_probability` | float `[0, 1]` | Score combinado de generacion por IA |
| `perplexity` | float | Perplejidad media sobre el texto |
| `burstiness` | float | Variabilidad de longitud/perplexidad por oracion |
| `boilerplate_hits` | int | Numero de frases-marca de LLM detectadas |
| `effective_freshness` | float `[0, 1]` | `raw_freshness * (1 - ai_probability * penalty)` |
| `penalty_factor` | float | Configurable por dominio |

**Reglas**:
- `ai_probability` se publica para todas las fuentes; no se borra ninguna.
- `effective_freshness` reemplaza al campo `freshness` previo en el
  scoring downstream (`SourceScorer.score_source`).

### `ConsensusDisputeMap` (entidad)

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `claim` | str | Afirmacion central |
| `supporting_sources` | list[SourceRef] | |
| `contradicting_sources` | list[SourceRef] | |
| `evidence_strength` | enum (`weak`, `moderate`, `strong`) | |
| `resolution` | str \| None | Si triangulacion resolvio |

---

## WS-C — Deep Analysis

### `ImplicitAssumption` (entidad)

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `finding_id` | UUID | FK |
| `text` | str | Asuncion en lenguaje natural |
| `severity` | enum (`info`, `warning`, `critical`) | |
| `affects_confidence` | float `[-1, 0]` | Penalizacion aplicada |

### `SCurveProjection` (entidad)

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `technology` | str | |
| `domain` | str | |
| `growth_rate` | float | Parametro `k` de la logistica |
| `inflection_year` | int | Punto de inflexion |
| `ceiling` | float | Plateau estimado |
| `r_squared` | float `[0, 1]` | Calidad del ajuste |
| `samples_count` | int | Datos historicos usados |

### `CriticalDependency` (entidad)

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `technology` | str | |
| `dependency_kind` | enum (`material`, `library`, `vendor`, `regulation`) | |
| `name` | str | Nombre del recurso |
| `risk_level` | enum (`low`, `medium`, `high`) | |

### `CounterfactualScenario` (entidad)

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `id` | UUID | |
| `question` | str | "Que pasaria si..." |
| `probability` | float `[0, 1]` | Estimada |
| `impact_summary` | str | Resumen narrativo |

### `MetaAnalysisResult` (entidad)

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `topic` | str | Fenomeno analizado |
| `studies_count` | int | |
| `effect_size_range` | tuple[float, float] | |
| `consensus_value` | float | Estimacion central |
| `i_squared` | float `[0, 1]` | Heterogeneidad |
| `q_test_pvalue` | float | |
| `outliers` | list[str] | Studies fuera del rango |

---

## WS-D — Strategic Signals

### `ConvergenceCluster` (entidad)

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `id` | UUID | |
| `domains` | list[str] | Dominios convergiendo |
| `representative_terms` | list[str] | |
| `growth_trend` | float | Pendiente temporal |
| `first_detected` | datetime | |

### `CollaborationNetwork` (entidad / extiende GraphSnapshot)

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `network_id` | UUID | |
| `nodes` | list[CollaborationNode] | Autor/inventor con metricas |
| `edges` | list[tuple[str, str, int]] | (a, b, peso) |
| `centrality_metrics` | json | Betweenness, eigenvector, etc. |
| `bubble_clusters` | list[list[str]] | Grupos auto-citantes |

### `IdeaLineage` (entidad)

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `idea` | str | |
| `seminal_publication` | SourceRef | |
| `citation_chain` | list[SourceRef] | Cadena ordenada |
| `circularity_detected` | bool | |

### `NarrativeShift` (entidad)

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `topic` | str | |
| `window_start` | datetime | |
| `window_end` | datetime | |
| `sentiment_pre` | float `[-1, 1]` | VADER compound |
| `sentiment_post` | float `[-1, 1]` | |
| `change_point` | datetime | |
| `change_magnitude` | float | abs(post - pre) |

### `TalentMobility` (entidad)

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `author_id` | str | FK a `author_reputation` |
| `academic_history` | list[Affiliation] | |
| `industry_transitions` | list[Affiliation] | |
| `mobility_score` | float `[0, 1]` | Indicador de transferencia tecnologica |

### `PatentingGap` (entidad)

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `subdomain` | str | |
| `publication_density` | float | Papers / ano |
| `patent_density` | float | Patentes / ano |
| `gap_score` | float | `pub / max(patent, 1)` |
| `classification` | enum (`blue_ocean`, `red_ocean`, `balanced`) | |

---

## WS-E — Output Assurance

### `GoldenCase` (entidad / tabla `golden_case`)

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `id` | UUID (PK) | |
| `name` | str | |
| `description` | str | |
| `seed_query` | str | Query que dispara el caso |
| `expected_findings` | list[ExpectedFinding] | Findings esperados (json) |
| `expected_confidence` | float `[0, 1]` | Confianza objetivo |
| `priority` | enum (`p0_critical`, `p1_high`, `p2_normal`) | |

### `GoldenCaseRun` (entidad / tabla `golden_case_run`)

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `id` | UUID (PK) | |
| `case_id` | UUID | FK |
| `run_at` | datetime | |
| `success` | bool | |
| `actual_confidence` | float `[0, 1]` | |
| `delta_vs_expected` | float | actual - expected |
| `failure_details` | str \| None | |

### `StakeholderSimulation` (entidad)

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `report_id` | UUID | |
| `stakeholder_type` | enum (`investor`, `regulator`, `competitor`, `academic`) | |
| `critique` | str | Texto del agente |
| `counterpoints` | list[str] | Bullets estructurados |

### `FalsificationScenario` (entidad)

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `conclusion_id` | UUID | FK |
| `hypothetical_evidence` | str | "Si apareciera X, esta conclusion cae" |
| `plausibility` | float `[0, 1]` | Probabilidad estimada de aparicion |
| `falsifiable` | bool | True si al menos un escenario fue formulado |

### `BiasAudit` (entidad)

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `report_id` | UUID | |
| `geographic_distribution` | json `dict[str, float]` | Por pais |
| `gender_distribution` | json `dict[str, float]` | Estimacion |
| `institutional_distribution` | json `dict[str, float]` | |
| `critical_bias_detected` | bool | |
| `bias_categories` | list[str] | Categorias activadas |

### `ForensicTrace` (entidad)

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `claim_id` | UUID | |
| `chain` | list[TraceStep] | Pasos secuenciales |
| `confidence_at_each_step` | list[float] | |

`TraceStep`:
| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `step_type` | enum (`source_fetch`, `extraction`, `reasoning`, `synthesis`) | |
| `input_ref` | str | URL/finding/etc |
| `output_ref` | str | Donde quedo el resultado |
| `applied_rule` | str | Que regla o LLM se uso |

### `CalibrationCurve` (entidad / tabla `calibration_curve`)

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `id` | UUID (PK) | |
| `model_version` | str | Hash del modelo isotonico |
| `created_at` | datetime | |
| `samples_count` | int | |
| `mappings` | json `list[tuple[float, float]]` | (raw_score, calibrated) |

---

---

## Manejo de errores trazables

### `StepError` (dataclass en `application/agents/pipeline/errors.py`)

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `workstream` | enum (`WS-A` ... `WS-E`) | WS que origino el fallo |
| `step_name` | str | Nombre del PipelineStep |
| `reason` | str | Mensaje accionable (no traceback) |
| `exception_type` | str | Clase del excepcion original |
| `context` | dict | Datos del contexto al momento del fallo (sin PII) |
| `occurred_at` | datetime | |
| `severity` | enum (`warning`, `error`) | `warning` permite continuar; `error` aborta el pipeline |

**Uso**: cada step que falla (LLM down, API externa no responde, schema
no valida) anade un `StepError` a `ToolLoopContext.errors`. El siguiente
step decide si puede continuar (degradacion controlada) o aborta. La
`FinalReport` incluye `errors[]` para auditoria. Cumple Manejo de Errores
Estricto de la constitucion: "cada error MUST propagarse o transformarse
con contexto util".

---

## Relaciones clave

- `AuthorReputation 1..* — SourceRef` (los autores producen fuentes).
- `Finding 1 — 1 ForensicTrace` (cada finding tiene su traza).
- `Finding 1..* — ImplicitAssumption` (asunciones detectadas por finding).
- `Finding 1..1 — ClaimExternalValidation` (fact-check opcional).
- `GoldenCase 1..* — GoldenCaseRun` (historial de ejecuciones).
- `CalibrationCurve` se entrena con `GoldenCaseRun.delta_vs_expected`.
- `CollaborationNetwork` reutiliza nodos del `KnowledgeGraph` (006).

---

## Tablas nuevas (resumen para migration alembic)

1. `author_reputation`
2. `temporal_decay_config`
3. `extraction_schema`
4. `golden_case`
5. `golden_case_run`
6. `calibration_curve`

`source_trust` (de spec 006) NO se modifica. `findings`, `branch_results`,
`reports` se extienden con columnas JSONB para entidades efimeras (ej:
`ClaimExternalValidation`, `ForensicTrace`) en lugar de tablas hijas
separadas, manteniendo el modelo simple (KISS).
