# Tasks: Admin Maintenance y Dreaming Mode

**Input**: `specs/017-admin-maintenance-dreaming/spec.md`, `specs/017-admin-maintenance-dreaming/plan.md`
**Feature**: Dreaming mode como orquestador secuencial de fases de auto-mantenimiento. **MVP F5a** (orquestador + memory consolidation + ingestion sync) + **roadmap F5b** (8 fases restantes + 7 loops de autoaprendizaje + Dreaming Report completo).

**Scope**:
- **MVP F5a (Phases 1-4)**: orquestador con scheduler y pause-on-interaction, Fase 1 (memory consolidation), Fase 5 (enterprise ingestion sync), observabilidad minima. NO requiere `AgentModifier` (spec 016).
- **Roadmap F5b (Phases 5-9)**: fases 2, 3, 4, 6, 7, 8, 9, 10 + 7 loops de autoaprendizaje. Consumen `AgentModifier` de spec 016 sin redefinirlo (DRY).

**User Stories del spec**:
- **US1 (P1)**: Operador tiene sistema que ejecuta automaticamente tareas de mantenimiento durante la noche o periodos de inactividad.

**Testing strategy**: test-before-implementation por componente. Tests por fase y por loop.

---

## Phase 1: Orquestador y scheduler MVP [MVP F5a]

Crear el orquestador secuencial, el scheduler (cron + idle), pause-on-interaction y log JSONL.

- [x] T001 Crear `src/vigilancia_multiagente/enterprise/dreaming/__init__.py` como marker del subpaquete dreaming
- [ ] T002 [P] Crear `src/vigilancia_multiagente/enterprise/dreaming/phase_protocol.py` con Protocol `DreamingPhase`: metodo async `execute(context: DreamingContext) -> PhaseResult`, atributo `name: str` (~40 LOC). Traza: FR-002
- [ ] T003 [P] Crear `src/vigilancia_multiagente/enterprise/dreaming/models.py` con dataclasses: `DreamingContext` (cycle_id, started_at, tenant_id, llm_available, phases_to_run), `PhaseResult` (phase_name, status: success|skipped|failed, duration_ms, error, metrics_dict), `CycleReport` (cycle_id, started_at, finished_at, results: list[PhaseResult]) (~60 LOC). Traza: FR-004
- [ ] T004 Crear `src/vigilancia_multiagente/enterprise/dreaming/phases/__init__.py` como marker del subpaquete phases
- [ ] T005 Test `tests/enterprise/dreaming/test_orchestrator.py`: 5 tests (ejecuta fases en orden secuencial; fallo en una fase no detiene el ciclo y registra error; pause detiene al final de fase actual; resume reanuda en proximo ciclo; log JSONL se escribe con resultado por fase). Traza: FR-001, FR-002, FR-003, FR-004, SC-007
- [ ] T006 Implementar `src/vigilancia_multiagente/enterprise/dreaming/orchestrator.py`: clase `DreamingOrchestrator` con lista de fases registradas, metodo async `run_cycle() -> CycleReport` que ejecuta fases en orden y escribe JSONL a `~/.vigilador/audit/dreaming/<YYYY-MM-DD>.jsonl`, metodo `pause()` (flag que detiene al final de fase actual), metodo `resume()`, metodo `register_phase(phase: DreamingPhase)`, property `status` (idle|running|paused) (~250 LOC). Hacer T005 verde. Traza: FR-001, FR-002, FR-003, FR-004
- [ ] T007 Test `tests/enterprise/dreaming/test_scheduler.py`: 4 tests (cron job se configura a hora correcta; idle trigger detecta inactividad > 10 min; pause-on-interaction activa pause del orquestador; configuracion custom desde settings respetada). Traza: FR-001, FR-003, SC-007
- [ ] T008 Implementar `src/vigilancia_multiagente/enterprise/dreaming/scheduler.py`: configuracion APScheduler con cron job (default 3 AM timezone local) + idle trigger (inactividad > 10 min configurable) + pause-on-interaction (flag compartido con session manager) (~100 LOC). Hacer T007 verde. Traza: FR-001, FR-003
- [ ] T009 Wirear `DreamingOrchestrator` en `src/vigilancia_multiagente/api/dependencies.py` como singleton lazy. Solo lineas aditivas
- [ ] T010 Registrar startup hook para scheduler en `src/vigilancia_multiagente/api/app.py`. Solo linea aditiva

**Independent Test Criteria for Phase 1**: `pytest tests/enterprise/dreaming/test_orchestrator.py tests/enterprise/dreaming/test_scheduler.py` verde; orquestador ejecuta fases fake en secuencia; pause-on-interaction funciona; JSONL se escribe correctamente.

---

## Phase 2: Fase 1 - Memory consolidation [MVP F5a]

Implementar la fase de consolidacion de memoria: comprimir sesiones del dia en memoria de largo plazo.

- [ ] T011 Test `tests/enterprise/dreaming/test_memory_consolidation.py`: 5 tests (recoge sesiones no consolidadas del dia; comprime via LLM mock generando resumen + entidades + decisiones; marca sesiones como consolidated=true sin eliminarlas; idempotente -- re-ejecutar no genera duplicados; sesiones corruptas se saltan con log de error). Traza: FR-005, FR-006, FR-007, SC-001, EC-06
- [ ] T012 Implementar `src/vigilancia_multiagente/enterprise/dreaming/phases/memory_consolidation.py`: clase `MemoryConsolidationPhase` que implementa `DreamingPhase`. Recoge sesiones no consolidadas, comprime cada una via LLM (resumen + entidades clave + decisiones), almacena en memoria largo plazo, marca originales como consolidated=true. Idempotente (~250 LOC). Hacer T011 verde. Traza: FR-005, FR-006, FR-007
- [ ] T013 Registrar `MemoryConsolidationPhase` en el orquestador (dentro de factory o startup). Traza: FR-002

**Independent Test Criteria for Phase 2**: `pytest tests/enterprise/dreaming/test_memory_consolidation.py` verde; fase procesa sesiones mock correctamente; idempotencia verificada; sesiones corruptas no rompen el ciclo.

---

## Phase 3: Fase 5 - Enterprise ingestion sync [MVP F5a]

Implementar sincronizacion incremental de conectores con checkpoint por conector.

- [ ] T014 Test `tests/enterprise/dreaming/test_ingestion_sync.py`: 5 tests (itera conectores configurados; procesa solo documentos nuevos/modificados desde checkpoint; actualiza checkpoint tras sync exitosa; fallo en un conector no detiene los demas; re-ejecutar sin cambios = 0 documentos procesados). Traza: FR-008, FR-009, FR-010, SC-002, EC-03
- [ ] T015 Implementar `src/vigilancia_multiagente/enterprise/dreaming/phases/ingestion_sync.py`: clase `IngestionSyncPhase` que implementa `DreamingPhase`. Itera conectores configurados, lee checkpoint (timestamp ultima sync) por conector, procesa documentos nuevos/modificados, actualiza checkpoint. Si un conector falla: registra error, continua con los demas (~200 LOC). Hacer T014 verde. Traza: FR-008, FR-009, FR-010
- [ ] T016 Registrar `IngestionSyncPhase` en el orquestador. Traza: FR-002

**Independent Test Criteria for Phase 3**: `pytest tests/enterprise/dreaming/test_ingestion_sync.py` verde; sync incremental correcto; checkpoint persistido; fallo parcial no detiene otros conectores; idempotencia verificada.

---

## Phase 4: Observabilidad y verificacion MVP [MVP F5a]

Metricas Prometheus del Dreaming y verificacion integral del MVP F5a.

- [ ] T017 [P] Crear `src/vigilancia_multiagente/enterprise/dreaming/metrics.py`: histograms `vigilador_dreaming_phase_duration_seconds{phase}`, counters `vigilador_dreaming_phase_status{phase, status}` (success/skipped/failed) (~50 LOC). Traza: FR-042
- [ ] T018 Integrar emisiones de metricas en `orchestrator.py`: registrar duracion y status por fase al finalizar cada una. Traza: FR-042
- [ ] T019 [P] Correr suite completa `pytest` y verificar 0 regresiones (2.0 + enterprise)
- [ ] T020 [P] Correr `scripts/check-layer-imports.py` y verificar 0 violaciones nuevas
- [ ] T021 [P] Correr `basedpyright src/vigilancia_multiagente/` y verificar 0 nuevos errores
- [ ] T022 [P] Correr `ruff check src/ tests/` + `ruff format src/ tests/` sin issues
- [ ] T023 Verificar SC-001: ejecutar memory consolidation con 50 sesiones mock y confirmar < 5 min + 0 duplicados
- [ ] T024 Verificar SC-002: ejecutar ingestion sync dos veces sin cambios y confirmar 0 documentos procesados en segunda ejecucion
- [ ] T025 Verificar SC-007: simular interaccion de usuario durante ciclo idle-triggered y confirmar pause sin corrupcion
- [ ] T026 Verificar EC-01: ejecutar ciclo con LLM no disponible y confirmar que fases LLM-dependientes se saltan con warning
- [ ] T027 Verificar EC-02: activar idle trigger, simular retorno de usuario, confirmar pause al final de fase actual

**Independent Test Criteria for Phase 4**: MVP F5a completo y verificado; SC-001, SC-002, SC-007 pasan; EC-01, EC-02, EC-03 verificados; metricas Prometheus emitidas; 0 regresiones.

---

## Phase 5: Fases roadmap F5b - Skill curator + Self-improvement [ROADMAP F5b]

Requiere `AgentModifier` de spec 016 implementado.

- [ ] T028 Test `tests/enterprise/dreaming/test_phases_skill_curator.py`: 4 tests (revalida skills contra ejecuciones recientes; depreca skill con >50% fallo en ultimas 5 ejecuciones; promueve skill con 5+ exitos consecutivos a estable; skill deprecated se excluye del discovery). Traza: FR-011, FR-012, FR-013
- [ ] T029 Implementar `src/vigilancia_multiagente/enterprise/dreaming/phases/skill_curator.py`: clase `SkillCuratorPhase` que implementa `DreamingPhase`. Revalida skills, depreca fallidos, promueve estables. Registra cambios via `AgentModifier` (spec 016) (~200 LOC). Hacer T028 verde. Traza: FR-011, FR-012, FR-013
- [ ] T030 Test `tests/enterprise/dreaming/test_phases_self_improvement.py`: 5 tests (detecta prompts con 5+ feedbacks negativos en 7 dias; genera variante via LLM; activa A/B test 50/50; promueve variante ganadora via AgentModifier; revierte variante que cae >10% en confianza). Traza: FR-014, FR-015, FR-016, FR-017, SC-006
- [ ] T031 Implementar `src/vigilancia_multiagente/enterprise/dreaming/phases/self_improvement.py`: clase `SelfImprovementPhase` que implementa `DreamingPhase`. Detecta prompts con feedback negativo, genera variante, A/B test, promocion/reversion via `AgentModifier` (~250 LOC). Hacer T030 verde. Traza: FR-014, FR-015, FR-016, FR-017
- [ ] T032 Registrar ambas fases en el orquestador

**Independent Test Criteria for Phase 5**: tests de ambas fases verdes; skill curator depreca/promueve correctamente; self-improvement genera variantes y revierte las malas.

---

## Phase 6: Fases roadmap F5b - Config refresher + Regulatory watch [ROADMAP F5b]

Requiere `AgentModifier` de spec 016 implementado.

- [ ] T033 Test `tests/enterprise/dreaming/test_phases_config_refresher.py`: 4 tests (detecta gaps en COMPANY por preguntas sin respuesta; genera propuesta de parrafo; propuestas a policies.md quedan pending_approval via AgentModifier; nunca elimina contenido existente). Traza: FR-018, FR-019, FR-020, FR-021
- [ ] T034 Implementar `src/vigilancia_multiagente/enterprise/dreaming/phases/config_refresher.py`: clase `ConfigRefresherPhase` que implementa `DreamingPhase`. Detecta gaps, genera propuestas, aplica via `AgentModifier` (~200 LOC). Hacer T033 verde. Traza: FR-018, FR-019, FR-020, FR-021
- [ ] T035 Test `tests/enterprise/dreaming/test_phases_regulatory_watch.py`: 4 tests (construye queries por company_geo; busca fuentes oficiales; genera propuesta con citas si encuentra info; marca incertidumbre si no encuentra fuente suficiente). Traza: FR-025, FR-026, FR-027, FR-028, FR-029, SC-004, EC-05
- [ ] T036 Implementar `src/vigilancia_multiagente/enterprise/dreaming/phases/regulatory_watch.py`: clase `RegulatoryWatchPhase` que implementa `DreamingPhase`. Queries por company_geo, busqueda fuentes oficiales, comparacion, propuestas con citas. Nunca hardcodea valores normativos (~250 LOC). Hacer T035 verde. Traza: FR-025..FR-029
- [ ] T037 Registrar ambas fases en el orquestador

**Independent Test Criteria for Phase 6**: tests de ambas fases verdes; config refresher no elimina contenido; regulatory watch siempre cita fuente o marca incertidumbre.

---

## Phase 7: Fases roadmap F5b - Index + Artifacts + Admin repos + Report [ROADMAP F5b]

- [ ] T038 [P] Test `tests/enterprise/dreaming/test_phases_index_maintenance.py`: 2 tests (vacuum/compact ejecuta sin error; registra metricas pre/post). Traza: FR-030, FR-031
- [ ] T039 [P] Implementar `src/vigilancia_multiagente/enterprise/dreaming/phases/index_maintenance.py`: clase `IndexMaintenancePhase` (~100 LOC). Hacer T038 verde. Traza: FR-030, FR-031
- [ ] T040 [P] Test `tests/enterprise/dreaming/test_phases_scheduled_artifacts.py`: 2 tests (genera reportes programados; respeta configuracion de frecuencia)
- [ ] T041 [P] Implementar `src/vigilancia_multiagente/enterprise/dreaming/phases/scheduled_artifacts.py`: clase `ScheduledArtifactsPhase` (~150 LOC). Hacer T040 verde
- [ ] T042 [P] Test `tests/enterprise/dreaming/test_phases_admin_repo.py`: 4 tests (detecta nuevas releases; clasifica impacto correctamente; genera propuesta admin con diff y tests; nunca promueve sin aprobacion). Traza: FR-032, FR-033, FR-034, FR-035, SC-005
- [ ] T043 [P] Implementar `src/vigilancia_multiagente/enterprise/dreaming/phases/admin_repo_maintenance.py`: clase `AdminRepoMaintenancePhase`. Revisa repos contra upstream, clasifica impacto, genera propuesta. Nunca promueve sin aprobacion (~300 LOC). Hacer T042 verde. Traza: FR-032..FR-035
- [ ] T044 [P] Test `tests/enterprise/dreaming/test_phases_dreaming_report.py`: 3 tests (genera reporte con changelog + metricas + pendientes; envia a canal configurado; incluye links a rollback). Traza: FR-036, FR-037
- [ ] T045 [P] Implementar `src/vigilancia_multiagente/enterprise/dreaming/phases/dreaming_report.py`: clase `DreamingReportPhase` (~200 LOC). Hacer T044 verde. Traza: FR-036, FR-037
- [ ] T046 Registrar las 4 fases en el orquestador

**Independent Test Criteria for Phase 7**: tests de las 4 fases verdes; admin repo nunca promueve sin aprobacion; dreaming report incluye toda la informacion requerida.

---

## Phase 8: Loops de autoaprendizaje [ROADMAP F5b]

Requiere `AgentModifier` de spec 016. Cada loop es modulo independiente bajo `enterprise/dreaming/loops/`.

- [ ] T047 Crear `src/vigilancia_multiagente/enterprise/dreaming/loops/__init__.py` como marker del subpaquete loops
- [ ] T048 [P] Test `tests/enterprise/dreaming/test_loops_skill_learning.py`: 3 tests (detecta demostracion exitosa; genera skill; registra via AgentModifier)
- [ ] T049 [P] Implementar `src/vigilancia_multiagente/enterprise/dreaming/loops/skill_learning.py`: clase `SkillLearningLoop` (~200 LOC). Hacer T048 verde
- [ ] T050 [P] Test `tests/enterprise/dreaming/test_loops_writing_style.py`: 3 tests (analiza correos aprobados; actualiza writing_style.yaml via AgentModifier; detecta drift severo y flaggea). Traza: FR-022, FR-023, FR-024
- [ ] T051 [P] Implementar `src/vigilancia_multiagente/enterprise/dreaming/loops/writing_style.py`: clase `WritingStyleLoop` (~150 LOC). Hacer T050 verde. Traza: FR-022, FR-023, FR-024
- [ ] T052 [P] Test `tests/enterprise/dreaming/test_loops_prompt_self_improvement.py`: 3 tests (genera variante; ejecuta A/B test; revierte si cae >10%)
- [ ] T053 [P] Implementar `src/vigilancia_multiagente/enterprise/dreaming/loops/prompt_self_improvement.py`: clase `PromptSelfImprovementLoop` (~250 LOC). Hacer T052 verde
- [ ] T054 [P] Test `tests/enterprise/dreaming/test_loops_tool_composition.py`: 3 tests (detecta secuencias repetidas 10+ veces; genera skill compuesto; nunca sobrescribe skill existente). Traza: FR-038, FR-039, FR-040, FR-041
- [ ] T055 [P] Implementar `src/vigilancia_multiagente/enterprise/dreaming/loops/tool_composition.py`: clase `ToolCompositionLoop` (~200 LOC). Hacer T054 verde. Traza: FR-038..FR-041
- [ ] T056 [P] Test `tests/enterprise/dreaming/test_loops_company_self_update.py`: 3 tests (detecta gaps; genera propuesta; aplica via AgentModifier)
- [ ] T057 [P] Implementar `src/vigilancia_multiagente/enterprise/dreaming/loops/company_self_update.py`: clase `CompanySelfUpdateLoop` (~200 LOC). Hacer T056 verde
- [ ] T058 [P] Test `tests/enterprise/dreaming/test_loops_regulatory_watcher.py`: 3 tests (busqueda por company_geo; propuesta con citas; marca incertidumbre)
- [ ] T059 [P] Implementar `src/vigilancia_multiagente/enterprise/dreaming/loops/regulatory_watcher.py`: clase `RegulatoryWatcherLoop` (~250 LOC). Hacer T058 verde
- [ ] T060 [P] Test `tests/enterprise/dreaming/test_loops_admin_repo.py`: 3 tests (detecta releases; clasifica impacto; no promueve sin aprobacion)
- [ ] T061 [P] Implementar `src/vigilancia_multiagente/enterprise/dreaming/loops/admin_repo_loop.py`: clase `AdminRepoLoop` (~250 LOC). Hacer T060 verde
- [ ] T062 Integrar los 7 loops con sus fases correspondientes (Loop 3 invocado por Fase 3, Loop 5 por Fase 4, Loop 6 por Fase 6, Loop 7 por Fase 9). Traza: FR-043

**Independent Test Criteria for Phase 8**: tests de los 7 loops verdes; todos registran cambios via AgentModifier; tool composition nunca sobrescribe skills existentes; todos los loops son invocables desde sus fases correspondientes.

---

## Phase 9: Verificacion integral F5b [ROADMAP F5b]

Validacion final del spec completo (MVP + roadmap).

- [ ] T063 Correr ciclo Dreaming completo (10 fases) y verificar SC-003: finaliza en < 30 min para tenant con 50 sesiones/dia, 500 docs, 20 tools
- [ ] T064 Verificar SC-004: regulatory watch genera propuestas con cita en 100% de casos con info; marca incertidumbre en 100% sin fuente
- [ ] T065 Verificar SC-005: admin repo detecta 100% de releases y nunca promueve sin aprobacion
- [ ] T066 Verificar SC-006: A/B test revierte variantes que caen >10% en confianza en < 24h
- [ ] T067 Verificar EC-01..EC-06 con evidencia documentada
- [ ] T068 [P] Correr suite completa `pytest` y verificar 0 regresiones
- [ ] T069 [P] Correr `scripts/check-layer-imports.py` y verificar 0 violaciones
- [ ] T070 [P] Correr `basedpyright` + `ruff` sin issues nuevos
- [ ] T071 Verificar que metricas FR-043 (`vigilador_skill_learned_total`, `vigilador_skill_curator_revalidated_total`, `vigilador_regulatory_watch_total`, `vigilador_admin_repo_updates_detected_total`) se emiten correctamente

**Independent Test Criteria for Phase 9**: spec 017 completo (MVP + roadmap); todos los SC pasan; todos los EC verificados; 0 regresiones; metricas completas.

---

## Dependencies

- **Phase 1 (Orquestador)** must complete before **Phase 2 (Memory consolidation)** y **Phase 3 (Ingestion sync)**.
- **Phase 2** y **Phase 3** son independientes entre si (fases distintas, archivos distintos).
- **Phase 4 (Observabilidad MVP)** requiere Phases 1, 2 y 3 completas.
- **Phases 5, 6, 7, 8** (roadmap F5b) requieren Phase 4 completa + spec 016 (`AgentModifier`) implementado.
- **Phases 5 y 6** son independientes entre si.
- **Phase 7** es independiente de Phases 5 y 6.
- **Phase 8 (Loops)** depende de Phases 5, 6 y 7 (loops se integran con fases correspondientes).
- **Phase 9 (Verificacion)** requiere Phases 1-8 completas.
- Dentro de **Phase 1**: T001..T004 (estructura + protocol + models) antes de T005 (test orquestador); T005 antes de T006 (implementar orquestador); T007 antes de T008 (scheduler).
- Dentro de **Phase 8**: todos los pares test/implementacion (T048/T049, T050/T051, etc.) son independientes entre si (archivos distintos, [P]).
- **Dependencias externas**:
  - spec 009 (estructura enterprise/, scheduler APScheduler) -- prerequisito de Phase 1.
  - spec 010 F2 (conectores de ingestion) -- prerequisito de Phase 3.
  - spec 016 (`AgentModifier`) -- prerequisito de Phases 5-8 (roadmap F5b). NO requerido para MVP F5a.

---

## Parallel Execution Examples

### Phase 1 Parallel Block

- Run **T002, T003** en paralelo (protocol + models, archivos distintos).
- T005 y T007 (tests) en paralelo tras T001..T004.
- T006 y T008 secuenciales tras sus tests respectivos.
- T009 y T010 en paralelo tras T006 y T008.

### Phases 2 y 3 Parallel Block

Tras Phase 1 verde, distribuir:
- **Dev A -- Memory**: T011 -> T012 -> T013.
- **Dev B -- Ingestion**: T014 -> T015 -> T016.

### Phase 4 Parallel Block

- Run **T017, T019, T020, T021, T022** en paralelo (metricas + linters independientes).
- Luego **T023..T027** secuencial (verificaciones SC/EC).

### Phase 7 Parallel Block

- Run **T038/T039, T040/T041, T042/T043, T044/T045** en paralelo (4 fases distintas, archivos independientes).

### Phase 8 Parallel Block

- Run **T048/T049, T050/T051, T052/T053, T054/T055, T056/T057, T058/T059, T060/T061** todos en paralelo (7 loops independientes, archivos distintos).

### Phase 9 Parallel Block

- Run **T068, T069, T070** en paralelo (linters/tests).
- Luego **T063..T067, T071** secuencial (verificaciones SC/EC manuales).

---

## Implementation Strategy

1. **MVP F5a primero (Phases 1-4)**: entregar en 1 semana. Orquestador + memory consolidation + ingestion sync + observabilidad. Gate: SC-001, SC-002, SC-007 pasan. Cero dependencia de spec 016.
2. **Roadmap F5b despues (Phases 5-9)**: activar solo cuando spec 016 (`AgentModifier`) este implementado y MVP valide la arquitectura. Los loops consumen `AgentModifier` directamente sin redefinirlo (DRY).
3. **Phases 2 y 3 en paralelo**: memory consolidation e ingestion sync son fases independientes. Distribuir entre desarrolladores.
4. **Phase 8 (Loops) altamente paralelizable**: 7 loops independientes, cada uno en su archivo. Maximo paralelismo posible.
5. **Backward compatibility total**: cero cambios al 2.0. Solo 2 archivos existentes modificados en modo aditivo (dependencies.py, app.py).
6. **Feature flag implicito**: fases F5b solo se registran en el orquestador cuando sus dependencias estan disponibles (spec 016 instalado). Sin flag explicito: la presencia del modulo es el flag (OCP).
7. **Pause-on-interaction como safety net**: si el usuario reanuda actividad durante ciclo idle-triggered, Dreaming se pausa al final de la fase actual. Sin corrupcion de estado.
