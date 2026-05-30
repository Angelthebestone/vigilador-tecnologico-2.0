# F0 — Matriz de Migración: Preservar / Extender / Nuevo

**Fuente**: `plan vigilador 3.0/07-migracion-2.0-a-3.0.md` (secciones A, B, C)
**Fecha**: 2026-05-29
**Principio rector**: cero breaking changes al 2.0.

---

## A. PRESERVAR intacto

Estos componentes NO se tocan. El 3.0 los reutiliza vía sus interfaces actuales (DIP).

| Componente | Ubicación | Razón | Existe en repo |
|---|---|---|---|
| OrchestratorService | `application/orchestration/orchestrator_service.py` | Lifecycle de sesiones del 2.0; el 3.0 lo invoca para playbook `technology-watch` | ✅ |
| BranchCoordinator | `application/execution/branch_coordinator.py` | Ejecución paralela de 6 ramas. Núcleo del 2.0 | ✅ |
| BaseBranchAgent | `application/agents/base.py` | Clase base de los 6 agentes | ✅ |
| 6 agentes de rama | `application/agents/{avances,comercial,riesgo,pi_normativa,competitivo,oportunidades}_agent.py` | Lógica de dominio del 2.0 | ✅ |
| PromptComposer | `application/governance/prompt_composer.py` | SystemBase + BranchOverlay composition | ✅ |
| ContractLoader (AgentSkillPolicy) | `application/governance/contract_loader.py` | Per-branch tool order/timeouts/retry | ✅ |
| MCPExecutionClient + cache | `infra/mcp/execution_client.py`, `infra/mcp/mcp_cache.py` | Ejecución de los 15 MCPs actuales | ✅ |
| 15 MCP providers actuales | `infra/mcp/mcp-providers.json` + carpetas | tavily, exa, jina, brave, firecrawl, serper, google_scholar, arxiv, fetch, sandbox, markitdown, minimax-image, openalex, playwright | ✅ |
| Sistema de governance overlays | `application/governance/contract_loader.py:_BRANCH_OVERLAYS` | Hardcoded dict del 2.0 | ✅ |
| CrossSessionService | `application/memory/cross_session_service.py` | Preload + merge de sesiones | ✅ |
| Evaluation framework | `application/evaluation/*` | 9 sub-módulos de eval del 2.0 | ✅ |
| Workstreams WS-A..WS-E | `application/evaluation/ws_a/` a `ws_e/` | No se reemplazan por playbooks | ✅ |
| Pipeline de agentes | `application/agents/pipeline/` | Pasos de WSA-WSE, deep analysis, data intelligence | ✅ |
| Artifacts | `application/artifacts/*` | Manifest y registro de artefactos | ✅ |
| Observability | `application/observability/*` | Metrics service | ✅ |
| TrendForecaster | `application/forecasting/trend_forecaster.py` | Proyección de tendencias | ✅ |
| KnowledgeGraphService | `application/graph/knowledge_graph_service.py` | NetworkX analytics | ✅ |
| SourceScorer | `application/routing/source_scorer.py` | Source trust scoring | ✅ |
| API routes existentes | `api/routes/*.py` | `/api/v2/research/*` sin cambios | ✅ |
| Frontend React actual | `frontend/src/` | Cero cambios mandatorios | ✅ |
| Ports de dominio | `domain/ports/*` | Contratos base para adapters 3.0 | ✅ |
| Infra existente | `infra/mcp`, `infra/embeddings`, `infra/reranking`, `infra/persistence`, `infra/llm` | Se envuelve/extiende, no se reemplaza | ✅ |
| Tests existentes | `tests/` | Deben seguir pasando 100% en cada fase | ✅ |

---

## B. EXTENDER (OCP — sin tocar lo existente)

Nueva subclase o nuevo parámetro opcional con default seguro.

| Componente | Tipo de extensión | Fase | Punto de extensión |
|---|---|---|---|
| BranchOverlay (`domain/system_base.py`) | Subclase `DomainProfile` | F4a | Herencia: `DomainProfile(BranchOverlay)` |
| Port `VectorIndex` | Nuevo adapter `TurboVecIndex` | F2 | Implementa port existente |
| MiniMaxClient (`infra/llm/minimax_client.py`) | Adapter por modelo/proveedor | F1 | Parámetro `model` con default |
| Port `EmbeddingGateway` | Adapters seleccionables (Gemini + local opcional) | F2 | Implementa port existente |
| Port `Reranker` | Adapters seleccionables (Cohere + local opcional) | F2 | Implementa port existente |
| AgentSkillPolicy (`contract_loader.py`) | Carga adicional desde `config/modes/` | F4a | Segundo loader sin tocar el primero |
| MCPProviderRegistry | Carga adicional desde `config/mcp/external.yaml` | F3a | Namespaces distintos (`mcp_ext.*`) |
| PromptComposer | Soporte SOUL + COMPANY frozen snapshot | F4a | Condicional: solo si Mode activo |
| LanguageRouter (nuevo, extiende PromptComposer) | Detecta locale por turno | F1 | Default inglés (comportamiento 2.0) |

---

## C. CREAR NUEVO en `enterprise/`

Todo bajo `src/vigilancia_multiagente/enterprise/`. Cero acoplamiento mandatorio con `application/`.

| Componente | Ubicación destino | Fase | Dependencias preservadas |
|---|---|---|---|
| orchestration/ (complexity_classifier, playbook_runner, subagent_registry, debate_coordinator, crewai_bridge, goal_pursuit/) | enterprise/orchestration/ | F4a (MVP), F4b (avanzado) | OrchestratorService, BranchCoordinator |
| modes/ (mode_loader, mode_registry, mode_resolver) | enterprise/modes/ | F4a | PromptComposer, ContractLoader |
| skills_marketplace/ (k_dense_adapter, agency_agents_adapter, skill_loader, skill_curator) | enterprise/skills_marketplace/ | F5b | — |
| intelligence/ (self_correction, cove_verifier, confidence_scorer, fewshot_retriever) | enterprise/intelligence/ | F4b | — |
| triggers/ (event_listener, webhook_handler) | enterprise/triggers/ | F4b | — |
| auth/ (oauth_manager, token_auth, device_token, capability_tokens) | enterprise/auth/ | F1 | — |
| governance/ (file_safety, redact, path_security, url_safety, website_policy, pii_redactor, language_router, forget_user, prompt_injection_detector, anomaly_detector, agent_modifier, approval_queue) | enterprise/governance/ | F1 (base), F5a/F5b (avanzado) | — |
| memory/ (frozen_snapshot, context_compressor, fts_search) | enterprise/memory/ | F2 | CrossSessionService |
| observability/ (metrics, dashboard, health_monitor) | enterprise/observability/ | F1 | application/observability |
| ingestion/ (orchestrator, connectors/*, chunking, dedup, acl_resolver) | enterprise/ingestion/ | F2 | — |
| optimization/ (standard_mapper, gap_analyzer, evidence_matrix, improvement_planner) | enterprise/optimization/ | F4b | — |
| artifacts/ (artifact_registry, dashboard_builder, pipeline_builder, metric_contracts) | enterprise/artifacts/ | F4b | application/artifacts |
| tooling/ (tool_registry, tool_schema_loader, parallel_dispatcher, local_app_detector, adaptive_cache, output_formatter, builtin/*) | enterprise/tooling/ | F1 (registry), F3a/F3b (tools) | MCPExecutionClient |
| dreaming/ (scheduler, phases, tasks/*, reporter) | enterprise/dreaming/ | F5a (básico), F5b (loops) | — |
| mcp/ (process_supervisor, healthcheck, admin_cli) | enterprise/mcp/ | F3a | MCPProviderRegistry |

---

## Verificación de integridad

- **PRESERVAR**: todos los componentes listados existen físicamente en el repositorio (verificado contra estructura `src/vigilancia_multiagente/`).
- **EXTENDER**: cada componente tiene punto de extensión identificado (port, clase base o parámetro opcional).
- **CREAR NUEVO**: ubicaciones destino definidas; ninguna colisiona con archivos existentes del 2.0.
