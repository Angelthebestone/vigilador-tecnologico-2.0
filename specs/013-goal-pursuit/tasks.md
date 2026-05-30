# Tasks: Goal-Pursuit (Ejecucion Autonoma Prolongada con Checkpoints)

**Input**: `specs/013-goal-pursuit/spec.md`, `specs/013-goal-pursuit/plan.md`
**Feature**: Playbook `goal-pursuit` como flujo proactivo que persigue objetivos de larga duracion con descomposicion en DAG de sub-goals, capability tokens con TTL, checkpoint reporter y approval gates.

**Status**: Roadmap post-MVP. Tareas gated hasta priorizacion. Dependencias bloqueantes: spec 009 (PlaybookRunner, SubagentRegistry, tabla subagents), spec 012 (infraestructura de approval gates compartida).

**User Stories del spec**:
- **US1 (P1)**: Usuario empresarial asigna un objetivo complejo que requiere multiples pasos durante varias horas; el sistema lo persigue autonomamente reportando progreso y pidiendo aprobacion en puntos criticos.

**Testing strategy**: test-before-implementation por componente. Cada componente (decomposer, resolver, reporter, gate, token, executor) tiene tests dedicados antes de su implementacion.

---

## Phase 1: Extension de schema y modelo de capability tokens

Objetivo: extender tabla `subagents` con columnas goal-pursuit y crear modelo de capability tokens (FR-005, FR-006).

- [ ] T001 [US1] Crear migración SQL cruda `src/vigilancia_multiagente/infra/db/migrations/007_goal_pursuit.sql` que extienda tabla `subagents` con columnas: `parent_goal_id UUID REFERENCES subagents(id)`, `capability_token JSONB` (almacena goal_id, ttl_seconds, scopes, issued_at, expires_at para sobrevivir restart), `goal_dag JSONB` (DAG serializado con estado de cada nodo). Índice en `parent_goal_id`. DDL idempotente con `ADD COLUMN IF NOT EXISTS`. Aplicada por MigrationRunner. Nota: `pause_reason`, `resume_token`, `last_progress_at` ya existen en 006 (FR-006)
- [ ] T002 [US1] Test migración `tests/enterprise/orchestration/goal_pursuit/test_migration_007.py`: aplicar 007_goal_pursuit.sql dos veces sin error (idempotencia); verificar aislamiento de tablas del 2.0 (tool_health, oauth_credentials, pending_approvals, company_profile intactas tras aplicar 007)
- [ ] T003 [P] [US1] Crear `tests/enterprise/orchestration/goal_pursuit/test_capability_token.py` con 4 tests: emision con TTL correcto; `is_expired()` retorna True tras TTL; `remaining_seconds()` calcula correctamente; `reissue(new_ttl)` genera nuevo token con TTL extendido (FR-005, SC-003)
- [ ] T004 [US1] Implementar `src/vigilancia_multiagente/enterprise/orchestration/goal_pursuit/capability_token.py` (~150 LOC): modelo `CapabilityToken(goal_id, ttl_seconds, scopes, issued_at, expires_at)` con metodos `is_expired()`, `remaining_seconds()`, `reissue(new_ttl)`. Hacer T003 verde (FR-005)
- [ ] T005 [P] Crear `src/vigilancia_multiagente/enterprise/orchestration/goal_pursuit/__init__.py` como marker del subpaquete

**Independent Test Criteria for Phase 1**: migración 007 aplica dos veces sin error (idempotente); modelo CapabilityToken tipado correctamente; tests de token verdes; tablas existentes del 2.0 intactas.

---

## Phase 2: GoalDecomposer y DependencyResolver

Objetivo: implementar descomposicion de objetivos en DAG y resolucion de dependencias con deteccion de ciclos (FR-001, FR-002, FR-008, FR-009).

- [ ] T006 [US1] Crear `tests/enterprise/orchestration/goal_pursuit/test_decomposer.py` con 4 tests: objetivo complejo produce >= 3 sub-goals con dependencias; objetivo vago retorna error pidiendo clarificacion (EC-01); max_depth respetado (FR-009); sub-goals tienen criterio de completitud explicito (FR-001)
- [ ] T007 [US1] Implementar `src/vigilancia_multiagente/enterprise/orchestration/goal_pursuit/decomposer.py` (~250 LOC): clase `GoalDecomposer` que recibe objetivo en lenguaje natural + contexto (mode, company), invoca LLM con tool calling para producir lista de sub-goals con dependencias explicitas. Respeta `max_depth` configurable. Retorna error si objetivo demasiado vago. Hacer T006 verde (FR-001, FR-009, EC-01)
- [ ] T008 [US1] Crear `tests/enterprise/orchestration/goal_pursuit/test_dependency_resolver.py` con 5 tests: DAG valido secuencia correctamente; identifica pasos paralelizables; detecta ciclo y rechaza con error explicito (FR-008, EC-04); DAG vacio retorna error; profundidad excesiva rechazada (FR-002, FR-008, SC-005)
- [ ] T009 [US1] Implementar `src/vigilancia_multiagente/enterprise/orchestration/goal_pursuit/dependency_resolver.py` (~200 LOC): clase `DependencyResolver` que recibe lista de sub-goals con dependencias, construye DAG, valida ausencia de ciclos con DFS topologico (stdlib, sin deps externas), identifica pasos paralelizables vs secuenciales, retorna plan de ejecucion ordenado. Hacer T008 verde (FR-002, FR-008, SC-005)

**Independent Test Criteria for Phase 2**: `pytest tests/enterprise/orchestration/goal_pursuit/test_decomposer.py tests/enterprise/orchestration/goal_pursuit/test_dependency_resolver.py` verde; ciclos detectados en 100% de casos ciclicos; max_depth respetado.

---

## Phase 3: CheckpointReporter y ApprovalGate

Objetivo: implementar reporte de progreso periodico y gates de aprobacion humana con integracion de capability tokens (FR-003, FR-004, FR-005, FR-011).

- [ ] T010 [US1] Crear `tests/enterprise/orchestration/goal_pursuit/test_checkpoint_reporter.py` con 4 tests: reporte generado cada N pasos con campos requeridos (completados, pendientes, resultado parcial, bloqueos, ETA) (FR-011); reporte al detectar bloqueo; canal no disponible persiste en log y no bloquea ejecucion (EC-05); formato de reporte correcto (FR-003, SC-001)
- [ ] T011 [US1] Implementar `src/vigilancia_multiagente/enterprise/orchestration/goal_pursuit/checkpoint_reporter.py` (~200 LOC): clase `CheckpointReporter` que monitorea progreso, cada N pasos genera reporte con campos FR-011, envia por canal Web/SSE. Si canal no disponible, persiste en log y reintenta en proximo ciclo. Hacer T010 verde (FR-003, FR-011, EC-05)
- [ ] T012 [US1] Crear `tests/enterprise/orchestration/goal_pursuit/test_approval_gate.py` con 3 tests: gate bloquea sin aprobacion humana; gate desbloquea con aprobacion; token expirado durante espera mantiene pausa (FR-004, SC-004)
- [ ] T013 [US1] Implementar `src/vigilancia_multiagente/enterprise/orchestration/goal_pursuit/approval_gate.py` (~150 LOC): clase `ApprovalGate` wrapper sobre `approval_queue.py` de governance adaptado a goal-pursuit. Pausa ejecucion en puntos criticos, presenta contexto al usuario, espera aprobacion explicita. Integra con capability token: si token expira durante espera, mantiene pausa. Hacer T012 verde (FR-004, SC-004)

**Independent Test Criteria for Phase 3**: tests de reporter y gate verdes; reportes contienen todos los campos FR-011; gate bloquea en 100% de casos sin aprobacion.

---

## Phase 4: GoalExecutor, playbook YAML y operaciones admin

Objetivo: implementar el orquestador principal, declarar el playbook YAML y exponer operaciones administrativas (FR-006, FR-007, FR-010).

- [ ] T014 [US1] Crear `tests/enterprise/orchestration/goal_pursuit/test_goal_executor.py` con 6 tests: flujo completo de 5 sub-goals con 2 checkpoints; pause/resume funciona correctamente; cancel marca FAILED en sub-goals activos (EC-03); restart recovery retoma desde ultimo checkpoint (SC-002); token expira y pausa goal (SC-003); sub-goal falla tras 3 reintentos pausa goal completo (EC-02) (FR-006, FR-007, SC-001, SC-002, SC-003)
- [ ] T015 [US1] Implementar `src/vigilancia_multiagente/enterprise/orchestration/goal_pursuit/goal_executor.py` (~350 LOC): clase `GoalExecutor` que coordina decomposer, resolver, reporter y gate. Ejecuta sub-goals segun plan del resolver, persiste estado en `subagents` tras cada paso, soporta pause/resume/cancel, detecta goals ACTIVE tras restart y retoma desde ultimo checkpoint. Hacer T014 verde (FR-006, FR-007, SC-001, SC-002)
- [ ] T016 [P] [US1] Crear `config/playbooks/goal-pursuit.yaml` con: id `goal-pursuit`, mode_compatible (todos los modos), intensity AUTONOMOUS, guardrails (max_depth configurable, checkpoint_every_n_steps configurable, capability_token_ttl_seconds: 28800), flow type dag (FR-010)
- [ ] T017 [US1] Registrar submodulo `goal_pursuit` en `src/vigilancia_multiagente/enterprise/orchestration/__init__.py` con import aditivo (sin tocar imports existentes ni el registro de spec 012)

**Independent Test Criteria for Phase 4**: `pytest tests/enterprise/orchestration/goal_pursuit/test_goal_executor.py` verde; YAML parseable; operaciones pause/resume/cancel funcionales; restart recovery verificado.

---

## Phase 5: Verificacion final

Objetivo: validar SC completos y cero regresiones.

- [ ] T018 [P] Correr `pytest tests/enterprise/orchestration/goal_pursuit/` completo y verificar verde
- [ ] T019 [P] Correr `ruff check src/vigilancia_multiagente/enterprise/orchestration/goal_pursuit/ tests/enterprise/orchestration/goal_pursuit/` sin issues
- [ ] T020 [P] Correr `python -m basedpyright src/vigilancia_multiagente/enterprise/orchestration/goal_pursuit/` sin nuevos errores
- [ ] T021 Verificar SC-002: simular restart tras paso 1, tras checkpoint y tras approval gate; confirmar retoma correcta en 100% de los casos
- [ ] T022 Verificar SC-005: ejecutar 5 DAGs con ciclos y confirmar rechazo en 100% de los casos
- [ ] T023 Verificar SC-003: simular expiracion de token mid-execution y confirmar que cero acciones autonomas se ejecutan tras expiracion

---

## Dependencies

- **Phase 1** must complete before **Phase 2** (schema extendido necesario para persistencia).
- **Phase 2** must complete before **Phase 4** (executor necesita decomposer y resolver).
- **Phase 3** must complete before **Phase 4** (executor necesita reporter y gate).
- **Phase 2** y **Phase 3** son independientes entre si -- pueden ejecutarse en paralelo.
- **Phase 4** must complete before **Phase 5** (verificacion final).
- **Dependencias externas bloqueantes**: spec 009 (PlaybookRunner, tabla subagents con schema base), spec 016 (governance: `approval_queue.py`; tabla `pending_approvals` ya existe en 006).
- T001 bloquea T002 (test necesita migracion).
- T003 es independiente de T001/T002 (modelo en memoria, no requiere DB).
- T006 bloquea T007; T008 bloquea T009 (test-before-implementation).
- T010 bloquea T011; T012 bloquea T013 (test-before-implementation).
- T014 bloquea T015 (test-before-implementation).
- T016 es independiente de T014/T015 (YAML no depende de codigo).

---

## Parallel Execution Examples

### Phase 1 Parallel Block

- Run T003, T005 en paralelo con T001 (archivos distintos sin dependencia).
- T002 espera a T001; T004 espera a T003.

### Phase 2 + Phase 3 Parallel Block

Tras Phase 1 verde, distribuir:

- **Dev A -- Decomposer/Resolver**: T006 -> T007 -> T008 -> T009.
- **Dev B -- Reporter/Gate**: T010 -> T011 -> T012 -> T013.

### Phase 5 Parallel Block

- Run T018, T019, T020 en paralelo (verificaciones independientes).

---

## Implementation Strategy

1. **Gated hasta priorizacion**: este spec es roadmap post-MVP. No se implementa hasta que spec 009 (tabla subagents) y spec 012 (approval gates) esten operativos.
2. **Phase 1 primero**: extension de schema + modelo de token. Esto valida que la migracion es compatible con el schema existente.
3. **Phase 2 y Phase 3 en paralelo**: decomposer/resolver y reporter/gate no tienen dependencia entre si; distribuir entre desarrolladores.
4. **Test-before-implementation estricto**: cada componente tiene tests antes de implementacion (T003->T004, T006->T007, T008->T009, T010->T011, T012->T013, T014->T015).
5. **Phase 4 como integracion**: GoalExecutor integra todos los componentes; solo se implementa tras Phase 2 y Phase 3 verdes.
6. **Phase 5 como gate final**: SC verificados manualmente + linters verdes.
7. **Diferenciacion con spec 012**: este playbook maneja ejecucion autonoma prolongada con DAG; spec 012 maneja flujo Spec-Kit secuencial para apps. No duplicar approval gates (reusar `approval_queue.py` de spec 016 governance).
