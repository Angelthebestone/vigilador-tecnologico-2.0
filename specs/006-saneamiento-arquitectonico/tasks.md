# Tasks: Saneamiento Arquitectonico — Correccion de Deuda Tecnica Estructural

**Input**: `specs/006-saneamiento-arquitectonico/spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/`
**Feature**: Refactor estructural para corregir violaciones SOLID y Hexagonal (~8 archivos hub, 21 FRs, 4 fases secuenciales).

---

## Phase 0 — Quick Wins

**Goal**: Romper ciclos DIP, eliminar estado mutable oculto, agregar logging faltante, crear script de validacion de capas.
**Independent Test Criteria**: `scripts/check-layer-imports.py` reporta zero violaciones de imports entre capas. `pytest` pasa sin regresiones.

- [X] T001 [P] Inyectar MCPSmartCache por constructor en `src/vigilancia_multiagente/infra/mcp/execution_client.py` y eliminar import a `api.dependencies.mcp_cache`. Actualizar `src/vigilancia_multiagente/api/dependencies.py` para pasar la instancia.
- [X] T002 [P] Mover funcion cosine_similarity a `src/vigilancia_multiagente/shared/math_utils.py` (nuevo) y eliminar import infra→application en `src/vigilancia_multiagente/infra/reranking/semantic_reranker.py`.
- [X] T003 [P] Eliminar o redirigir `execute_research` duplicado en `src/vigilancia_multiagente/application/orchestration/orchestrator_service.py`; unificar toda ejecucion en `BranchCoordinator.execute`.
- [X] T004 Inyectar `EventLogger` Protocol en `BaseBranchAgent` (constructor) y `BranchCoordinator` (constructor). Crear Protocol en `src/vigilancia_multiagente/domain/ports/event_publisher.py`. Eliminar lazy imports desde `api.dependencies` en `src/vigilancia_multiagente/application/agents/base.py` y `src/vigilancia_multiagente/application/execution/branch_coordinator.py`.
- [X] T005 [P] Crear script de validacion de imports entre capas en `scripts/check-layer-imports.py` usando `ast.parse()`. Debe escanear todos los `.py` del proyecto y reportar violaciones: infra→api, infra→application, application→api, application→api.dependencies.
- [X] T006 [P] Agregar logging explicito en `ToolSelector.force_chain()` en `src/vigilancia_multiagente/application/routing/tool_selector.py` cuando fuerza cadena de herramientas (download_paper → read_paper). Loggear tool origen, tool destino y motivo. No cambiar logica de negocio.
- [X] T007 Hacer `_sub_results` session-scoped (dict keyed por session_id) en `src/vigilancia_multiagente/application/execution/branch_coordinator.py`. Agregar `reset_session_state(session_id)` en `src/vigilancia_multiagente/application/agents/base.py` para limpiar `_preload_context` y `_directive_queue`. Inicializar `_directive_queue` en constructor (no lazy).

---

## Phase 1 — Controladores Delgados

**Goal**: Extraer logica de negocio de rutas HTTP hacia Application/. Rutas quedan como adaptadores delgados (< 50 LOC de enrutamiento).
**Independent Test Criteria**: `POST /research/approve` delega en `ApproveResearchUseCase`. `research_approve.py` <= 100 LOC total. `pytest` sin regresiones.

- [X] T008 [P] Crear `ApproveResearchUseCase` en `src/vigilancia_multiagente/application/orchestration/approve_research_usecase.py`. Extraer el contenido de `approve_plan` de `src/vigilancia_multiagente/api/routes/research_approve.py`. El use case recibe `session_id`, `plan_data` y retorna `ApproveResult` estructurado (no dict). Inyectar dependencias via constructor.
- [X] T009 Reducir la ruta `POST /research/approve` en `src/vigilancia_multiagente/api/routes/research_approve.py` a solo: validar request, llamar a `ApproveResearchUseCase`, mapear DTO de respuesta. Target: <= 50 LOC de enrutamiento (sin contar imports y decoradores).
- [X] T010 [P] Crear `AdHocResearchToolsService` en `src/vigilancia_multiagente/application/research/ad_hoc_tools_service.py`. Extraer toda la logica de busquedas MCP inline de `src/vigilancia_multiagente/api/routes/research_outputs.py`. La ruta solo debe validar request, llamar al servicio y mapear respuesta.
- [X] T011 [P] Crear `DocumentConversionService` en `src/vigilancia_multiagente/application/research/document_conversion_service.py` con puerto para Markitdown. `src/vigilancia_multiagente/api/routes/upload.py` no debe instanciar `MarkitdownProvider` directamente; debe recibir el servicio inyectado.

---

## Phase 2 — Puertos de Dominio

**Goal**: Crear Protocols en `domain/ports/`, externalizar configuracion a YAML, tipar respuestas MCP.
**Independent Test Criteria**: Todos los puntos de extension tienen Protocol en `domain/ports/` con adapter en `infra/`. `dependencies.py` es el unico composition root. Cero retornos `dict[str, Any]` en modulos MCP. `pytest` sin regresiones.

- [X] T012 [P] Crear 6 Protocols en `src/vigilancia_multiagente/domain/ports/`: `LLMClient`, `EmbeddingGateway`, `ToolExecutor`, `VectorIndex`, `GlobalKnowledgeStore`, `SourceTrustStore`. **NOTA**: `EventPublisher` ya fue creado por T004, no duplicar. Cada Protocol con 1-3 metodos, documentacion de contrato, tipos de entrada/salida definidos. Incluir `__init__.py` que re-exporte todos los Protocols.
- [X] T013 Modificar adaptadores en `src/vigilancia_multiagente/infra/` para implementar los Protocols: MiniMaxClient → LLMClient, GeminiEmbeddingGateway → EmbeddingGateway, MCPExecutionClient → ToolExecutor, VectorIndex → VectorIndex, GlobalKnowledgeRepository → GlobalKnowledgeStore, SourceTrustRepository → SourceTrustStore, EventLogDB → EventPublisher. Actualizar `src/vigilancia_multiagente/api/dependencies.py` para ensamblar Protocols → adapters.
- [X] T014 [P] Externalizar `load_skill_matrix` de `src/vigilancia_multiagente/application/governance/contract_loader.py` a `config/skills/skill_matrix_default.yaml`. Schema: `branch_type -> list[skill]` con tool_order, timeout, retries. Cargar YAML en startup con fallback a dict embebido. Actualizar contract_loader.py a solo carga YAML + validacion.
- [X] T015a Auditar `src/vigilancia_multiagente/application/agents/` (base.py, agentes de rama). Reemplazar constructores para recibir Protocols de `domain/ports/` en lugar de clases concretas de infra.
- [X] T015b [P] Auditar `src/vigilancia_multiagente/application/orchestration/` + `application/execution/`. Reemplazar constructores.
- [X] T015c [P] Auditar `src/vigilancia_multiagente/application/fusion/` + `application/memory/`. Reemplazar constructores.
- [X] T015d [P] Auditar `src/vigilancia_multiagente/application/planning/` + `application/routing/` + `application/governance/`. Reemplazar constructores. Verificar con `basedpyright` que no queden imports directos a infra desde application.
- [X] T016 [P] Crear dataclasses tipadas en `src/vigilancia_multiagente/application/mcp/types.py`: `NavigationResult`, `ScreenshotResult`, `SearchResult`, `SourceResult`, `DocumentConversionResult`. Reemplazar todos los retornos `dict[str, Any]` en `src/vigilancia_multiagente/infra/mcp/playwright_mcp.py` y `src/vigilancia_multiagente/infra/mcp/execution_client.py`.
- [X] T017 [P] Migrar `MCPProviderRegistry` en `src/vigilancia_multiagente/infra/mcp/provider_registry.py` a carga desde `config/mcp-providers.yaml`. Mantener `ensure_standard_providers()` como fallback para proveedores no declarados en el manifiesto. El YAML debe poder anadir/quitar providers sin tocar Python.

---

## Phase 3 — Pipeline de Agente

**Goal**: Pipeline componible. KnowledgeGraphService dividido. Sandbox extraido de base.py.
**Independent Test Criteria**: `BaseBranchAgent.run()` delega en Pipeline. Cada pipeline step testeable con fakes (<= 60 LOC). GraphBuilder y GraphAnalytics separados. Sandbox tools en modulo propio. `pytest` sin regresiones.

- [X] T018 Crear pipeline steps en `src/vigilancia_multiagente/application/agents/pipeline/`: `base_step.py` (`PipelineStep[T]` base class con `execute(context) -> T`), `compose_prompt_step.py`, `tool_loop_step.py`, `sandbox_execution_step.py`, `assemble_branch_result_step.py`, `pipeline.py` (orquestador secuencial). `BaseBranchAgent.run()` en `src/vigilancia_multiagente/application/agents/base.py` debe delegar en `Pipeline.run()`.
- [X] T019 [P] Dividir `KnowledgeGraphService` en `src/vigilancia_multiagente/application/graph/graph_builder.py` (construye grafo: entidades, relaciones) y `src/vigilancia_multiagente/application/graph/graph_analytics.py` (analiza: centralidad, clusters, bridges). `knowledge_graph_service.py` se reduce a wrapper que delega en ambos para compatibilidad.
- [X] T020 Crear tests unitarios para cada pipeline step con fakes en `tests/application/agents/pipeline/`. Tests de integracion para Pipeline completo. Cada step testeable de forma aislada con <= 60 LOC de implementacion.
- [X] T021 Extraer funciones sandbox (`execute_code`, `list_libraries`, `visualize`) de `src/vigilancia_multiagente/application/agents/base.py` a `src/vigilancia_multiagente/application/agents/sandbox_tools.py`. `BaseBranchAgent` debe importar y delegar en el modulo externo. **NOTA**: Secuencial con T018 (ambos modifican base.py). Ejecutar T021 primero, luego T018.

---

---

## Phase 4 — Hallazgos Residuales

**Goal**: Eliminar duplicacion nominal de source_scorer, reemplazar optional `None` con Null Objects, planificar migracion de evaluation/, reducir fragilidad del composition root.
**Independent Test Criteria**: `OrchestratorService` sin parametros `None`. Un solo `source_scorer.py`. `dependencies.py` organizado en factories. `pytest` sin regresiones.

- [X] T022 [P] Unificar `source_scorer.py` duplicados. Evaluar opciones A/B/C (fusion, renombrar, deprecar) y ejecutar la decision. Si se fusiona, crear `src/vigilancia_multiagente/application/evaluation/source_scorer.py` con estrategia snapshot (`SourceScorer`) y estrategia transaccional (`SourceScorerService`) como implementaciones intercambiables de un mismo Protocol. Si se renombra, `SourceScorerService` pasa a `SourceConfirmationService` en `src/vigilancia_multiagente/application/routing/`. Actualizar todos los imports en `src/vigilancia_multiagente/api/dependencies.py` y demas consumidores (`src/vigilancia_multiagente/application/fusion/evidence_linker.py` importa `SourceScorer` de evaluation/; `src/vigilancia_multiagente/application/routing/smart_router.py` recibe `SourceScorerService` por constructor). **Deprecacion**: Si Opcion A, anadir comentario `# DEPRECATED: fusionado en evaluation/source_scorer.py` en `routing/source_scorer.py` antes de eliminar el archivo. Si Opcion C, anadir `# DEPRECATED: migrar a evaluation/source_scorer.py (spec 007)` en cada metodo de `SourceScorerService`.
- [X] T023 [P] Introducir Null Object Pattern en `src/vigilancia_multiagente/application/orchestration/orchestrator_service.py`. Crear 4 Null classes (una por dependencia opcional) en `application/orchestration/null_services.py` o `domain/ports/null_implementations.py`. Cada Null class implementa su Protocol con comportamiento neutro. Reemplazar `cross_session_service=None` → `NullCrossSessionService()`, etc. Eliminar condicionales `if x is None` en los metodos del servicio. **Deprecacion**: Anadir comentario `# DEPRECATED: usar Null Object en lugar de None` en las lineas donde se definen los parametros `= None` viejos. No mantener backward compatibility — el composition root siempre provee todas las dependencias.
- [X] T024 [P] Auditar `src/vigilancia_multiagente/application/evaluation/` y documentar destino de cada componente (legacy/eliminar, activo/integrado, migrar a spec 007). Componentes a evaluar (todos los .py, 13 archivos): `source_scorer.py`, `branch_kpi_service.py`, `golden_cases_runner.py`, `prompt_regression_service.py`, `confidence_calibrator.py`, `causal_timeline.py`, `claim_polarity.py`, `contradiction_analyzer.py`, `finding_impact_scorer.py`, `hype_detector.py`, `obsolescence_detector.py`, `weak_signal_detector.py`, `_markdown.py`. Anadir comentario de estado en la cabecera de cada archivo: `# ACTIVE` si se mantiene, `# DEPRECATED: [motivo]` si es legacy o migra a spec 007. Crear `specs/006-saneamiento-arquitectonico/evaluation-migration-plan.md` con el roadmap detallado.
- [X] T025 [P] Organizar `src/vigilancia_multiagente/api/dependencies.py` en funciones factory por dominio: `_build_session_services()`, `_build_governance_services()`, `_build_agent_services()`, `_build_orchestration_services()`, `_build_execution_services()`. Cada factory < 50 LOC. Mantener la funcion principal `get_dependencies()` o similar que llama a las factories en orden topologico. **Deprecacion**: La funcion principal original (que orquestaba todo linealmente) se marca con `# DEPRECATED: refactorizar a factories individuales` en su cabecera. No eliminar — mantener como wrapper que delega en las factories hasta que todos los consumidores esten migrados.
- [X] T026 Verificar que tras T022-T025, `basedpyright` reporta 0 errores y `pytest` pasa sin regresiones.

---

## Dependencies

- **Phase 0** debe completarse antes de **Phase 1** (sin DIP roto, los use cases serían ininyectables).
- **Phase 1** debe completarse antes de **Phase 2** (los use cases son los consumidores de los Protocols).
- **Phase 2** debe completarse antes de **Phase 3** (el pipeline necesita Protocols estables para inyeccion).
- **T004** debe completarse antes de **T018** (EventLogger necesario en BranchCoordinator para el pipeline).
- **T007** debe completarse antes de **T018** (estado mutable controlado necesario antes de pipeline).
- **T013** debe completarse antes de **T015a-d** (adapters implementando Protocols necesarios para auditar constructores).
- **T015b, T015c, T015d** son paralelos entre si; **T015a** se recomienda primero (agents/ es el consumidor mas grande de infra).
- **T016** debe completarse antes de que `dependencies.py` ensamble MCP types (mismo ciclo).
- **T022 y T025 son SECUENCIALES en dependencies.py**: T022 modifica imports y llamadas a source_scorer en `dependencies.py`; T025 reorganiza `dependencies.py` en factories. Ejecutar T022 primero, luego T025.
- **T026 debe esperar a T022-T025**: la verificacion final requiere todos los cambios aplicados.

## Parallel Execution Examples

### Phase 0 Parallel Block

- Run T001, T002, T003, T005, T006 en paralelo (todos tocan archivos diferentes: execution_client, semantic_reranker, orchestrator, scripts/tool_selector).
- T004 y T007 deben esperar a T001-T003 (comparten dependencias de inyeccion).

### Phase 1 Parallel Block

- Run T008 y T010 en paralelo (ApproveResearchUseCase y AdHocResearchToolsService son independientes).
- T009 depende de T008; T011 puede correr en paralelo con T008-T009.

### Phase 2 Parallel Block

- Run T012 (Protocols), T014 (YAML skills), T016 (MCP types) y T017 (YAML providers) en paralelo — 4 archivos diferentes sin dependencias mutuas.
- T013 (adapters) depende de T012.
- T015a-d (auditar constructores) dependen de T013. T015b, T015c, T015d son paralelos entre si; T015a debe ejecutarse antes (agents/ es el consumidor mas grande).

### Phase 3 Parallel Block

- Run T019 (Graph split) en paralelo con T021 (sandbox extraction) — tocan archivos diferentes (knowledge_graph_service.py vs sandbox_tools.py + base.py).
- **T021 y T018 son SECUENCIALES**: ejecutar T021 primero (extrae sandbox de base.py), luego T018 (refactoriza base.py.run() a pipeline). Ambos modifican base.py.
- T020 (tests) debe esperar a T018.
- T019 puede ejecutarse en cualquier orden (archivos independientes).

### Phase 4 Parallel Block

- Run T022, T023, T024, T025 en paralelo — tocan 4 areas diferentes sin superposicion:
  - T022: `evaluation/source_scorer.py` + `routing/source_scorer.py` + consumers (`evidence_linker.py`, `dependencies.py`)
  - T023: `orchestrator_service.py` + `null_services.py` (nuevo)
  - T024: `evaluation/*.py` (READ-ONLY audit, no modifica archivos)
  - T025: `dependencies.py` (organizar en factories)
- **Sin conflictos detectados**: consumers de source_scorer (`evidence_linker`, `dependencies.py`) no se superponen con T023 ni T024. T025 (dependencies.py) es el unico que toca el mismo archivo que T022 (ambos modifican `dependencies.py`). **Ejecutar T025 DESPUES de T022**, o fusionar cambios manualmente si se ejecutan en paralelo.
- **T026 (verificacion) debe esperar a T022-T025**: verificar basedpyright + pytest solo despues de que todos los cambios esten aplicados.

## Implementation Strategy

1. **Ejecutar Phase 0 primero** — Romper los ciclos DIP es prerequisito de absolutamente todo. Sin esto, cualquier nuevo componente hereda las violaciones.
2. **Phase 1 y Phase 2 tienen solapamiento posible** — Los use cases de Phase 1 pueden definirse con interfaces temporales (Protocols aun no estables) siempre que se inyecten por constructor. Esto permite adelantar trabajo.
3. **Phase 3 despues de Phase 2** — El pipeline necesita Protocols estables y el EventLogger funcionando. GraphBuilder/GraphAnalytics puede empezar antes si KnowledgeGraphService actual se trata como caja negra.
4. **Coexistencia con spec 007** — Los Protocols de Phase 2 (SourceTrustStore, MCP Response Types) son el contrato que 007 necesita. 007 puede empezar en paralelo a Phase 3 una vez que Phase 2 complete validacion.
5. **MVP minimo**: Phase 0 completo (DIP roto + script validacion). Con solo Phase 0, la puntuacion arquitectonica sube ~1 punto.
6. **Phase 4 es independiente de Fases 0-3**: Los hallazgos residuales no existian en el analisis original. Puede ejecutarse en cualquier orden respecto a spec 007.
7. **T022 y T025 comparten dependencies.py**: Se recomienda T022 → T025 secuencial. Si se ejecutan en paralelo, fusionar los cambios en dependencies.py manualmente.
8. **T024 es READ-ONLY**: No modifica archivos de evaluation/. Solo documenta. Puede ejecutarse en paralelo con cualquier otra tarea sin riesgo de conflicto.
