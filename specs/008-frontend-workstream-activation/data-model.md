# Data Model: Activación de Workstreams desde Frontend

> Todas las entidades de dominio (AuthorReputation, SCurveProjection, BiasAudit, etc.) ya están definidas en spec 007 `data-model.md`. Este documento define solo las entidades NUEVAS introducidas por spec 008.

## WorkstreamConfig

Configuración de activación de workstreams. Fuente de verdad: `config/workstream_overrides.json` > `.env`.

| Field | Type | Description |
|-------|------|-------------|
| `ws_a` | `bool` | Source Quality activo (default `false`) |
| `ws_b` | `bool` | Data Intelligence activo (default `false`) |
| `ws_c` | `bool` | Deep Analysis activo (default `false`) |
| `ws_d` | `bool` | Strategic Signals activo (default `false`) |
| `ws_e` | `bool` | Output Assurance activo (default `false`) |

**Resolution order**: `workstream_overrides.json[ws_x]` ?? `settings.eval_ws_x_enabled` ?? `False`

**Persistence**: `config/workstream_overrides.json` — JSON plano con claves booleanas. Solo se guardan los valores modificados explícitamente.

---

## PromptTemplate

Metadatos de un template de prompt de evaluación.

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Nombre del template (ej. `assumption_detection`) |
| `modified` | `bool` | `true` si existe override en `config/prompt_overrides/` |
| `size` | `int` | Tamaño en bytes del contenido actual |
| `content` | `str` | Contenido completo del template (solo en GET individual) |

**Resolution order**: `config/prompt_overrides/{name}.txt` ?? `prompts/evaluation/{name}.txt`

**Persistence**: Archivos `.txt` individuales en `config/prompt_overrides/`. El restore simplemente elimina el archivo.

---

## SessionEvaluation

Agregado de resultados de workstreams para una sesión de investigación. Incluido en `FinalReport.evaluation` y disponible en `GET /research/{id}/evaluation`.

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | `UUID` | ID de la sesión |
| `ws_a` | `WsaResult \| null` | Resultados de Source Quality, `null` si no activo |
| `ws_b` | `WsbResult \| null` | Resultados de Data Intelligence |
| `ws_c` | `WscResult \| null` | Resultados de Deep Analysis |
| `ws_d` | `WsdResult \| null` | Resultados de Strategic Signals |
| `ws_e` | `WseResult \| null` | Resultados de Output Assurance |
| `active_workstreams` | `list[str]` | Lista de workstreams que estuvieron activos (ej. `["ws_a", "ws_e"]`) |

### WsaResult

| Field | Type | Description |
|-------|------|-------------|
| `author_reputations` | `list[AuthorReputation]` | Reputación por autor encontrado |
| `conflicts_of_interest` | `list[ConflictOfInterest]` | Conflictos detectados |
| `external_validations` | `list[ClaimExternalValidation]` | Fact-checks externos |
| `retraction_records` | `list[RetractionRecord]` | DOIs retractados |
| `reproducibility_scores` | `list[ReproducibilityScore]` | Scores de reproducibilidad |
| `effective_freshness` | `list[float]` | Decay temporal aplicado por fuente |

### WsbResult

| Field | Type | Description |
|-------|------|-------------|
| `hybrid_search_stats` | `dict` | `{ total_queries, bm25_hits, embedding_hits, combined_hits }` |
| `dedup_rate` | `float` | Tasa de deduplicación (0.0–1.0) |
| `deduped_sources` | `list[DedupedSource]` | Fuentes canónicas post-dedup |
| `authenticity_signals` | `list[ContentAuthenticitySignal]` | Señales de autenticidad por fuente |
| `consensus_disputes` | `list[ConsensusDisputeEntry]` | Mapa de consenso/disputa |

### WscResult

| Field | Type | Description |
|-------|------|-------------|
| `s_curves` | `list[SCurveProjection]` | Proyecciones de curva-S por tecnología |
| `meta_analyses` | `list[MetaAnalysisResult]` | Resultados de meta-análisis |
| `implicit_assumptions` | `list[ImplicitAssumption]` | Asunciones implícitas detectadas |
| `counterfactuals` | `list[CounterfactualScenario]` | Escenarios contrafactuales |
| `critical_dependencies` | `list[CriticalDependency]` | Dependencias críticas mapeadas |

### WsdResult

| Field | Type | Description |
|-------|------|-------------|
| `convergence_clusters` | `list[ConvergenceCluster]` | Clusters de convergencia |
| `collaboration_network` | `list[CollaborationNetwork]` | Redes de colaboración |
| `idea_lineages` | `list[IdeaLineage]` | Linajes de ideas |
| `narrative_shifts` | `list[NarrativeShift]` | Cambios de narrativa |
| `talent_mobilities` | `list[TalentMobility]` | Movilidad de talento |
| `patenting_gaps` | `list[PatentingGap]` | Brechas de patentamiento |

### WseResult

| Field | Type | Description |
|-------|------|-------------|
| `bias_audit` | `BiasAudit` | Resultado de auditoría de sesgo |
| `forensic_traces` | `list[ForensicTrace]` | Trazas forenses por claim |
| `stakeholder_simulations` | `list[StakeholderSimulation]` | Simulaciones de stakeholders |
| `falsification_scenarios` | `list[FalsificationScenario]` | Escenarios de falsificación |
| `calibration_curve` | `CalibrationCurve \| null` | Curva de calibración (null si <5 muestras) |
| `quality_gate_passed` | `bool` | Si el quality gate permitió continuar |
| `calibrated_confidence` | `float \| null` | Confianza calibrada final |

---

## WorkstreamHealth

Estado de disponibilidad de dependencias externas.

| Field | Type | Description |
|-------|------|-------------|
| `ws_a` | `HealthStatus` | Estado de servicios WS-A |
| `ws_b` | `HealthStatus` | Estado de servicios WS-B |
| `ws_c` | `HealthStatus` | Estado de servicios WS-C |
| `ws_d` | `HealthStatus` | Estado de servicios WS-D |
| `ws_e` | `HealthStatus` | Estado de servicios WS-E |

### HealthStatus

| Field | Type | Description |
|-------|------|-------------|
| `available` | `bool` | Si el workstream puede ejecutarse |
| `missing_dependencies` | `list[str]` | Dependencias faltantes (ej. `["google_factcheck_api_key"]`) |
| `degraded_services` | `list[str]` | Servicios degradados (ej. `["openalex_timeout"]`) |

---

## Mock Entities (solo mock server)

### MockScenario

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | `str` | ID de sesión simulado |
| `branches` | `dict[str, list[MockIteration]]` | Iteraciones por rama |
| `workstream_data` | `SessionEvaluation` | Datos de workstreams simulados |
| `report` | `FinalReport` | Reporte final simulado |

### MockIteration

| Field | Type | Description |
|-------|------|-------------|
| `step_number` | `int` | Número de paso (1-based) |
| `reasoning` | `str` | Cadena de razonamiento simulada |
| `tool_call` | `MockToolCall` | Tool call simulada |
| `result` | `str` | Finding sintetizado |
| `confidence` | `float` | Confianza simulada |

### MockToolCall

| Field | Type | Description |
|-------|------|-------------|
| `tool` | `str` | Nombre de la tool (tavily, exa, brave, etc.) |
| `query` | `str` | Query enviada a la tool |
| `payload` | `dict` | Payload simulado de la tool call |
| `result` | `str` | Resultado simulado (texto o JSON string) |
