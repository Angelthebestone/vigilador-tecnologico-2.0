# Data Model: Vigilancia Tecnologica Multiagente

## 1. ResearchSession

**Purpose**: Contenedor principal de una investigacion completa.

**Fields**
- `id` (UUID, required)
- `created_at` (datetime, required)
- `updated_at` (datetime, required)
- `status` (enum, required): `DRAFT | CLARIFYING | PLANNING | APPROVED | EXECUTING | COMPLETED | FAILED | CANCELED`
- `user_query` (string, required, 10..4000 chars)
- `scope` (object, optional): geografia, horizonte temporal, dominio
- `clarification_set_id` (UUID, optional)
- `approved_plan_id` (UUID, optional)
- `final_report_id` (UUID, optional)
- `execution_time_seconds` (number, optional, >=0)
- `error_code` (string, optional)
- `error_message` (string, optional)

**Validation Rules**
- `status` must follow valid transitions.
- `approved_plan_id` required before moving to `EXECUTING`.
- `final_report_id` required for `COMPLETED`.

## 2. ClarificationSet

**Purpose**: Preguntas y respuestas usadas para reducir ambiguedad.

**Fields**
- `id` (UUID, required)
- `session_id` (UUID, required, FK -> ResearchSession.id)
- `questions` (array<Question>, required, min 1)
- `answers` (map<string,string>, optional until completed)
- `is_complete` (boolean, required)

**Validation Rules**
- Cada `answer` debe corresponder a un `question.id`.
- `is_complete=true` solo si todas las preguntas obligatorias tienen respuesta.

## 3. ResearchPlan

**Purpose**: Plan editable y aprobable para ejecucion por ramas.

**Fields**
- `id` (UUID, required)
- `session_id` (UUID, required, FK -> ResearchSession.id)
- `version` (int, required, >=1)
- `system_base_version` (string, required, default "1.0.0")
- `branches` (array<BranchConfig>, required, min 1)
- `global_constraints` (object, optional): `max_sources_per_branch`, `freshness`, `geographic_scope`, `depth_limit`, `breadth_cycles`, `temporal_policy`
- `requires_approval` (boolean, required, default true)
- `approved_at` (datetime, optional)

**Validation Rules**
- Cada `BranchConfig.branch_type` debe ser unico dentro del plan.
- Cada rama debe tener al menos 1 query de enfoque.

## 4. BranchConfig

**Purpose**: Configuracion de una rama especializada.

**Fields**
- `branch_type` (enum, required): `AVANCES | COMERCIAL | RIESGO | PI_NORMATIVA | COMPETITIVO | OPORTUNIDADES`
- `focus_queries` (array<string>, required, min 1, max 30)
- `mcp_providers` (array<string>, required, min 1)
- `mcp_tool_profile` (string, optional): perfil de herramientas habilitadas por rama/proveedor
- `priority_weight` (int, optional, 0..100)
- `overlay_ref` (string, optional)
- `status` (enum, required): `PENDING | RUNNING | COMPLETED | FAILED | SKIPPED`

## 5. BranchResult

**Purpose**: Resultado estructurado de una rama.

**Fields**
- `id` (UUID, required)
- `session_id` (UUID, required, FK -> ResearchSession.id)
- `branch_type` (enum, required)
- `started_at` (datetime, optional)
- `completed_at` (datetime, optional)
- `queries_executed` (array<string>, required)
- `iterations` (array<ResearchIteration>, optional)
- `findings` (array<Finding>, required)
- `sources` (array<SourceRef>, required)
- `semantic_relations` (array<SemanticIterationRelation>, optional)
- `coverage_score` (number, optional, 0..1)
- `confidence_score` (number, optional, 0..1)
- `provider_usage` (array<MCPExecutionLog>, optional)
- `errors` (array<string>, optional)

**Validation Rules**
- `completed_at` >= `started_at` when both present.
- `coverage_score` required if branch status is `COMPLETED`.

## 6. Finding

**Purpose**: Hallazgo puntual con trazabilidad.

**Fields**
- `id` (UUID, required)
- `branch_result_id` (UUID, required, FK -> BranchResult.id)
- `topic` (string, required)
- `statement` (string, required)
- `confidence` (number, required, 0..1)
- `source_ids` (array<UUID>, required, min 1)
- `tags` (array<string>, optional)

## 7. SourceRef

**Purpose**: Referencia de evidencia utilizada.

**Fields**
- `id` (UUID, required)
- `session_id` (UUID, required, FK -> ResearchSession.id)
- `url` (string, required, unique per session normalized)
- `title` (string, optional)
- `provider` (string, required)
- `branch_type` (enum, required)
- `accessed_at` (datetime, required)
- `content_hash` (string, optional)

**Validation Rules**
- Deduplicacion por `normalized_url` + `session_id`.

## 8. FinalReport

**Purpose**: Consolidado final de la investigacion.

**Fields**
- `id` (UUID, required)
- `session_id` (UUID, required, FK -> ResearchSession.id)
- `generated_at` (datetime, required)
- `executive_summary` (string, required)
- `branch_sections` (map<branch_type,string>, required)
- `cross_analysis` (string, required)
- `contradictions` (array<string>, optional)
- `opportunities` (array<string>, optional)
- `risks` (array<string>, optional)
- `recommendations` (array<Recommendation>, required)
- `all_source_ids` (array<UUID>, required)
- `metrics` (object, required): total_sources, total_findings, confidence_score

## 9. KnowledgeGraph

**Purpose**: Estructura navegable para exploracion semantica.

**Fields**
- `session_id` (UUID, required, PK/FK -> ResearchSession.id)
- `nodes` (array<GraphNode>, required)
- `edges` (array<GraphEdge>, required)
- `analytics` (object, optional): centralidad, clustering, paths

## 10. GraphNode

**Fields**
- `id` (UUID/string, required)
- `type` (enum, required): `TECHNOLOGY | CONCEPT | SOURCE | FINDING | BRAND | PATENT`
- `label` (string, required)
- `metadata` (object, optional)
- `embedding_id` (UUID, optional)

## 11. GraphEdge

**Fields**
- `id` (UUID/string, required)
- `source_node_id` (UUID/string, required)
- `target_node_id` (UUID/string, required)
- `relation_type` (enum, required): `REFERENCES | RELATED_TO | CITES | COMPETES_WITH | PARTNERS_WITH | DEPENDS_ON | SUCCEEDED_BY`
- `weight` (number, optional, >=0)

## 12. EmbeddingRecord

**Purpose**: Vector semantico para retrieval y linking de grafo.

**Fields**
- `id` (UUID, required)
- `session_id` (UUID, required, FK -> ResearchSession.id)
- `content_type` (enum, required): `FINDING | SOURCE | CONCEPT | QUERY`
- `content_ref_id` (UUID/string, required)
- `model` (string, required, default `gemini-embedding-2`)
- `dimensions` (int, required, default 768)
- `vector` (vector, required)
- `created_at` (datetime, required)

## 13. ResearchIteration

**Purpose**: Unidad de ejecucion iterativa dentro de una rama.

**Fields**
- `id` (UUID, required)
- `branch_result_id` (UUID, required, FK -> BranchResult.id)
- `iteration_index` (int, required, >=1)
- `query` (string, required)
- `query_type` (enum, required): `SEED | FOLLOW_UP`
- `started_at` (datetime, required)
- `completed_at` (datetime, optional)
- `needs_follow_up` (boolean, required)
- `next_query` (string, optional)
- `stop_reason` (enum, optional): `DEPTH_LIMIT | EVIDENCE_SATURATION | NO_FOLLOW_UP | ERROR`

## 14. SemanticIterationRelation

**Purpose**: Relacion semantica entre outputs de iteraciones.

**Fields**
- `id` (UUID, required)
- `session_id` (UUID, required)
- `branch_type` (enum, required)
- `source_iteration_id` (UUID, required)
- `target_iteration_id` (UUID, required)
- `relation_type` (enum, required): `SUPPORTS | CONTRADICTS | REFINES | DUPLICATES`
- `similarity_score` (number, required, 0..1)
- `evidence_overlap` (number, optional, 0..1)
- `created_at` (datetime, required)

## 15. MCPProvider

**Purpose**: Catalogo de proveedores MCP y sus capacidades operativas.

**Fields**
- `id` (UUID, required)
- `name` (string, required, unique)
- `transport` (enum, required): `STDIO | HTTP | STREAMABLE_HTTP`
- `base_url_or_command` (string, required)
- `auth_mode` (enum, required): `API_KEY | OAUTH | NONE`
- `enabled_tools` (array<string>, optional)
- `tool_filters` (object, optional): include/exclude tools o tags
- `timeout_ms` (int, required, >0)
- `retry_policy` (object, required): max_attempts, backoff
- `status` (enum, required): `ACTIVE | DEGRADED | DISABLED`

## 16. MCPExecutionLog

**Purpose**: Telemetria de llamadas MCP por sesion/rama.

**Fields**
- `id` (UUID, required)
- `session_id` (UUID, required, FK -> ResearchSession.id)
- `branch_type` (enum, required)
- `provider_name` (string, required)
- `tool_name` (string, required)
- `transport` (enum, required): `STDIO | HTTP | STREAMABLE_HTTP`
- `request_fingerprint` (string, required)
- `latency_ms` (int, required, >=0)
- `attempt_count` (int, required, >=1)
- `result_status` (enum, required): `SUCCESS | RETRY | FAILED | TIMEOUT`
- `error_code` (string, optional)
- `created_at` (datetime, required)

## 17. AgentSkillPolicy

**Purpose**: Matriz de herramientas MCP por agente/rama.

**Fields**
- `id` (UUID, required)
- `branch_type` (enum, required, unique)
- `allowed_tools` (array<string>, required)
- `tool_order` (array<string>, required)
- `timeout_ms_per_tool` (object, required)
- `retry_limit_per_tool` (object, required)
- `substitution_policy` (string, required, fixed: `none`)
- `version` (string, required)

## 18. AgentPromptContract

**Purpose**: Contrato versionado de prompt por agente.

**Fields**
- `id` (UUID, required)
- `branch_type` (enum, required)
- `objective` (string, required)
- `required_context` (array<string>, required)
- `output_schema` (object, required)
- `quality_criteria` (array<string>, required)
- `do_rules` (array<string>, required)
- `dont_rules` (array<string>, required)
- `uncertainty_handling` (string, required)
- `version` (string, required)

## 19. SessionArtifactManifest

**Purpose**: Inventario de artefactos por sesion y agente.

**Fields**
- `id` (UUID, required)
- `session_id` (UUID, required)
- `artifact_path` (string, required)
- `artifact_type` (enum, required): `PROMPT | TRACE | RAW_RESULTS | FINDINGS | REPORT | GRAPH | METRICS`
- `produced_by` (string, required)
- `naming_pattern` (string, required)
- `retention_days` (int, required, >=1)
- `version` (string, required)

## 20. BranchEvaluation

**Purpose**: Evaluacion operativa por rama.

**Fields**
- `id` (UUID, required)
- `session_id` (UUID, required)
- `branch_type` (enum, required)
- `coverage_kpi` (number, required, 0..1)
- `precision_kpi` (number, required, 0..1)
- `latency_ms_kpi` (number, required, >=0)
- `cost_kpi` (number, required, >=0)
- `prompt_regression_passed` (boolean, required)
- `golden_case_id` (string, optional)
- `evaluated_at` (datetime, required)

## 21. SystemBase

**Purpose**: Configuracion base del sistema multiagente.

**Fields**
- `version` (string, required)
- `global_rules` (array<string>, required)
- `tool_usage_policy` (object, required)
- `safety_limits` (object, required)
- `error_handling` (array<string>, required)
- `output_style` (array<string>, required)
- `model_behavior` (object, required)
- `embedding_config` (object, optional)

## 22. BranchOverlay

**Purpose**: Overlay de reglas especificas por tipo de rama.

**Fields**
- `branch_type` (enum, required)
- `objective` (string, required)
- `required_context` (array<string>, required)
- `output_schema` (object, required)
- `quality_criteria` (array<string>, required)
- `do_rules` (array<string>, required)
- `dont_rules` (array<string>, required)
- `uncertainty_handling` (string, required)
- `version` (string, required)

## 23. ComposedPrompt

**Purpose**: Prompt compuesto a partir de SystemBase + BranchOverlay + user query.

**Fields**
- `system_base_version` (string, required)
- `branch_type` (enum, required)
- `user_query` (string, required)
- `sections` (object, required)
- `full_text` (string, required)
- `prompt_composition_id` (string, required for traceability)

## Relationships Summary

- `ResearchSession 1 - N ResearchPlan`
- `ResearchSession 1 - 1 ClarificationSet`
- `ResearchSession 1 - N BranchResult`
- `BranchResult 1 - N Finding`
- `ResearchSession 1 - N SourceRef`
- `ResearchSession 1 - 1 FinalReport`
- `ResearchSession 1 - 1 KnowledgeGraph`
- `ResearchSession 1 - N EmbeddingRecord`
- `BranchResult 1 - N ResearchIteration`
- `ResearchSession 1 - N SemanticIterationRelation`
- `ResearchSession 1 - N MCPExecutionLog`
- `MCPProvider 1 - N MCPExecutionLog`
- `ResearchSession 1 - N AgentPromptContract`
- `ResearchSession 1 - N SessionArtifactManifest`
- `ResearchSession 1 - N BranchEvaluation`
- `SystemBase 1 - N ComposedPrompt`
- `BranchOverlay 1 - N ComposedPrompt`

## Session State Transitions

1. `DRAFT -> CLARIFYING`
2. `CLARIFYING -> PLANNING`
3. `PLANNING -> APPROVED` (after user approval)
4. `APPROVED -> EXECUTING`
5. `EXECUTING -> COMPLETED | FAILED`
6. `ANY NON-TERMINAL -> CANCELED`

## Storage Line

- Persistencia oficial: `Postgres + pgvector`.
- El grafo de conocimiento y sus analytics se guardan como snapshots JSON por sesion, sobre el mismo backend de Postgres.

