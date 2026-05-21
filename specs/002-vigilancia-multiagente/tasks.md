# Tasks: Backend Closure vs SPEC_V2

**Input**: `specs/002-vigilancia-multiagente/spec.md`, `plan.md`, `data-model.md`, `research.md`, `contracts/`, `quickstart.md`  
**Feature**: Vigilancia Tecnologica Multiagente

## Phase 1: Setup (Project Initialization)

- [X] T001 Update API router base strategy for `/api/v2` compatibility in `src/vigilancia_multiagente/api/router.py`
- [X] T002 [P] Add backend test package scaffold in `tests/__init__.py`
- [X] T003 [P] Add test fixtures and shared session helpers in `tests/conftest.py`
- [X] T004 [P] Add MCP production manifest baseline aligned to runtime environments in `specs/002-vigilancia-multiagente/contracts/mcp-providers.json`
- [X] T005 [P] Add backend closure execution notes in `specs/002-vigilancia-multiagente/quickstart.md`

## Phase 2: Foundational (Blocking Prerequisites)

- [X] T006 Add API v2 request/response DTOs for graph analytics and path search in `src/vigilancia_multiagente/api/routes/research_governance.py`
- [X] T007 Add graph analytics domain contracts (centrality, clusters, path result, semantic search hit) in `src/vigilancia_multiagente/domain/models.py`
- [X] T008 Add graph persistence query contracts for nodes/edges/analytics retrieval in `src/vigilancia_multiagente/domain/repositories.py`
- [X] T009 Extend Postgres persistence for graph-node, graph-edge and analytics snapshots in `src/vigilancia_multiagente/infra/persistence/postgres_repositories.py`
- [X] T010 Add migration for graph analytics storage and indices in `src/vigilancia_multiagente/infra/db/migrations/002_graph_analytics.sql`
- [X] T011 [P] Add graph algorithm dependency declarations in `pyproject.toml`
- [X] T012 Add MCP runtime validation for manifest completeness and provider readiness in `src/vigilancia_multiagente/infra/mcp/provider_registry.py`

## Phase 3: User Story 1 (P1) - API v2 parity, advanced graph analytics, and production closure

**Goal**: Entregar backend conforme a `SPEC_V2.md` con API `/api/v2`, paquete de grafo avanzado (centralidad, clustering, DFS/BFS, Dijkstra, búsqueda semántica), runtime MCP productivo y cobertura de pruebas backend.  
**Independent Test Criteria**: Desde una sesión iniciada, el backend expone rutas `/api/v2/research/*` con respuestas de plan/modify/report/graph; calcula y entrega analytics de grafo, shortest-path y búsqueda semántica; y pasa suite de orquestador, MCP integration y flujo e2e.

- [X] T013 [US1] Add `/api/v2/research/start` and `/api/v2/research/{session_id}/clarify` route aliases in `src/vigilancia_multiagente/api/routes/research_start_clarify.py`
- [X] T014 [US1] Add `/api/v2/research/{session_id}/plan` retrieval endpoint in `src/vigilancia_multiagente/api/routes/research_start_clarify.py`
- [X] T015 [US1] Add `/api/v2/research/{session_id}/modify` endpoint and plan version bump logic in `src/vigilancia_multiagente/api/routes/research_approve.py`
- [X] T016 [US1] Add `/api/v2/research/{session_id}/report`, `/sources`, `/stream` endpoints under v2 router in `src/vigilancia_multiagente/api/routes/research_outputs.py`
- [X] T017 [US1] Add `/api/v2/research/{session_id}/graph/nodes` and `/graph/edges` endpoints in `src/vigilancia_multiagente/api/routes/research_outputs.py`
- [X] T018 [US1] Add `/api/v2/research/{session_id}/graph/analytics` endpoint in `src/vigilancia_multiagente/api/routes/research_outputs.py`
- [X] T019 [US1] Add `/api/v2/research/{session_id}/graph/path` endpoint for shortest path queries in `src/vigilancia_multiagente/api/routes/research_outputs.py`
- [X] T020 [US1] Add `/api/v2/research/{session_id}/graph/search` semantic lookup endpoint in `src/vigilancia_multiagente/api/routes/research_outputs.py`
- [X] T021 [US1] Implement graph traversal algorithms (DFS/BFS) in `src/vigilancia_multiagente/application/graph/knowledge_graph_service.py`
- [X] T022 [US1] Implement shortest path computation (Dijkstra) in `src/vigilancia_multiagente/application/graph/knowledge_graph_service.py`
- [X] T023 [US1] Implement graph centrality metrics computation in `src/vigilancia_multiagente/application/graph/knowledge_graph_service.py`
- [X] T024 [US1] Implement graph clustering (Leiden) pipeline in `src/vigilancia_multiagente/application/graph/knowledge_graph_service.py`
- [X] T025 [US1] Implement graph layout/position generation for visualization in `src/vigilancia_multiagente/application/graph/knowledge_graph_service.py`
- [X] T026 [US1] Implement graph semantic search against pgvector embeddings in `src/vigilancia_multiagente/application/graph/knowledge_graph_service.py`
- [X] T027 [US1] Persist generated graph analytics snapshots after report generation in `src/vigilancia_multiagente/api/routes/research_approve.py`
- [X] T028 [US1] Replace MCP placeholder defaults with environment-ready provider bootstrap in `src/vigilancia_multiagente/api/dependencies.py`
- [X] T029 [US1] Add MCP runtime readiness checks before branch execution in `src/vigilancia_multiagente/application/execution/branch_coordinator.py`
- [X] T030 [US1] Add operation-level telemetry enrichment (tool retries/errors/latency buckets) in `src/vigilancia_multiagente/application/observability/metrics_service.py`
- [X] T031 [US1] Add storage-line consistency update (Postgres+pgvector vs Supabase) in `specs/002-vigilancia-multiagente/research.md`
- [X] T032 [US1] Add storage-line consistency update in `specs/002-vigilancia-multiagente/data-model.md`
- [X] T033 [US1] Add storage-line consistency update in `specs/002-vigilancia-multiagente/contracts/research-api.yaml`

## Phase 4: Polish & Cross-Cutting Concerns

- [X] T034 [P] Implement orchestrator unit coverage in `tests/test_orchestrator.py`
- [X] T035 [P] Implement MCP integration tests in `tests/test_mcp_integration.py`
- [X] T036 [P] Implement end-to-end flow tests in `tests/test_e2e_flow.py`
- [X] T037 Implement prompt regression gate assertions with thresholds in `tests/test_prompt_regression.py`
- [X] T038 Implement golden cases validation with pass/fail thresholds in `tests/test_golden_cases.py`
- [X] T039 Implement graph analytics contract tests for `/api/v2/research/*/graph/*` in `tests/test_graph_api_contract.py`
- [X] T040 Update startup and runtime health metadata endpoints for backend closure reporting in `src/vigilancia_multiagente/api/app.py`
- [X] T041 Update deployment instructions and backend closure checklist in `specs/002-vigilancia-multiagente/quickstart.md`
- [X] T042 Update task execution evidence footer with closure validation outputs in `specs/002-vigilancia-multiagente/tasks.md`

## Phase 5: System Base Standardization — Gap Remediation

**Goal**: Cerrar las 8 brechas entre el plan `plan-system-base.md` y la implementación real detectadas en la auditoría post-implementación.
**Independent Test Criteria**: Cada GAP se valida independientemente: deprecation warning visible en runtime, composed prompts con ID traceable, feature flag controla el flujo, contracts OpenAPI sirven los 2 nuevos endpoints, eventos SSE reflejan versionamiento, modelo de datos documenta las 3 nuevas entidades, quickstart y research docs cubren el pipeline, tests de regresión pasan con composed prompts.

- [X] T043 Add `warnings.warn(DeprecationWarning)` to `contract_loader.load_prompt_template()` in `src/vigilancia_multiagente/application/governance/contract_loader.py`
- [X] T044 Add `prompt_composition_id` (UUID) field to `ComposedPrompt` dataclass in `src/vigilancia_multiagente/domain/system_base.py`
- [X] T045 [P] Generate `prompt_composition_id` via `uuid4()` in `PromptComposer.compose()` in `src/vigilancia_multiagente/application/governance/prompt_composer.py`
- [X] T046 [P] Pass `prompt_composition_id` in MCP `execute_tool()` arguments dict in `src/vigilancia_multiagente/application/agents/base.py`
- [X] T047 Add `system_base_enabled: bool = True` feature flag (`VT_SYSTEM_BASE_ENABLED`) to `src/vigilancia_multiagente/config/settings.py`
- [X] T048 Gate `system_base` and `prompt_composer` DI on `system_base_enabled` flag in `src/vigilancia_multiagente/api/dependencies.py` — when False, pass None (fallback to old PromptContract path)
- [X] T049 Return `501 Not Implemented` on `/system-base` and `/system-base/composed-prompt/*` when `system_base_enabled` is False in `src/vigilancia_multiagente/api/routes/system_base.py`
- [X] T050 Update `ComposedPrompt` and `prompt_composition_id` in `tests/test_prompt_composer.py` and `tests/test_system_base_contract.py`
- [X] T051 Update `research-api.yaml` — add `GET /system-base`, `GET /system-base/composed-prompt/{session_id}/{branch_type}`, add `system_base_version` to `PlanResponse`, add `overlay_ref` to `BranchConfig`, add `SystemBaseResponse` and `ComposedPromptResponse` schemas in `specs/002-vigilancia-multiagente/contracts/research-api.yaml`
- [X] T052 Update `PromptContractApplied` event to include `system_base_version`, `prompt_composition_id`, `overlay_version` and add `SystemBaseLoaded` event in `specs/002-vigilancia-multiagente/contracts/sse-events.md`
- [X] T053 [P] Add entities 21 (SystemBase), 22 (BranchOverlay), 23 (ComposedPrompt) and add `system_base_version` field to ResearchPlan, `overlay_ref` field to BranchConfig in `specs/002-vigilancia-multiagente/data-model.md`
- [X] T054 [P] Add "System Base Pipeline" section to `specs/002-vigilancia-multiagente/quickstart.md`
- [X] T055 Add Decision 20 (System Base Standardization) to `specs/002-vigilancia-multiagente/research.md`
- [X] T056 [P] Add composed prompt regression tests per branch type in `tests/test_prompt_regression.py`
- [X] T057 [P] Add golden case using `PromptComposer.compose()` in `tests/test_golden_cases.py`
- [X] T058 Add rollout phase comments to source files: `base.py`, `contract_loader.py`, `system_base.py` routes, `dependencies.py`

## Phase 6: MCP Installation & Verification

**Goal**: Instalar, configurar y verificar los 7 providers MCP (Tavily, Exa, Jina, Brave, Firecrawl, Google Scholar, ArXiv) e integrar Serper como REST API, reemplazando los placeholders `example-*.local` por conectividad real.
**Independent Test Criteria**: Cada provider MCP responde a `initialize` con las tools esperadas y ejecuta la tool más simple sin error. Serper REST responde HTTP 200. `mcp-providers.json` usa URLs reales. `python -m pytest -q` pasa 43+ tests.

### Fase 6.1 — Runtime & Environment

- [X] T059 Upgrade Node.js to v20+ (needed by Brave Search MCP) via `node --version` verification
- [X] T060 Install `uv` package manager (`pip install uv`) for ArXiv MCP
- [X] T061 Add API keys to `.env` — `TAVILY_API_KEY`, `EXA_API_KEY`, `JINA_API_KEY`, `BRAVE_API_KEY`, `FIRECRAWL_API_KEY`, `SERPER_API_KEY`

### Fase 6.2 — MCP Installation (Parallelizable per provider)

- [X] T062 [P] Install & verify Tavily MCP (`npx -y tavily-mcp@latest` with `TAVILY_API_KEY`)
- [X] T063 [P] Install & verify Exa MCP (remote `https://mcp.exa.ai/mcp`)
- [X] T064 [P] Install & verify Jina MCP (remote `https://mcp.jina.ai/v1` + Bearer token)
- [X] T065 [P] Install & verify Brave MCP (`npx -y @brave/brave-search-mcp-server --transport stdio`)
- [X] T066 [P] Install & verify Firecrawl MCP (`npx -y firecrawl-mcp`)
- [X] T067 [P] Install & verify Google Scholar MCP (`pip install scholarly` + `python google_scholar_server.py`)
- [X] T068 [P] Install & verify ArXiv MCP (`pip install arxiv-mcp-server`)

### Fase 6.3 — Serper REST Integration (no es MCP)

- [X] T069 [P] Add `SERPER_API_KEY` to `.env` and verify REST endpoints respond HTTP 200: `POST https://google.serper.dev/{news|patents|scholar}` with `X-API-KEY` header
- [X] T070 Create Serper REST service wrapper in `src/vigilancia_multiagente/infra/serper/serper_client.py` — HTTP calls via `httpx` replacing deprecated `requests` scripts

### Fase 6.4 — Smoke Tests por Provider (Parallelizable)

- [X] T071 [P] Smoke test Tavily: `tavily_search` tool returns results for a test query
- [X] T072 [P] Smoke test Exa: `web_search_exa` tool returns results for a test query
- [X] T073 [P] Smoke test Jina: `read_url` tool fetches and returns markdown from a known URL
- [X] T074 [P] Smoke test Brave: `brave_web_search` tool returns results for a test query
- [X] T075 [P] Smoke test Firecrawl: `firecrawl_scrape` tool extracts content from a known URL
- [X] T076 [P] Smoke test Google Scholar: `search_google_scholar_key_words` tool searches for a test paper
- [X] T077 [P] Smoke test ArXiv: `search_papers` tool searches for a test paper
- [X] T078 [P] Smoke test Serper: Serper REST client hits `POST /news` and returns parsed JSON

### Fase 6.5 — Integración con el Proyecto

- [X] T079 Update `specs/002-vigilancia-multiagente/contracts/mcp-providers.json` — replace all `example-*.local` URLs with real MCP endpoints and API key refs
- [X] T080 Update `specs/002-vigilancia-multiagente/contracts/agent-governance.md` — document tool lists matching installed MCPs (via checklists/mcp-verification-plan.md)
- [X] T081 Run full test suite `python -m pytest -q` — verify all 43+ tests pass with real MCP endpoints
- [X] T082 Verify `GET /api/v2/system-base` and `GET /api/v2/health` return correct metadata with MCP providers active

## Phase 7: Code Health — Dead Code, Verificaciones, Token Limit y System Base por Agente

**Goal**: Eliminar código muerto (30+ items), corregir verificaciones innecesarias, subir token limit de 2048 a 100000, y extender el composed prompt con la skill matrix de cada agente para que cada subagente conozca exactamente sus tools MCP.
**Independent Test Criteria**: `python -m pytest -q` pasa 43+ tests después de cada bloque de cambios. El composed prompt incluye sección "Tools Disponibles" con orden, timeout, retry y fallback.

### Fase 7.1 — Token Limit + Bug Fix

- [X] T083 Raise max tokens from 2048 to 100000 in `specs/002-vigilancia-multiagente/contracts/system-base.md` (line 45: `**Max tokens**: 2048 → 100000`)
- [X] T084 Fix undefined variable `bt` in `src/vigilancia_multiagente/application/governance/prompt_composer.py` — replace `overlay.branch_type if overlay is not None else bt` with `overlay.branch_type`

### Fase 7.2 — Dead Code: Módulos y Clases (Parallelizable)

- [X] T085 [P] Remove orphaned module `src/vigilancia_multiagente/infra/serper/serper_client.py` (148 lines, never imported)
- [X] T086 [P] Remove orphaned DTOs (`GraphPathRequest`, `GraphSearchRequest`, `GraphCentralityDTO`, `GraphClusterDTO`, `GraphAnalyticsResponse`, `GraphPathResponse`, `GraphSearchHitDTO`, `GraphSearchResponse`) from `src/vigilancia_multiagente/api/routes/research_governance.py`
- [X] T087 [P] Remove orphaned re-exports from `src/vigilancia_multiagente/infra/llm/__init__.py`
- [X] T088 [P] Remove unused function `is_terminal()` from `src/vigilancia_multiagente/domain/session_state.py`

### Fase 7.3 — Dead Code: Imports No Usados (8 subagentes en paralelo)

- [X] T089 [P] Remove unused imports in `src/vigilancia_multiagente/api/dependencies.py` (`MCPAuthMode`, `MCPProviderConfig`, `MCPTransport`, `RetryPolicy`)
- [X] T090 [P] Remove unused import `Path` from `src/vigilancia_multiagente/api/routes/research_approve.py`
- [X] T091 [P] Remove unused import `VectorRecord` from `src/vigilancia_multiagente/api/routes/research_outputs.py`
- [X] T092 [P] Remove unused imports (`branch_kpi_service`, `golden_cases_runner`, `plan_repository`, `BaseModel`, `Field`) from `src/vigilancia_multiagente/api/routes/research_governance.py`
- [X] T093 [P] Remove unused import `branch_coordinator` from `src/vigilancia_multiagente/api/routes/system_base.py`
- [X] T094 [P] Remove unused import `atan2` from `src/vigilancia_multiagente/application/graph/knowledge_graph_service.py`
- [X] T095 [P] Remove unused imports (`BranchKPIService`, `SessionEvent`, `format_sse`, `ReportSynthesizer`) from `tests/conftest.py`
- [X] T096 [P] Remove unused import `MemorySessionRepository` from `tests/test_e2e_flow.py`

### Fase 7.4 — Verificaciones Innecesarias

- [X] T097 Eliminar fixture `fake_db` no usada de `tests/conftest.py`
- [X] T098 Replace `undirected_edges` with `_` in `src/vigilancia_multiagente/application/execution/branch_coordinator.py` (variable asignada y nunca leída)
- [X] T099 Fix redundant `ensure_contract_file()` call in `src/vigilancia_multiagente/application/governance/contract_loader.py` — called once in `load_prompt_template()` and again in `load_branch_overlay()` which it calls

### Fase 7.5 — System Base por Agente (Skill Matrix en composed prompt)

- [X] T100 Extend `PromptComposer` to include `AgentSkillPolicy` info in the composed prompt: add a "Tools Disponibles" section showing tool order, timeout, retry, and fallback for each tool. Pass `policy` from `BaseBranchAgent.run()` to `composer.compose()`. Update `ComposedPrompt.sections` with the new section.

## Phase 8: MiniMax Readiness + Embedding Fix + Prompts Separation

**Goal**: Dejar todo listo para que al configurar `VT_MINIMAX_API_KEY`, clarificación, planificación y síntesis usen MiniMax sin reescribir código. Todos los cambios usan parámetros opcionales (`llm: MiniMaxClient | None = None`) para mantener compatibilidad total con el flujo actual.
**Independent Test Criteria**: `python -m pytest -q` pasa 43+ tests. MiniMaxClient envía `max_tokens`, `temperature`, `stream`, `reasoning_split` en el payload. `embed_query()` usa prefix `query:`. Prompt files existen y son cargables. BranchOverlays tienen fallback al dict actual.

### Fase 8.1 — MiniMax Client Params + Gemini Embedding

- [X] T101 Fix MiniMax base URL from `https://api.minimax.chat/v1` to `https://api.minimax.io` in `src/vigilancia_multiagente/config/settings.py`
- [X] T102 Add `max_tokens=100000`, `temperature=0.3`, `stream=False`, `reasoning_split=True` to MiniMaxClient request payload and update `_parse_response()` to handle `reasoning_details` field in `src/vigilancia_multiagente/infra/llm/minimax_client.py`
- [X] T103 Add `embed(text, task_type)` method with `RETRIEVAL_QUERY` (`query:` prefix) and `RETRIEVAL_DOCUMENT` (`document:` prefix) support to `GeminiEmbeddingGateway` in `src/vigilancia_multiagente/infra/embeddings/gemini_gateway.py`
- [X] T104 Update graph search to use `embed(query, task_type="RETRIEVAL_QUERY")` instead of `embed_document(query)` in `src/vigilancia_multiagente/api/routes/research_outputs.py`

### Fase 8.2 — Conectar MiniMax al Flujo (parámetros opcionales)

- [X] T105 Add optional `llm: MiniMaxClient | None = None` parameter to `ClarificationService.generate_questions()`. When llm is provided, load prompt from `src/prompts/orchestration/clarify.txt` and call `llm.complete()`. Update caller in `src/vigilancia_multiagente/api/routes/research_start_clarify.py` to pass `minimax_client` from dependencies.
- [X] T106 Add optional `llm: MiniMaxClient | None = None` parameter to `PlanBuilder.build()`. When llm is provided, load prompt from `src/prompts/orchestration/planning.txt` and call `llm.complete()`. Update caller in `research_start_clarify.py` to pass `minimax_client`. Update `PlanBuilder()` instantiation in `tests/test_system_base_contract.py`.
- [X] T107 Add optional `llm: MiniMaxClient | None = None` parameter to `ReportSynthesizer.synthesize()`. When llm is provided, load prompt from `src/prompts/orchestration/synthesis.txt` and call `llm.complete()`. Update caller in `src/vigilancia_multiagente/api/routes/research_approve.py` to pass `minimax_client` from dependencies.

### Fase 8.3 — Prompts en Archivos Separados

- [X] T108 [P] Create orchestration prompt files: `src/prompts/orchestration/clarify.txt`, `src/prompts/orchestration/planning.txt`, `src/prompts/orchestration/synthesis.txt`
- [X] T109 [P] Create branch prompt files: `src/prompts/branches/avances.txt`, `src/prompts/branches/comercial.txt`, `src/prompts/branches/riesgo.txt`, `src/prompts/branches/pi_normativa.txt`, `src/prompts/branches/competitivo.txt`, `src/prompts/branches/oportunidades.txt`
- [X] T110 [P] Create `src/infra/prompts/loader.py` — `load_prompt(path: str) -> str` reads `src/prompts/{path}.txt`
- [X] T111 Migrate `_BRANCH_OVERLAYS` in `contract_loader.py` to load from prompt files (`src/prompts/branches/{branch_type}.txt`) with fallback to current hardcoded dict if file doesn't exist

### Fase 8.4 — Tests

- [X] T112 [P] Add tests verifying MiniMaxClient sends `max_tokens`, `temperature`, `stream`, `reasoning_split` in request payload, and that `_parse_response` correctly handles both response formats (with and without `reasoning_details`) in `tests/test_minimax_client.py`

## Phase 9: Backend Intelligence v3 — Source Scoring, MCP Cache, Graph Intelligence, Agent Features

**Goal**: Agregar 12 features de inteligencia avanzada: source scoring, cross-session search, ecosystem map, obsolescencia, branch signaling, MCP cache, smart router, parameter learner, hype detector, decision assistant, MiniMax roles avanzados, tool usage prompts.
**Constraint**: Sin `VT_MINIMAX_API_KEY` — todas las features con LLM usan `llm=None` por defecto con fallback funcional.
**Independent Test Criteria**: `python -m pytest -q` pasa 50+ tests. Ningún feature queda sin integración (todas tienen caller/endpoint definido).

### Phase 9.0 — Foundation + DI Wiring

- [X] T113 [P] Implement `SourceScorer` class with `DOMAIN_SCORES` dict and `score(url)` method in `src/vigilancia_multiagente/application/evaluation/source_scorer.py`
- [X] T114 Integrate `SourceScorer` into `EvidenceLinker.deduplicate_sources()` — apply source confidence scoring to findings in `src/vigilancia_multiagente/application/fusion/evidence_linker.py`
- [X] T115 [P] Implement `MCPSmartCache` — thread-safe cache with per-tool TTLs (tavily=1h, exa=1h, jina=24h, brave=1h, firecrawl=24h, scholar=3d, arxiv=3d) in `src/vigilancia_multiagente/infra/mcp/mcp_cache.py`
- [X] T116 Add `name: str = ""` field to `MiniMaxMessage` dataclass and include `name` in serialization payload in `src/vigilancia_multiagente/domain/system_base.py` and `src/vigilancia_multiagente/infra/llm/minimax_client.py`
- [X] T117 Extend `MiniMaxClient.complete()` to prepend `system` role message, `user_system` role, `sample_message_user` and `sample_message_ai` from `src/prompts/minimax_examples/` when available in `src/vigilancia_multiagente/infra/llm/minimax_client.py`
- [X] T118 Wire new services (`source_scorer`, `mcp_cache`, `smart_router`, `parameter_learner`) as module-level singletons in `src/vigilancia_multiagente/api/dependencies.py`

### Phase 9.1 — Knowledge Graph Intelligence

- [X] T119 Add `search_across_sessions(query, query_vector, limit)` method to `KnowledgeGraphService` — extend `PostgresVectorIndex.list_by_session()` with `session_id: UUID | None` (None = all sessions) in `src/vigilancia_multiagente/infra/persistence/vector_index.py` and `src/vigilancia_multiagente/application/graph/knowledge_graph_service.py`
- [X] T120 Add `discover_ecosystem(seed, graph, depth)` method to `KnowledgeGraphService` — traverse graph from seed node classifying relationships as `competes_with`, `adopted_by`, `depends_on`, `emerging` in `src/vigilancia_multiagente/application/graph/knowledge_graph_service.py`
- [X] T121 [P] Add endpoint `GET /research/{id}/graph/ecosystem?seed=...&depth=2` in `src/vigilancia_multiagente/api/routes/research_outputs.py` and register in router
- [X] T122 [P] Add tests for `search_across_sessions()` and `discover_ecosystem()` in `tests/test_graph_api_contract.py`

### Phase 9.2 — Agent Intelligence

- [X] T123 [P] Implement `SmartToolRouter` — classifies query by keywords (academic, company, patent, news, deep_research) and returns optimal tool order in `src/vigilancia_multiagente/application/governance/smart_router.py`
- [X] T124 Integrate `SmartToolRouter` into `BaseBranchAgent.run()` — gated by feature flag (default: off), falls back to current fixed tool order in `src/vigilancia_multiagente/application/agents/base.py`
- [X] T125 Add `signal_branch(target: BranchType, payload: SignalPayload)` method to `BaseBranchAgent` — call automatically after `run()` when findings have tags from other branches in `src/vigilancia_multiagente/application/agents/base.py`
- [X] T126 Add signal queue and `_process_cross_signals()` post-execution handler in `BranchCoordinator` in `src/vigilancia_multiagente/application/execution/branch_coordinator.py`
- [X] T127 [P] Implement `ParameterLearner` with `record_outcome(branch, params, success, coverage)` and `suggest(branch)` — called from `BranchCoordinator` after each `BranchResult` in `src/vigilancia_multiagente/application/evaluation/parameter_learner.py`
- [X] T128 [P] Implement `ObsolescenceDetector.analyze(tech_name)` — heuristic without LLM, exposed via endpoint `POST /research/{id}/obsolescence` in `src/vigilancia_multiagente/application/evaluation/obsolescence_detector.py` and `src/vigilancia_multiagente/api/routes/research_outputs.py`
- [X] T129 Integrate `MCPSmartCache` into `MCPExecutionClient.execute_tool()` — transparent wrapper that checks cache before execution, stores results after in `src/vigilancia_multiagente/infra/mcp/execution_client.py`
- [X] T130 [P] Add tests for `SmartToolRouter` and `ObsolescenceDetector` in `tests/test_smart_router.py`

### Phase 9.3 — Advanced Analysis (MiniMax optional)

- [X] T131 [P] Implement `HypeDetector` — cross-reference papers, prototypes, funding, patents. Without LLM: compute hype ratio. With LLM: narrative analysis. Exposed via `POST /research/{id}/hype-analysis` in `src/vigilancia_multiagente/application/evaluation/hype_detector.py` and endpoint in `src/vigilancia_multiagente/api/routes/research_outputs.py`
- [X] T132 [P] Implement `DecisionAssistant` — upside/downside/risks/recommendation framework. Without LLM: template-based. With LLM: deep analysis. Exposed via `POST /research/{id}/decision` in `src/vigilancia_multiagente/application/fusion/decision_assistant.py` and endpoint in `src/vigilancia_multiagente/api/routes/research_outputs.py`
- [X] T133 [P] Add tests for `HypeDetector` and `DecisionAssistant` in `tests/test_evaluation_advanced.py`

### Phase 9.4 — Tool Usage Prompts

- [X] T134 [P] Create tool usage guide files with real parameters: `src/prompts/tools/tavily.txt`, `exa.txt`, `jina.txt`, `brave.txt`, `firecrawl.txt`, `scholar.txt`, `arxiv.txt`, `fetch.txt`
- [X] T135 Integrate tool usage guides into `PromptComposer.compose()` — add a "Tool Usage" section per agent showing how to use each tool in its skill matrix in `src/vigilancia_multiagente/application/governance/prompt_composer.py`
- [X] T136 Final verification: python -m pytest -q — 50+ tests passing.

## Phase 10: Cierre de Features Parciales — Conectar Providers + Endpoints Faltantes

**Goal**: Cerrar las 6 features parciales conectándolas con providers reales o endpoints REST faltantes. Todos con fallback si no hay API keys.
**Independent Test Criteria**: python -m pytest -q pasa 59+ tests. SourceScorer modifica confidence. Cross-session endpoint responde. Branch signaling re-ejecuta sub-ramas. Observaciones, hype y decisión producen output útil sin API keys.

- [X] T137 [P] Add confidence: float = 0.7 field to SourceRef in src/vigilancia_multiagente/domain/models.py and apply SourceScorer.score() in EvidenceLinker.deduplicate_sources() in src/vigilancia_multiagente/application/fusion/evidence_linker.py
- [X] T138 [P] Add endpoint GET /research/{id}/graph/search-cross-session?query=... that calls search_across_sessions() with ector_index.list_by_session(None) in src/vigilancia_multiagente/api/routes/research_outputs.py
- [X] T139 Connect ObsolescenceDetector.analyze() with rave_news_search (detect mention decline) and web_search_advanced_exa (detect alternatives) — both optional with fallback in src/vigilancia_multiagente/application/evaluation/obsolescence_detector.py
- [X] T140 [P] Upgrade BranchCoordinator._process_cross_signals() to spawn real sub-executions via gent.run() for each signal, merging results into the final output in src/vigilancia_multiagente/application/execution/branch_coordinator.py
- [X] T141 [P] Connect HypeDetector.analyze() with search_papers, web_search_advanced_exa(category=company), irecrawl_scrape — all optional with fallback in src/vigilancia_multiagente/application/evaluation/hype_detector.py
- [X] T142 Add heuristic to DecisionAssistant.analyze() that extracts upside/downside from ranch_results when available (no LLM needed) in src/vigilancia_multiagente/application/fusion/decision_assistant.py
- [X] T143 Final verification: python -m pytest -q — 59+ tests passing.

## Dependencies: `python -m pytest -q` — 50+ tests passing. Validate legacy behavior with `VT_SYSTEM_BASE_ENABLED=false` and without API keys.

## Dependencies (User Story Order)

- Setup (Phase 1) must complete before Foundational (Phase 2).
- Foundational (Phase 2) must complete before User Story 1 (Phase 3).
- User Story order: `US1` (single P1 story, MVP scope for backend closure).
- Polish phase (Phase 4) depends on completion of `US1` core implementation tasks (`T013-T033`).
- Remediation (Phase 5) depends on completion of Phases 0-4 of system-base standardization (already implemented).
- T044 and T045/T046 are sequential: T044 must land before T045 can use the new field.
- T048 and T049 depend on T047 (feature flag in settings first).
- T051-T055 are independent of each other and can run in parallel.
- T056 and T057 depend on T044-T046 (need `prompt_composition_id` in place first).
- **MCP (Phase 6)**: T059 (Node upgrade) must complete before T065 (Brave MCP). T060 (uv install) must complete before T068 (ArXiv MCP). T061 (API keys in .env) must complete before ALL T062-T070.
- T062-T068 are fully independent (parallelizable subagents).
- T071-T078 depend on corresponding T062-T068 being installed first.
- T079 depends on T062-T068 (real URLs known).
- T081 depends on T079 and T080.
- T082 depends on T081.
- **Code Health (Phase 7)**: T083 (token limit) is independent. T084 (bug fix) is independent. T085-T098 are all independent of each other (parallelizable). T100 depends on T084 (same file, prompt_composer.py).
- T089-T096 (import cleanup) each touch a different file — fully parallel.
- T097 (fixture) depends on T095 (same file — conftest.py). Run T097 after T095.
- **MiniMax Readiness (Phase 8)**: T104 depends on T103 (same file, gemini_gateway.py). T106 cannot run in parallel with T105 (both modify research_start_clarify.py). T111 depends on T109 + T110 (needs files + loader). T112 depends on T102 (tests the new params).
- T101, T102, T103, T105, T107, T108, T110 are fully independent (different files, no shared dependencies).
- T109 is independent and can run in parallel with T108 (different directories).
- T105 and T106 are serial: T106 after T105 (same file: research_start_clarify.py).
- **Complete Partial Features (Phase 10)**: T137 and T138 are independent (different files). T139, T141, T142 are independent (different files, 3 subagentes en paralelo). T140 depends on understanding branch_coordinator flow. T143 (tests) depends on all previous.
- **Backend Intelligence (Phase 9)**: T113 (SourceScorer) must complete before T114 (integration). T116 must complete before T117 (MiniMaxMessage → MiniMaxClient). T118 (DI wiring) after all Phase 0 services exist. T124 depends on T123 (SmartRouter impl → integration). T125+T126 depend on each other (signal flow). T129 depends on T115 (MCP cache impl → integration). T135 depends on T134 (prompts exist → integration).
- Phase 9.0 parallel: T113, T115, T116 (3 subagentes, archivos distintos).
- Phase 9.1 serial: T119+T120 (mismo archivo: knowledge_graph_service.py).
- Phase 9.2 parallel: T123, T127, T128 (3 subagentes, archivos distintos).
- Phase 9.3 parallel: T131, T132 (2 subagentes, archivos distintos).
- Phase 9.4 serial: T134 → T135 → T136.

## Parallel Execution Examples

### Setup Parallel Block

- Run `T002`, `T003`, `T004`, `T005` in parallel after `T001`.

### Foundational Parallel Block

- Run `T011` and `T012` in parallel after `T006-T010`.

### US1 Parallel Block A (API surfaces)

- Run `T013`, `T014`, `T015`, `T016`, `T017`, `T018`, `T019`, `T020` in parallel where file collisions do not occur; serialize edits per file.

### US1 Parallel Block B (graph algorithms)

- Run `T021`, `T022`, `T023`, `T024`, `T025`, `T026` sequentially within `knowledge_graph_service.py` (same file), but in parallel with `T028`, `T029`, `T030`.

### Polish Parallel Block

- Run `T034`, `T035`, `T036`, `T037`, `T038`, `T039` in parallel across distinct test files.

### Remediation Parallel Block A (docs)

- Run `T051`, `T052`, `T053`, `T054`, `T055` in parallel (all in different spec files).

### Remediation Parallel Block B (tests + comments)

- Run `T056`, `T057`, `T058` in parallel (different test/source files).

### MCP Parallel Block A (Install: 7 subagents)

- Run `T062`, `T063`, `T064`, `T065`, `T066`, `T067`, `T068` in parallel — each is a fully independent provider installation. Deploy as subagents for isolation.
- `T069` (Serper REST) runs in parallel with this block too.

### MCP Parallel Block B (Smoke tests: 8 subagents)

- Run `T071`, `T072`, `T073`, `T074`, `T075`, `T076`, `T077`, `T078` in parallel — each tests a different provider. Deploy as subagents.

### MCP Parallel Block C (Docs + integration)

- Run `T079` and `T080` in parallel (different contract files).
- Run `T081` after both complete.
- Run `T082` after T081.

### Code Health Parallel Block A (Token + Bug: 2 subagents)

- Run `T083` and `T084` in parallel (different files).

### Code Health Parallel Block B (Modules/Classes: 4 subagents)

- Run `T085`, `T086`, `T087`, `T088` in parallel (all different files).

### Code Health Parallel Block C (Imports: 8 subagents)

- Run `T089`, `T090`, `T091`, `T092`, `T093`, `T094`, `T095`, `T096` in parallel — each touches a different file.

### Code Health Parallel Block D (Checks + System base)

- Run `T097` after `T095` (same file: conftest.py).
- Run `T098`, `T099` in parallel (different files).
- Run `T100` after `T084` (same file: prompt_composer.py).

### MiniMax Block A (7 subagents en paralelo)

- Run `T101`, `T102`, `T103`, `T105`, `T107`, `T108`, `T110` in parallel — todos tocan archivos distintos:
  - T101: settings.py (1 línea)
  - T102: minimax_client.py (payload params + parser)
  - T103: gemini_gateway.py (embed con task prefix)
  - T105: clarification_service.py + research_start_clarify.py (clarificación)
  - T107: report_synthesizer.py + research_approve.py (síntesis)
  - T108: 3 archivos .txt en src/prompts/orchestration/
  - T110: infra/prompts/loader.py (nuevo archivo)

### MiniMax Block B (independientes, corren con Block A o después)

- Run `T109` (branch prompts, 6 archivos) en paralelo con Block A (directorio distinto).
- Run `T104` después de T103 (mismo archivo: gemini_gateway.py).
- Run `T106` después de T105 (mismo archivo: research_start_clarify.py — serial obligatorio).
- Run `T111` después de T109 + T110 (necesita archivos y loader).
- Run `T112` después de T102 (verifica los nuevos params).

### Intelligence Phase 9.0 Block A (Foundation: 3 subagentes)

- Run `T113`, `T115`, `T116` in parallel — archivos distintos:
  - T113: source_scorer.py
  - T115: mcp_cache.py
  - T116: system_base.py (MiniMaxMessage name field)
- Run `T114` after T113 (integra SourceScorer en EvidenceLinker).
- Run `T117` after T116 (usa MiniMaxMessage con name).
- Run `T118` after T114 + T117 (wire services en dependencies.py).

### Intelligence Phase 9.1 Block B (Graph: serial + paralelo)

- Run `T119` and `T120` sequentially (mismo archivo: knowledge_graph_service.py).
- Run `T121` and `T122` in parallel (endpoint + tests, archivos distintos).

### Intelligence Phase 9.2 Block C (Agent: 3 subagentes)

- Run `T123`, `T127`, `T128` in parallel — archivos distintos:
  - T123: smart_router.py
  - T127: parameter_learner.py
  - T128: obsolescence_detector.py + endpoint
- Run `T124` after T123 (integra SmartRouter en base.py).
- Run `T125` + `T126` sequentially (branch signaling flow).
- Run `T129` after T115 (integra MCP cache en execution_client.py).
- Run `T130` after T127 + T128 (tests).

### Intelligence Phase 9.3 Block D (Analysis: 2 subagentes)

- Run `T131` and `T132` in parallel — archivos distintos:
  - T131: hype_detector.py + endpoint
  - T132: decision_assistant.py + endpoint
- Run `T133` after T131 + T132 (tests).

### Intelligence Phase 9.4 Block E (Tool Prompts: serial)

- Run T134 → T135 → T136 sequentially (cada paso depende del anterior).

### Phase 10 Block A (3 subagentes en paralelo)

- Run T137, T139, T141 in parallel — archivos distintos:
  - T137: domain/models.py + evidence_linker.py
  - T139: obsolescence_detector.py (conectar providers)
  - T141: hype_detector.py (conectar providers)
- Run T138 after T137 (misma área funcional: cross-session depende de vector_index).
- Run T140 after T139 (branch signaling puede usar datos de obsolescencia).
- Run T142 independently (decision_assistant.py).
- Run T143 after all (tests finales).

- Run `T134` → `T135` → `T136` sequentially (cada paso depende del anterior).

## Implementation Strategy

1. Complete API v2 parity (`T013-T020`) and graph engine core (`T021-T026`) as backend-closure MVP.
2. Close runtime production gaps (`T027-T033`) to remove placeholder behavior and align storage narrative.
3. Finish quality gates and test suite (`T034-T039`) before final operational checklist (`T040-T042`).
4. Remediation (`T043-T058`): close all gaps between plan and implementation. Start with deprecation warning and `prompt_composition_id` (`T043-T046`), then feature flag (`T047-T049`), then docs (`T051-T055`), then tests (`T050`, `T056-T057`), finally rollout comments (`T058`).
5. MCP Installation (`T059-T082`): primero runtime y API keys (`T059-T061`), luego deploy 7 subagentes en paralelo para instalación de MCPs (`T062-T068`), luego serper REST (`T069-T070`), luego 8 subagentes en paralelo para smoke tests (`T071-T078`), finalmente integración con el proyecto (`T079-T082`).
6. Code Health (`T083-T100`): primero token limit y bug fix (`T083-T084`), luego 4 subagentes en paralelo para módulos/classes muertos (`T085-T088`), luego 8 subagentes en paralelo para imports no usados (`T089-T096`), luego verificaciones innecesarias (`T097-T099`), finalmente system base por agente con skill matrix (`T100`).
7. MiniMax Readiness (`T101-T112`): primero 7 subagentes en paralelo para cambios independientes (T101, T102, T103, T105, T107, T108, T110). Luego T104 (gemini query fix), T106 (planning, serial con T105), T109 (branch prompts), T111 (branch overlay migration, después de T109+T110), y T112 (tests, después de T102).
8. Backend Intelligence (`T113-T136`): Primero foundation (T113-T118): 3 subagentes en paralelo (SourceScorer, MCP Cache, MiniMaxMessage), luego integraciones. Segundo, graph (T119-T122): serial knowledge_graph, paralelo endpoint+tests. Tercero, agent (T123-T130): 3 subagentes en paralelo (SmartRouter, ParameterLearner, Obsolescencia), luego integraciones y cache. Cuarto, analysis (T131-T133): 2 subagentes en paralelo (HypeDetector, DecisionAssistant). Quinto, tools (T134-T136): tool usage prompts secuencial.

## Execution Evidence

- Backend closure health metadata now exposes service version, environment, api base, and per-surface closure status at `GET /health`.
- Quickstart now includes backend closure smoke checks for `/health`, `/docs`, and `/api/v2/research/*`.
- Validation run: `python -m pytest -q` (15 passed).
