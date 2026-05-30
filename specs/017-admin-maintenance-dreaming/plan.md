# Implementation Plan: Admin Maintenance y Dreaming Mode

**Feature ID**: 017-admin-maintenance-dreaming
**Created**: 2026-05-29
**Spec**: [spec.md](spec.md)

## Problem

El agente acumula sesiones, documentos indexados, skills aprendidos, configuracion empresarial y dependencias externas (repos de tools/MCPs) que requieren mantenimiento continuo. Sin un proceso automatizado de consolidacion, sincronizacion y revision, el sistema degrada: la memoria crece sin compresion, los indices se fragmentan, la normativa local queda desactualizada, y los repos de tools/MCPs acumulan versiones obsoletas o vulnerables.

Actualmente no existe ningun proceso de mantenimiento automatizado. Este plan implementa el Dreaming mode como orquestador secuencial de fases de auto-mantenimiento, distinguiendo claramente entre el scope MVP F5a (memory consolidation + ingestion sync) y el roadmap F5b (loops de autoaprendizaje, regulatory watch, admin repo maintenance, Dreaming Report completo).

## Approach

Implementar un orquestador `DreamingOrchestrator` que ejecuta fases secuencialmente, activable por cron (3 AM) o idle > 10 min. Cada fase es un modulo independiente con interfaz uniforme (input: contexto del ciclo; output: resultado + metricas). El orquestador no conoce la logica interna de cada fase.

**Arquitectura fase vs loop**: una *fase* es la unidad de scheduling del orquestador (un archivo, una clase `DreamingPhase`, invocada via `phase.execute(context)`). Un *loop* es logica de autoaprendizaje reutilizable (bajo `loops/`, expone `async run(context) -> LoopResult`). Las fases PUEDEN delegar a loops internamente (composicion); el orquestador solo conoce fases.

**Scope MVP vs Roadmap**:
- **MVP F5a (1 semana)**: solo Fase 1 (memory consolidation) y Fase 5 (enterprise ingestion sync) + orquestador minimo con scheduler y pause-on-interaction. Estas dos fases NO modifican archivos de config, por lo que NO requieren `AgentModifier` (spec 016).
- **Roadmap F5b**: las 8 fases restantes (2, 3, 4, 6, 7, 8, 9, 10) + los 7 loops de autoaprendizaje + Dreaming Report completo. Estas fases SI consumen `AgentModifier` de spec 016 para registrar cambios a config. La tabla SQL `agent_modifications` es prerequisito de F5b, no de F5a.

---

## Technical Context

| Area | Decision |
|------|----------|
| Lenguaje | Python 3.11+ (mismo que 2.0 y enterprise/) |
| Scheduler | APScheduler (ya instalado por spec 009) para cron + idle trigger |
| Orquestacion | Secuencial simple (no DAG). Fallo en una fase no detiene el ciclo. |
| Persistencia ciclo | JSONL en `~/.vigilador/audit/dreaming/<YYYY-MM-DD>.jsonl` |
| Memory consolidation | Compresion via LLM activo (resumen + entidades + decisiones). Persistencia en `~/.vigilador/memory/consolidated.jsonl` (append-only) |
| Ingestion sync | Checkpoint por conector en `~/.vigilador/memory/sync_checkpoints.jsonl` (JSONL, un registro por conector) |
| Observabilidad | Prometheus histograms/counters via `prometheus-client` |
| Pause-on-interaction | Flag compartido entre scheduler y session manager |
| Loops autoaprendizaje (F5b) | Cada loop es modulo independiente bajo `enterprise/dreaming/loops/` |
| Registro de cambios (F5b) | Via `AgentModifier` de spec 016 (no se redefine aqui -- DRY) |

## External Constraints

| Constraint | Impact |
|------------|--------|
| Constitucion v1.2.0 #5 Cambios quirurgicos | Cero modificaciones a modulos del 2.0. Solo archivos nuevos bajo `enterprise/`. |
| Dependencia spec 009 | Infraestructura base (MigrationRunner + SQL crudo, scheduler, estructura enterprise/) debe existir. |
| Dependencia spec 010 (F2) | Conectores de ingestion deben existir para Fase 5. |
| Dependencia spec 016 (solo F5b) | `AgentModifier` requerido solo para loops de autoaprendizaje (roadmap F5b). |
| DRY con spec 016 | Este plan NO redefine audit trail, rollback ni approval-gate. Los loops invocan `AgentModifier`. |
| Archivos <= 400 LOC | Cada fase es un modulo independiente dentro del limite. |
| YAGNI | Fases roadmap F5b se especifican para completitud pero NO se implementan hasta que MVP valide. |

---

## Files to Create / Modify

### New Files -- MVP F5a

| File | Purpose |
|------|---------|
| `src/vigilancia_multiagente/enterprise/dreaming/__init__.py` | Marker subpaquete dreaming |
| `src/vigilancia_multiagente/enterprise/dreaming/orchestrator.py` | `DreamingOrchestrator`: scheduler, ejecucion secuencial, pause-on-interaction, log JSONL (~250 LOC) |
| `src/vigilancia_multiagente/enterprise/dreaming/phase_protocol.py` | Protocol `DreamingPhase` con interfaz uniforme: `execute(context) -> PhaseResult` (~40 LOC) |
| `src/vigilancia_multiagente/enterprise/dreaming/models.py` | Dataclasses: `DreamingContext`, `PhaseResult`, `CycleReport` (~60 LOC) |
| `src/vigilancia_multiagente/enterprise/dreaming/phases/__init__.py` | Marker subpaquete phases |
| `src/vigilancia_multiagente/enterprise/dreaming/phases/memory_consolidation.py` | Fase 1: recoger sesiones, comprimir, fusionar en memoria largo plazo (~250 LOC) |
| `src/vigilancia_multiagente/enterprise/dreaming/phases/ingestion_sync.py` | Fase 5: sync incremental de conectores, checkpoint por conector (~200 LOC) |
| `src/vigilancia_multiagente/enterprise/dreaming/scheduler.py` | Configuracion APScheduler: cron 3 AM + idle trigger (~100 LOC) |
| `src/vigilancia_multiagente/enterprise/dreaming/metrics.py` | Prometheus: `dreaming_phase_duration_seconds`, `dreaming_phase_status` (~50 LOC) |
| `tests/enterprise/dreaming/test_orchestrator.py` | Tests del orquestador: secuencia, fallo parcial, pause |
| `tests/enterprise/dreaming/test_memory_consolidation.py` | Tests Fase 1: idempotencia, compresion, marcado consolidated |
| `tests/enterprise/dreaming/test_ingestion_sync.py` | Tests Fase 5: incremental, checkpoint, fallo parcial conector |
| `tests/enterprise/dreaming/test_scheduler.py` | Tests scheduler: cron, idle trigger, pause-on-interaction |

### New Files -- Roadmap F5b (no implementar hasta activacion)

| File | Purpose |
|------|---------|
| `src/vigilancia_multiagente/enterprise/dreaming/phases/skill_curator.py` | Fase 2: revalidar skills, deprecar fallidos (~200 LOC) |
| `src/vigilancia_multiagente/enterprise/dreaming/phases/self_improvement.py` | Fase 3: detectar prompts con feedback negativo, A/B test (~250 LOC) |
| `src/vigilancia_multiagente/enterprise/dreaming/phases/config_refresher.py` | Fase 4: detectar gaps COMPANY, proponer actualizaciones (~200 LOC) |
| `src/vigilancia_multiagente/enterprise/dreaming/phases/regulatory_watch.py` | Fase 6: busqueda normativa por company_geo (~250 LOC) |
| `src/vigilancia_multiagente/enterprise/dreaming/phases/index_maintenance.py` | Fase 7: vacuum/compact TurboVecIndex (~100 LOC) |
| `src/vigilancia_multiagente/enterprise/dreaming/phases/scheduled_artifacts.py` | Fase 8: generar dashboards y reportes programados (~150 LOC) |
| `src/vigilancia_multiagente/enterprise/dreaming/phases/admin_repo_maintenance.py` | Fase 9: revisar repos tools/MCPs contra upstream (~300 LOC) |
| `src/vigilancia_multiagente/enterprise/dreaming/phases/dreaming_report.py` | Fase 10: generar reporte con changelog + metricas (~200 LOC) |
| `src/vigilancia_multiagente/enterprise/dreaming/loops/__init__.py` | Marker subpaquete loops |
| `src/vigilancia_multiagente/enterprise/dreaming/loops/skill_learning.py` | Loop 1: aprendizaje por demostracion (~200 LOC) |
| `src/vigilancia_multiagente/enterprise/dreaming/loops/writing_style.py` | Loop 2: aprendizaje estilo escritura (~150 LOC) |
| `src/vigilancia_multiagente/enterprise/dreaming/loops/prompt_self_improvement.py` | Loop 3: variantes de prompts + A/B test (~250 LOC) |
| `src/vigilancia_multiagente/enterprise/dreaming/loops/tool_composition.py` | Loop 4: deteccion secuencias repetidas, skill compuesto (~200 LOC) |
| `src/vigilancia_multiagente/enterprise/dreaming/loops/company_self_update.py` | Loop 5: detectar gaps COMPANY, proponer contenido (~200 LOC) |
| `src/vigilancia_multiagente/enterprise/dreaming/loops/regulatory_watcher.py` | Loop 6: busqueda normativa localizada (~250 LOC) |
| `src/vigilancia_multiagente/enterprise/dreaming/loops/admin_repo_loop.py` | Loop 7: mantenimiento repos clonados (~250 LOC) |
| `tests/enterprise/dreaming/test_loops_*.py` | Tests por cada loop (7 archivos) |
| `tests/enterprise/dreaming/test_phases_f5b_*.py` | Tests por cada fase F5b (8 archivos) |

### Modified Files

| File | Changes |
|------|---------|
| `src/vigilancia_multiagente/config/settings.py` | Anadir fields: `dreaming_enabled: bool = True`, `dreaming_cron_hour: int = 3`, `dreaming_idle_timeout_min: int = 10`. Solo lineas aditivas. |
| `src/vigilancia_multiagente/api/dependencies.py` | Wirear `DreamingOrchestrator` como singleton lazy. Solo lineas aditivas. |
| `src/vigilancia_multiagente/api/app.py` | Registrar startup hook para scheduler del Dreaming. Solo linea aditiva. |

---

## Constitution Check (Pre-Design)

- **Gate result**: PASS
- **Alignment**:
  - **Pensar Antes de Codificar**: Supuestos A-01..A-08 del spec declarados. Scope MVP F5a vs roadmap F5b explicitamente separado. Dependencias con specs 009, 010, 016 documentadas.
  - **Simplicidad Obligatoria**: orquestador secuencial simple (no DAG, no paralelismo). Cada fase es un modulo con interfaz uniforme. Sin abstracciones especulativas.
  - **Modularidad Primero**: cada fase es un modulo independiente bajo `phases/`. Cada loop bajo `loops/`. El orquestador no conoce logica interna de fases. Protocol `DreamingPhase` define contrato.
  - **Cambios Quirurgicos y Trazables**: solo 2 archivos existentes modificados en modo aditivo. Cero refactors laterales.
  - **Entrega Verificable**: MVP F5a verificable en 1 semana con 4 fases. SC medibles. Tests por fase.
- **Diseno de Software**: SRP (cada fase un modulo, cada loop un modulo), SoC (orquestacion separada de logica de fase), DIP (fases implementan Protocol, orquestador depende de abstraccion), OCP (anadir fase = anadir modulo sin tocar orquestador), CQS (orchestrator.run() es command; orchestrator.status() es query), DRY (no redefine audit trail de spec 016), KISS (secuencial simple), YAGNI (F5b documentado pero no implementado hasta activacion).

---

## Phases

### Phase 1 -- Orquestador y scheduler MVP (2 dias)

1. Crear `enterprise/dreaming/phase_protocol.py` con Protocol `DreamingPhase`: metodo `execute(context: DreamingContext) -> PhaseResult`.
2. Crear `enterprise/dreaming/models.py` con dataclasses del ciclo.
3. Crear `enterprise/dreaming/orchestrator.py`:
   - `DreamingOrchestrator` con lista de fases registradas.
   - Metodo `run_cycle()`: ejecuta fases en orden, registra resultado por fase en JSONL, continua si una falla.
   - Metodo `pause()`: flag que detiene al final de la fase actual.
   - Metodo `resume()`: reanuda en proximo ciclo.
4. Crear `enterprise/dreaming/scheduler.py`:
   - Cron job configurable (default 3 AM timezone local).
   - Idle trigger: detecta inactividad > 10 min (configurable).
   - Pause-on-interaction: si usuario reanuda, pausa Dreaming.
5. Wirear en `dependencies.py` y `app.py`.
6. Tests del orquestador y scheduler.

**Output**: orquestador funcional con scheduler, pause-on-interaction y log JSONL. Sin fases reales todavia. Traza: FR-001, FR-002, FR-003, FR-004, SC-007.

### Phase 2 -- Fase 1: Memory consolidation MVP (2 dias)

1. Crear `enterprise/dreaming/phases/memory_consolidation.py`:
   - Implementa `DreamingPhase`.
   - Recoge sesiones del dia no consolidadas de la capa de memoria.
   - Comprime cada sesion via LLM: resumen + entidades clave + decisiones.
   - Almacena resultado en memoria de largo plazo.
   - Marca sesiones originales como `consolidated = true` sin eliminarlas.
   - Idempotente: re-ejecutar no genera duplicados.
2. Registrar fase en el orquestador.
3. Tests: idempotencia, compresion correcta, marcado, manejo de sesiones corruptas (EC-06).

**Output**: Fase 1 operativa. Traza: FR-005, FR-006, FR-007, SC-001.

### Phase 3 -- Fase 5: Enterprise ingestion sync MVP (2 dias)

1. Crear `enterprise/dreaming/phases/ingestion_sync.py`:
   - Implementa `DreamingPhase`.
   - Itera conectores configurados (Drive, OneDrive, local_fs).
   - Por cada conector: lee checkpoint (timestamp ultima sync), procesa documentos nuevos/modificados, actualiza checkpoint.
   - Si un conector falla: registra error, continua con los demas (EC-03).
   - Re-ejecutar sin cambios = 0 documentos procesados.
2. Registrar fase en el orquestador.
3. Tests: incremental correcto, checkpoint persistido, fallo parcial, idempotencia.

**Output**: Fase 5 operativa. Traza: FR-008, FR-009, FR-010, SC-002.

### Phase 4 -- Observabilidad y verificacion MVP (1 dia)

1. Crear `enterprise/dreaming/metrics.py` con Prometheus histograms/counters.
2. Integrar emisiones en orquestador (duracion por fase, status por fase).
3. Correr bateria completa `pytest`, verificar 0 regresiones.
4. Verificar SC-001, SC-002, SC-007 con evidencia.
5. Verificar EC-01 (LLM no disponible), EC-02 (pause-on-interaction), EC-03 (conector falla).

**Output**: MVP F5a completo y verificado. Traza: FR-042, SC-001, SC-002, SC-007.

### Phase 5 -- Fases roadmap F5b: Skill curator + Self-improvement (3 dias) [ROADMAP]

1. Crear `phases/skill_curator.py` (Fase 2): revalidar skills, deprecar fallidos, promover estables. Traza: FR-011, FR-012, FR-013.
2. Crear `phases/self_improvement.py` (Fase 3): detectar prompts con feedback negativo, generar variante, A/B test, promocion/reversion. Traza: FR-014, FR-015, FR-016, FR-017.
3. Ambas fases registran cambios via `AgentModifier` (spec 016).
4. Tests por fase.

**Output**: Fases 2 y 3 operativas. Traza: SC-003, SC-006.

### Phase 6 -- Fases roadmap F5b: Config refresher + Regulatory watch (3 dias) [ROADMAP]

1. Crear `phases/config_refresher.py` (Fase 4): detectar gaps COMPANY, generar propuestas, aplicar via `AgentModifier`. Traza: FR-018, FR-019, FR-020, FR-021.
2. Crear `phases/regulatory_watch.py` (Fase 6): queries por company_geo, buscar fuentes oficiales, comparar, generar propuestas con citas. Traza: FR-025..FR-029.
3. Tests por fase.

**Output**: Fases 4 y 6 operativas. Traza: SC-004.

### Phase 7 -- Fases roadmap F5b: Index + Artifacts + Admin repos + Report (3 dias) [ROADMAP]

1. Crear `phases/index_maintenance.py` (Fase 7): vacuum/compact TurboVecIndex. Traza: FR-030, FR-031.
2. Crear `phases/scheduled_artifacts.py` (Fase 8): generar reportes programados.
3. Crear `phases/admin_repo_maintenance.py` (Fase 9): revisar repos contra upstream, clasificar impacto, generar propuesta admin. Traza: FR-032..FR-035.
4. Crear `phases/dreaming_report.py` (Fase 10): generar reporte con changelog + metricas + pendientes. Traza: FR-036, FR-037.
5. Tests por fase.

**Output**: Fases 7-10 operativas. Traza: SC-003, SC-005.

### Phase 8 -- Loops de autoaprendizaje roadmap F5b (5 dias) [ROADMAP]

1. Crear `loops/skill_learning.py` (Loop 1): aprendizaje por demostracion. Traza: doc 05 Loop 1.
2. Crear `loops/writing_style.py` (Loop 2): aprendizaje estilo escritura. Traza: FR-022, FR-023, FR-024.
3. Crear `loops/prompt_self_improvement.py` (Loop 3): variantes + A/B test. Invocado por Fase 3.
4. Crear `loops/tool_composition.py` (Loop 4): deteccion secuencias, skill compuesto. Traza: FR-038..FR-041.
5. Crear `loops/company_self_update.py` (Loop 5): gaps COMPANY. Invocado por Fase 4.
6. Crear `loops/regulatory_watcher.py` (Loop 6): normativa localizada. Invocado por Fase 6.
7. Crear `loops/admin_repo_loop.py` (Loop 7): mantenimiento repos. Invocado por Fase 9.
8. Todos los loops registran cambios via `AgentModifier` (spec 016).
9. Tests por loop.

**Output**: 7 loops operativos, integrados con fases correspondientes. Traza: FR-043.

### Phase 9 -- Verificacion integral F5b (2 dias) [ROADMAP]

1. Correr ciclo Dreaming completo (10 fases) y verificar SC-003 (< 30 min).
2. Verificar SC-004 (regulatory watch con citas).
3. Verificar SC-005 (admin repo no promueve sin aprobacion).
4. Verificar SC-006 (A/B test revierte variantes malas).
5. Verificar todos los edge cases EC-01..EC-06.
6. Correr `pytest` completo, 0 regresiones.

**Output**: spec 017 completo (MVP + roadmap).

---

## Rollout Strategy

**MVP F5a (Phases 1-4)**: se entrega en 1 semana como parte del MVP. Solo memory consolidation + ingestion sync + orquestador con scheduler. No requiere `AgentModifier` ni tabla `agent_modifications`. Backward compatible: cero cambios al 2.0.

**Roadmap F5b (Phases 5-9)**: se activa despues de que:
1. MVP valide la arquitectura base (specs 009-013 completos).
2. Spec 016 (`AgentModifier`) este implementado (prerequisito para loops que modifican config).
3. Spec 012 (modos) este implementado (prerequisito para `mode_settings.intensity`).

**Estrategia incremental F5b**:
- Phases 5-6 primero (loops mas criticos: skill curator, self-improvement, config refresher, regulatory watch).
- Phase 7 despues (fases de mantenimiento menos urgentes).
- Phase 8 ultimo (loops completos, mayor complejidad).

**Backward compatibility**: el orquestador ejecuta solo las fases registradas. En MVP F5a solo estan registradas Fase 1 y Fase 5. Anadir fases F5b = registrar modulos nuevos sin tocar el orquestador (OCP).

**Pause-on-interaction**: si el usuario reanuda actividad durante un ciclo idle-triggered, Dreaming se pausa al final de la fase actual. No hay corrupcion de estado.

**Feature flag implicito**: las fases F5b solo se registran en el orquestador cuando sus dependencias estan disponibles (spec 016 instalado, spec 012 instalado). Sin flag explicito: la presencia del modulo es el flag.

---

## Success Criteria

- **SC-001**: Memory consolidation procesa el 100% de las sesiones del dia sin duplicados y en menos de 5 minutos para un dia tipico (50 sesiones). [MVP F5a]
- **SC-002**: Ingestion sync procesa solo documentos nuevos/modificados; re-ejecutar sin cambios en conectores resulta en 0 documentos procesados. [MVP F5a]
- **SC-003**: Un ciclo Dreaming completo (10 fases) finaliza en menos de 30 minutos para un tenant con 50 sesiones/dia, 500 documentos indexados y 20 tools registradas. [Roadmap F5b]
- **SC-004**: La Fase 6 (regulatory watch) genera propuestas con cita a fuente oficial en el 100% de los casos donde encuentra informacion; marca incertidumbre en el 100% de los casos donde no la encuentra. [Roadmap F5b]
- **SC-005**: La Fase 9 (admin repo maintenance) detecta el 100% de las nuevas releases de repos clonados y NUNCA promueve cambios sin aprobacion. [Roadmap F5b]
- **SC-006**: El A/B test de prompts (Fase 3) revierte automaticamente variantes que caen >10% en confianza, en menos de 24 horas desde la deteccion. [Roadmap F5b]
- **SC-007**: Dreaming se pausa correctamente cuando el usuario reanuda interaccion, sin corromper estado de la fase en curso. [MVP F5a]

## Constitution Check (Post-Design)

- **Status**: PASS
- **Justification**:
  - **Pensar Antes de Codificar**: scope MVP F5a vs roadmap F5b declarado en cada fase. Dependencias explicitas. Supuestos del spec preservados. Phases 5-9 marcadas como [ROADMAP] para evitar implementacion prematura.
  - **Simplicidad Obligatoria**: orquestador secuencial simple. Cada fase un modulo. Sin DAGs, sin paralelismo, sin event bus. La complejidad se distribuye en modulos pequenos (<=300 LOC cada uno).
  - **Modularidad Primero**: Protocol `DreamingPhase` define contrato. Cada fase y cada loop es un modulo independiente. Anadir fase = anadir archivo sin tocar orquestador (OCP). Orquestador no conoce logica interna de fases (SoC).
  - **Cambios Quirurgicos y Trazables**: 2 archivos existentes modificados en modo aditivo. Cero refactors. Cada archivo nuevo traza a FRs del spec.
  - **Entrega Verificable**: MVP F5a verificable en 4 phases (1 semana). SC medibles por scope. Tests por fase y por loop. Edge cases cubiertos.
  - **Diseno de Software**: SRP (fase = un concern), SoC (orquestacion/fases/loops/persistence separados), DIP (Protocol como abstraccion), OCP (extensible sin modificar), CQS (run_cycle es command, status es query), DRY (no redefine audit trail de spec 016; loops invocan AgentModifier sin reimplementarlo), KISS (secuencial, sin over-engineering), YAGNI (F5b documentado pero no implementado hasta necesidad real).
