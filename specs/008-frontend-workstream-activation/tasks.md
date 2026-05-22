# Tasks: Activación de Workstreams desde Frontend y Visualización de Resultados

**Input**: `specs/008-frontend-workstream-activation/spec.md`, `plan.md`, `data-model.md`, `contracts/`, `research.md`, `quickstart.md`
**Feature**: Panel de configuración, visualización de workstreams, editor de prompts y mock server completo

---

## Phase 1: Setup — Infraestructura de configuración

**Goal**: Crear archivos base de persistencia y overrides para flags y prompts. Sin esto, ningún endpoint de config funciona.

- [ ] T001 [P] Crear `src/vigilancia_multiagente/config/workstream_overrides.py` con funciones `load_overrides() -> dict[str, bool]`, `save_overrides(data: dict[str, bool])`, `resolve_workstream_config(settings) -> WorkstreamConfig` resolviendo prioridad JSON > .env
- [ ] T002 [P] Crear `src/vigilancia_multiagente/config/prompt_overrides.py` con funciones `get_override(name) -> str | None`, `set_override(name, content)`, `restore_default(name)`, `list_overrides() -> list[dict]`, usando `config/prompt_overrides/` como directorio de archivos .txt
- [ ] T003 Crear `config/workstream_overrides.json` vacío (`{}`) como placeholder
- [ ] T004 Crear `config/prompt_overrides/.gitkeep` para inicializar directorio vacío

---

## Phase 2: Backend — API de configuración y evaluación

**Goal**: Exponer 7 endpoints REST para que el frontend pueda leer/escribir flags, prompts y resultados de evaluación. **Bloquea todas las fases de frontend.**

### 2.1 — Endpoints de workstreams

- [ ] T005 [P] Implementar `GET /config/workstreams` y `PATCH /config/workstreams` en `src/vigilancia_multiagente/api/routes/config_workstreams.py` usando `workstream_overrides.py` para leer/guardar. El `PATCH` solo acepta keys válidas (`ws_a`..`ws_e`), valores booleanos. Devuelve `{"applies_to": "next_session"}`.
- [ ] T006 [P] Implementar `GET /config/workstreams/health` en `src/vigilancia_multiagente/api/routes/config_workstreams.py`. Chequea: OpenAlex reachable (HTTP HEAD), Google FactCheck API key presente (`settings.google_factcheck_api_key is not None`), Retraction Watch CSV URL configurada (`settings.retraction_watch_csv_url is not None`). Devuelve `WorkstreamHealth` por workstream.

### 2.2 — Endpoints de prompts

- [ ] T007 [P] Implementar `GET /config/prompts` y `GET /config/prompts/{name}` en `src/vigilancia_multiagente/api/routes/config_prompts.py`. Lista los 8 templates (nombres fijos). `GET` individual devuelve contenido, `modified` flag, `default_content` y `size`.
- [ ] T008 Implementar `PUT /config/prompts/{name}` en `src/vigilancia_multiagente/api/routes/config_prompts.py`. Valida: nombre en lista conocida, contenido no vacío, tamaño ≤ 100KB. Guarda en `config/prompt_overrides/{name}.txt`.
- [ ] T009 Implementar `POST /config/prompts/{name}/restore` en `src/vigilancia_multiagente/api/routes/config_prompts.py`. Elimina el archivo de override si existe.

### 2.3 — Endpoint de evaluación extendido

- [ ] T010 Reescribir `GET /research/{session_id}/evaluation` en `src/vigilancia_multiagente/api/routes/research_evaluation.py`. Implementar `EvaluationAggregator.aggregate(session_id) -> SessionEvaluation` que consulta: `branch_result_repository.list_by_session()` (KPIs legacy), `golden_case_run_repository.list_by_session()` (WS-E calibración), `finding_repository.find_by_session()` con filtro de entidades WS-A/C/D adjuntas en columnas JSONB. Workstreams no activos → `null`. Mantiene `branch_evaluations` legacy para compatibilidad.

### 2.4 — Extensión del loader de prompts

- [ ] T011 Modificar `src/vigilancia_multiagente/infra/prompts/loader.py`: `FilesystemPromptLoader.load()` primero busca en `config/prompt_overrides/{path}.txt`. Si no existe, usa `prompts/{path}.txt`. Mantener `@lru_cache`.

### 2.5 — Registro de rutas y dependencias

- [ ] T012 Modificar `src/vigilancia_multiagente/config/settings.py`: agregar campo `workstream_overrides_path: str = "config/workstream_overrides.json"` y `prompt_overrides_dir: str = "config/prompt_overrides"`
- [ ] T013 Modificar `src/vigilancia_multiagente/api/dependencies.py`: exponer `workstream_overrides` y `prompt_overrides` como servicios en el dict de dependencias
- [ ] T014 Modificar `src/vigilancia_multiagente/api/router.py`: registrar rutas de `config_workstreams.py` y `config_prompts.py` bajo prefijo `/config`
- [ ] T015 Modificar `src/vigilancia_multiagente/api/routes/research_outputs.py`: delegar `GET /research/{id}/evaluation` a la nueva implementación en `research_evaluation.py`
- [ ] T016 Extender `src/vigilancia_multiagente/api/routes/research_outputs.py` y `src/vigilancia_multiagente/application/fusion/report_synthesizer.py`: `report_synthesizer.synthesize()` acepta parámetro opcional `session_evaluation: SessionEvaluation | None` y lo adjunta como `FinalReport.evaluation`. `GET /research/{id}/report` pasa `session_evaluation` al synthesizer cuando hay workstreams activos.

---

## Phase 3: Frontend — Tipos, API y Store

**Goal**: Definir todos los tipos TypeScript, funciones fetch y Zustand store necesarios. **Bloquea las fases 4 y 5.**

### 3.1 — Tipos de spec 007

- [ ] T017 Crear `frontend/src/types/evaluation.ts` con todos los tipos de entidades de spec 007: `AuthorReputation`, `ConflictOfInterest`, `ClaimExternalValidation`, `RetractionRecord`, `ReproducibilityScore`, `DedupedSource`, `ContentAuthenticitySignal`, `ConsensusDisputeEntry`, `SCurveProjection`, `ImplicitAssumption`, `CounterfactualScenario`, `CriticalDependency`, `MetaAnalysisResult`, `ConvergenceCluster`, `CollaborationNetwork`, `IdeaLineage`, `NarrativeShift`, `TalentMobility`, `PatentingGap`, `BiasAudit`, `ForensicTrace`, `StakeholderSimulation`, `FalsificationScenario`, `CalibrationCurve`
- [ ] T018 [P] Agregar a `frontend/src/types/evaluation.ts` tipos agregados: `WsaResult`, `WsbResult`, `WscResult`, `WsdResult`, `WseResult`, `SessionEvaluation`, `WorkstreamConfig`, `PromptTemplate`, `WorkstreamHealth`, `HealthStatus`
- [ ] T019 Modificar `frontend/src/types/index.ts`: importar y re-exportar tipos de `evaluation.ts`, extender `FinalReport` con campo `evaluation?: SessionEvaluation`

### 3.2 — API functions

- [ ] T020 Crear `frontend/src/api/evaluation.ts` con funciones: `getWorkstreamConfig()`, `patchWorkstreamConfig(data)`, `getWorkstreamHealth()`, `getPromptList()`, `getPrompt(name)`, `putPrompt(name, content)`, `restorePrompt(name)`, `getSessionEvaluation(sessionId)`
- [ ] T021 Modificar `frontend/src/api/endpoints.ts`: exportar funciones de `evaluation.ts` como parte de la API pública

### 3.3 — Zustand store

- [ ] T022 Crear `frontend/src/state/configStore.ts` (Zustand + persist): estado `workstreams: WorkstreamConfig`, `prompts: PromptTemplate[]`, `selectedPrompt: string | null`, `promptContent: string`, `health: WorkstreamHealth | null`. Acciones: `fetchWorkstreams`, `toggleWorkstream`, `saveWorkstreams`, `fetchPrompts`, `selectPrompt`, `updatePromptContent`, `savePrompt`, `restorePrompt`, `fetchHealth`
- [ ] T023 Modificar `frontend/src/state/hooks.ts`: exportar selectores `useWorkstreamConfig`, `usePrompts`, `useWorkstreamHealth` desde `configStore`

---

## Phase 4: Frontend — Panel de Configuración (US1)

**Goal**: Pestaña "Configuración" con toggles de workstreams y editor de prompts. Independiente de US2 (visualización de resultados).

**Independent Test**: Iniciar mock server, ir a pestaña Configuración, activar WS-A, guardar, verificar que `GET /config/workstreams` devuelve `ws_a: true`.

- [ ] T024 [US1] Crear `frontend/src/analysis/WorkstreamToggles.tsx`: 5 cards con toggle Switch, nombre (WS-A Source Quality, etc.), descripción corta, tooltip explicativo, y badge de health (verde/amarillo/rojo según `WorkstreamHealth`). Cada toggle llama `configStore.toggleWorkstream`. Botón "Guardar cambios" llama `configStore.saveWorkstreams`.
- [ ] T025 [US1] Crear `frontend/src/analysis/PromptEditor.tsx`: lista lateral de 8 templates con nombre + indicador "Modificado". Área de texto (`<textarea>`) con el contenido del template seleccionado. Botones "Guardar" y "Restaurar default". Al guardar, llama `configStore.savePrompt`. Al restaurar, llama `configStore.restorePrompt` y confirma con diálogo.
- [ ] T026 [US1] Crear `frontend/src/analysis/ConfigView.tsx`: contenedor con dos secciones ("Workstreams", "Prompts"). Importa y renderiza `WorkstreamToggles` y `PromptEditor`. Al montar, dispara `fetchWorkstreams()` + `fetchPrompts()` + `fetchHealth()`.
- [ ] T027 [US1] Modificar `frontend/src/MainLayout.tsx`: agregar `'configuracion'` al union type `MainTab`. Extender array `TABS` con `{ id: 'configuracion', label: 'Configuración', icon: 'settings' }` y `FOLIO` con el número romano IV. Agregar render condicional: `{tab === 'configuracion' && <ConfigView />}`.

### 4.1 — Workstream Indicator

- [ ] T028 [US1] Crear `frontend/src/analysis/WorkstreamIndicator.tsx`: componente que recibe `activeWorkstreams: string[]` y renderiza badges inline (íconos con tooltip). Si vacío, muestra "Sin workstreams activos".
- [ ] T029 [US1] Integrar `WorkstreamIndicator` en `frontend/src/chat/ChatView.tsx`: mostrarlo junto al estado de sesión (`sessionStatus`) durante EXECUTING y COMPLETED. Leer `activeWorkstreams` desde `configStore.workstreams`.

---

## Phase 5: Frontend — Visualización de Resultados (US2)

**Goal**: Secciones colapsables en el reporte para cada workstream activo. Independiente de US1 (ya tiene datos del mock/backend).

**Independent Test**: Iniciar mock server con workstreams activos, completar investigación, verificar que el reporte muestra secciones WS-A y WS-E con datos simulados, y que WS-B/WS-C/WS-D no aparecen si están desactivados.

### 5.1 — Componente base

- [ ] T030 [US2] Crear `frontend/src/analysis/WorkstreamSection.tsx`: wrapper colapsable (`<details open>`). Props: `title`, `icon`, `status` ('active' | 'degraded' | 'inactive'), `children`. Renderiza cabecera con icono, título y badge de estado.

### 5.2 — Secciones por workstream

- [ ] T031 [P] [US2] Crear `frontend/src/analysis/WSASection.tsx`: recibe `data: WsaResult`. Renderiza tabla de `author_reputations` (nombre, h-index, afiliación), badges de `conflicts_of_interest` (risk_level con color), lista de `external_validations` (verified/contradicted/not_found), badges de `retraction_records`, scores de `reproducibility_scores`, y barras de `effective_freshness`.
- [ ] T032 [P] [US2] Crear `frontend/src/analysis/WSBSection.tsx`: recibe `data: WsbResult`. Renderiza stats de `hybrid_search_stats` (cards numéricas), `dedup_rate` (barra de progreso), mini-tabla de `deduped_sources`, badges de `authenticity_signals` (ai_probability con color), y lista de `consensus_disputes` con indicador de acuerdo/desacuerdo.
- [ ] T033 [P] [US2] Crear `frontend/src/analysis/WSCSection.tsx`: recibe `data: WscResult`. Renderiza mini-tarjetas de `s_curves` (growth_rate, inflection_year, r_squared), badges de `implicit_assumptions` (severity con color), lista de `counterfactuals` (scenario + plausibility), lista de `critical_dependencies`, y stats de `meta_analyses` (effect_size_range, i_squared).
- [ ] T034 [P] [US2] Crear `frontend/src/analysis/WSDSection.tsx`: recibe `data: WsdResult`. Renderiza lista de `convergence_clusters` (dominios + growth_trend), lista de `idea_lineages` (seminal → leaf), mini-red de `collaboration_network` (nodos autor + edges co-author), indicador de `narrative_shifts` (sentiment pre/post con flecha), badges de `talent_mobilities`, y badges de `patenting_gaps` (blue_ocean/red_ocean).
- [ ] T035 [P] [US2] Crear `frontend/src/analysis/WSESection.tsx`: recibe `data: WseResult`. Renderiza alerta de `bias_audit` (crítico: rojo, no crítico: verde) con distribuciones geográfico/género/institucional, timeline de `forensic_traces` (trace_steps encadenados), tarjetas de `stakeholder_simulations` (4 tarjetas: critique + counterpoints), lista de `falsification_scenarios`, y curva de calibración (`calibration_curve` con comparación raw vs calibrated). Si `quality_gate_passed === false`, muestra banner de error "Quality Gate bloqueado".

### 5.3 — Integración en ReportSummary

- [ ] T036 [US2] Modificar `frontend/src/chat/ReportSummary.tsx`: si `report.evaluation` existe, renderizar `WorkstreamIndicator` y mapear `report.evaluation.ws_a` → `<WSASection>`, `ws_b` → `<WSBSection>`, etc. Cada sección solo se renderiza si el campo no es `null`. Insertar después del executive summary y antes de `IntelligenceSections`.

### 5.4 — SSE Handler

- [ ] T037 [US2] Modificar `frontend/src/state/sseHandlers.ts`: en el handler de `EvaluationComputed`, además de las KPIs legacy, despachar `configStore.fetchWorkstreams()` para refrescar el indicador. En el handler de `ReportGenerated`, si el payload incluye `evaluation`, guardarlo en el store de sesión. Agregar campo `evaluation?: SessionEvaluation` al `SessionSlice` de `useStore.ts`.

### 5.5 — AnalysisPanel

- [ ] T038 [US2] (Opcional) Modificar `frontend/src/analysis/AnalysisPanel.tsx`: si hay datos de workstreams en la sesión, agregar un selector de workstream en la vista de análisis para alternar entre secciones sin recargar el reporte completo.

---

## Phase 6: Mock Server — Refactor y Workstreams (US4)

**Goal**: Refactorizar `mock_server.py` monolítico en paquete modular, agregar datos simulados de los 5 workstreams, y endpoints de configuración. Independiente del backend real.

**Independent Test**: `python mock_server.py` arranca, frontend se conecta, todos los endpoints existentes responden igual, nuevos endpoints `/config/*` funcionan, SSE stream incluye datos de workstreams.

### 6.1 — Extraer datos a módulos

- [ ] T039 [P] [US4] Crear `mock_server/data/branches.py`: extraer `BRANCH_ITERATIONS`, `REPLAN_SIGNALS`, `CROSS_SESSION_RECURRING` y helpers (`_delta_focus`) desde `mock_server.py`
- [ ] T040 [P] [US4] Crear `mock_server/data/report.py`: extraer `FINAL_REPORT`, `INTELLIGENCE_SECTIONS`, `GRAPH_NODES`, `GRAPH_EDGES`, `MOCK_ECOSYSTEM` desde `mock_server.py`
- [ ] T041 [P] [US4] Crear `mock_server/data/workstreams.py`: definir `MOCK_WSA_DATA` (2 author_reputations, 1 conflict, 2 fact-checks, 1 retraction, 2 reproducibility scores), `MOCK_WSB_DATA` (hybrid stats, 2 deduped sources, 2 authenticity signals, 1 consensus dispute), `MOCK_WSC_DATA` (2 s-curves, 1 meta-analysis, 3 assumptions, 2 counterfactuals, 2 dependencies), `MOCK_WSD_DATA` (2 convergence clusters, 1 collaboration network, 1 idea lineage, 1 narrative shift, 2 talent mobilities, 1 patenting gap), `MOCK_WSE_DATA` (bias audit con distribuciones, 2 forensic traces, 4 stakeholder simulations, 2 falsification scenarios, calibration curve)

### 6.2 — SSE emitter con workstreams

- [ ] T042 [US4] Crear `mock_server/sse_emitter.py`: función `async emit_research_stream(session_id, active_workstreams: set[str])` que emite eventos SSE en secuencia realista (~25-30s total): `SessionStarted` → `ClarificationRequested` → `PlanGenerated` → `BranchStarted x6` → `BranchProgress` (interleaved con tool calls) → `ReplanTriggered x2` → `BranchCompleted x6` → `AllBranchesCompleted` → `FusionStarted` → `FusionProgress` → `GraphBuildingStarted` → `GraphAnalyticsComputed` → `ReportGenerated` (con `evaluation` si hay workstreams activos) → `ReportVariantsGenerated` → `EvaluationComputed`

### 6.3 — Endpoints de research refactorizados

- [ ] T043 [US4] Crear `mock_server/routes/research.py`: extraer todos los endpoints de investigación desde `mock_server.py` (start, clarify, plan, approve, stream, report, sources, graph y sub-rutas, providers, modify, decision, obsolescence, hype-analysis, delete, sessions, reports, sources/score, upload, sandbox). Mantener 100% compatibilidad de respuestas.

### 6.4 — Endpoints de configuración simulados

- [ ] T044 [US4] Crear `mock_server/routes/config.py`: implementar `GET /config/workstreams` (devuelve diccionario en memoria), `PATCH /config/workstreams` (actualiza dict en memoria), `GET /config/workstreams/health` (devuelve todo `available: true`). Implementar `GET /config/prompts` (lista 8 templates con contenido placeholder), `GET /config/prompts/{name}`, `PUT /config/prompts/{name}` (guarda en dict en memoria), `POST /config/prompts/{name}/restore` (restaura placeholder).

### 6.5 — Entry point

- [ ] T045 [US4] Crear `mock_server/__init__.py` vacío y `mock_server/__main__.py` que importa y ejecuta uvicorn con la app
- [ ] T046 [US4] Modificar `mock_server.py`: convertir en thin wrapper que importa `from mock_server import app` y ejecuta `uvicorn.run(app)`. **Eliminar del archivo original todo el código extraído a `mock_server/data/`, `mock_server/routes/` y `mock_server/sse_emitter.py`** — solo deben permanecer los imports y la llamada a uvicorn. Agregar banner de inicio que liste workstreams simulados activos. [Constitution: Cambios Quirurgicos — eliminar codigo huerfano generado por el cambio]

### 6.6 — Workstream toggle en mock

- [ ] T047 [US4] Modificar `mock_server/routes/config.py`: cuando `PATCH /config/workstreams` cambia flags, la siguiente sesión SSE emitida por `sse_emitter.py` incluye o excluye datos de workstreams según los flags activos. Si ningún workstream está activo, `ReportGenerated` no incluye campo `evaluation` (comportamiento pre-007).

---

## Phase 7: Polish & Cross-Cutting

**Goal**: Integración final, documentación, verificaciones. Sin dependencias de fases anteriores (puede ejecutarse en paralelo con cualquier fase).

- [ ] T048 [P] Actualizar `.env.example`: documentar `VT_EVAL_WS_A_ENABLED`..`VT_EVAL_WS_E_ENABLED` en sección "Spec 008", y nuevos paths `WORKSTREAM_OVERRIDES_PATH`, `PROMPT_OVERRIDES_DIR`
- [ ] T049 [P] Ejecutar `scripts/check-layer-imports.py` para verificar que `application/` no importa de `infra/` y que las nuevas rutas de config respetan DIP
- [ ] T050 [P] Ejecutar `npx tsc --noEmit` en `frontend/` para verificar que todos los tipos compilan
- [ ] T051 [P] Ejecutar `ruff check src/vigilancia_multiagente/api/routes/config_*.py src/vigilancia_multiagente/config/workstream_overrides.py src/vigilancia_multiagente/config/prompt_overrides.py` para verificar estilo
- [ ] T052 Probar flujo completo mock server + frontend: (1) Activar WS-A y WS-E desde UI, (2) Iniciar investigación, (3) Verificar SSE stream incluye datos de workstreams, (4) Verificar reporte muestra secciones WS-A y WS-E, (5) Verificar WS-B/WS-C/WS-D no aparecen
- [ ] T053 Probar flujo con flags=false: verificar que el pipeline es byte-idéntico a pre-008 (sin campo `evaluation` en reporte, sin secciones de workstreams)
- [ ] T054 Marcar `mock_server.py` original con comentario `# Deprecated: use mock_server/ package instead. Kept for backward compat.` al inicio del archivo

---

## Dependencies

- **Phase 1 (Setup)** → sin dependencias, ejecutable inmediatamente
- **Phase 2 (Backend API)** → depende de Phase 1 (necesita `workstream_overrides.py` y `prompt_overrides.py`)
- **Phase 3 (Frontend Types/API/Store)** → depende de Phase 2 (necesita endpoints existentes para definir fetch functions). T019-T023 pueden empezar en paralelo con T017-T018.
- **Phase 4 (US1 Config Panel)** → depende de Phase 3 (necesita tipos y store)
- **Phase 5 (US2 Visualization)** → depende de Phase 3 (necesita tipos). Independiente de Phase 4.
- **Phase 6 (US4 Mock Server)** → sin dependencias de backend. T039-T041 (datos) pueden ejecutarse en paralelo. T042-T047 dependen de T039-T041.
- **Phase 7 (Polish)** → sin dependencias estrictas. T048-T051 ejecutables en cualquier momento. T052-T053 requieren fases 4+5+6 completas.

**User Stories Independencia**:
- US1 (Config Panel): Fases 1→2→3→4
- US2 (Visualization): Fases 1→2→3→5
- US4 (Mock Server): Fase 6 (autónoma)
- US1 y US2 comparten Fases 1-3 pero divergen en 4 vs 5 — pueden ejecutarse en paralelo una vez Phase 3 completa

## Parallel Execution Examples

### Phase 1 Parallel Block
- T001, T002 en paralelo (archivos diferentes, sin dependencia mutua)

### Phase 2 Parallel Block
- T005, T006, T007 en paralelo (diferentes endpoints, diferentes archivos)
- T008 depende de T007 (mismo archivo de rutas)
- T012, T013 en paralelo (settings.py vs dependencies.py)

### Phase 3 Parallel Block
- T017, T020, T022 en paralelo (types vs api vs store — diferentes archivos)
- T018 depende de T017 (extiende mismo archivo)
- T021 depende de T020

### Phase 5 Parallel Block
- T031, T032, T033, T034, T035 en paralelo (5 componentes independientes, cada uno en su propio archivo)

### Phase 6 Parallel Block
- T039, T040, T041 en paralelo (3 archivos de datos independientes)
- T043, T044 en paralelo (research routes vs config routes)

## Implementation Strategy

**MVP (US1 solo)**: Fases 1→2→3→4. Entrega: panel de configuración funcionando contra mock server. El administrador puede activar/desactivar workstreams y editar prompts desde la UI. ~14 tareas.

**Incremental 1 (+US4)**: Agregar Fase 6. Entrega: mock server completo con workstreams simulados. El desarrollador frontend puede iterar sin backend real. ~9 tareas adicionales.

**Incremental 2 (+US2)**: Agregar Fase 5. Entrega: visualización completa de resultados de workstreams en el reporte. ~9 tareas adicionales.

**Full**: Fase 7 (polish). ~7 tareas. Total: ~54 tareas.
