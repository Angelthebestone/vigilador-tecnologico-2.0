# Implementation Plan: Goal-Pursuit (Ejecucion Autonoma Prolongada con Checkpoints)

**Feature ID**: 013-goal-pursuit
**Created**: 2026-05-29
**Spec**: [spec.md](spec.md)

## Problem

Los playbooks reactivos del sistema responden a una pregunta puntual y terminan. Muchos objetivos empresariales requieren ejecucion prolongada (horas o dias) con multiples pasos, dependencias entre sub-tareas, checkpoints de progreso y aprobaciones humanas intermedias. No existe un mecanismo que descomponga un objetivo complejo en sub-goals, los secuencie segun dependencias (DAG), reporte progreso periodicamente, sobreviva reinicios del sistema y opere con autorizacion temporal limitada (capability tokens con TTL).

## Approach

Este plan es **roadmap post-MVP**. Describe COMO se construiria el playbook `goal-pursuit` al priorizarse, con dependencias en specs 009 (MVP foundation: PlaybookRunner, SubagentRegistry, tabla subagents) y 012 (playbook app-development, que comparte infraestructura de approval gates). La implementacion se estructura en 4 fases: (1) extension del schema de `subagents` para goal-pursuit, (2) componentes core (GoalDecomposer, DependencyResolver), (3) componentes de control (CheckpointReporter, ApprovalGate, capability tokens), (4) playbook YAML, operaciones administrativas y tests e2e. Cada componente vive en su propio archivo bajo `enterprise/orchestration/goal_pursuit/` con responsabilidad unica.

---

## Technical Context

| Area | Decision |
|------|----------|
| Ubicacion modulo | `src/vigilancia_multiagente/enterprise/orchestration/goal_pursuit/` |
| Ubicacion playbook YAML | `config/playbooks/goal-pursuit.yaml` |
| Persistencia | Tabla `subagents` (spec 009) extendida con columnas goal-pursuit |
| Approval gates | Reusa `approval_queue.py` de governance (no reimplementa) |
| Canal de reportes | Web/SSE existente para checkpoint reports |
| Migrations | `src/vigilancia_multiagente/infra/db/migrations/007_goal_pursuit.sql` aplicada por MigrationRunner (forward-only, idempotente) |
| Capability tokens | Implementacion propia con TTL + scopes, persistida en columna `capability_token JSONB` de `subagents` |
| DAG validation | Deteccion de ciclos con DFS topologico (stdlib, sin deps externas) |
| LLM para descomposicion | Adapter activo segun `llm.default` con tool calling |

## External Constraints

| Constraint | Impact |
|------------|--------|
| Dependencia en tabla `subagents` (spec 009) | Schema base debe existir; este spec extiende con columnas adicionales |
| Dependencia en PlaybookRunner (spec 009 F4a) | Runner debe soportar playbooks proactivos (no solo reactivos) |
| Dependencia en `approval_queue.py` (spec 016 governance) | Gates de aprobacion humana reusan modulo existente; tabla `pending_approvals` ya en 006 |
| Dependencia en canal Web/SSE | Checkpoint reports requieren canal operativo |
| Constitucion v1.2.0 #4 Manejo errores estricto | Fallos en sub-goals se propagan con contexto; no se silencian |
| Constitucion v1.2.0 #3 Modularidad | 4 componentes separados, un archivo por componente |
| Archivos <= 400 LOC | Cada componente en su propio archivo |
| Sobrevivir restart | Estado completo persistido; retoma desde ultimo checkpoint |

---

## Files to Create / Modify

### New Files

| File | Purpose |
|------|---------|
| `config/playbooks/goal-pursuit.yaml` | Declaracion del playbook: modo proactivo, guardrails, checkpoint config |
| `src/vigilancia_multiagente/enterprise/orchestration/goal_pursuit/__init__.py` | Marker del subpaquete |
| `src/vigilancia_multiagente/enterprise/orchestration/goal_pursuit/decomposer.py` | GoalDecomposer: descompone objetivo en DAG de sub-goals (~250 LOC) |
| `src/vigilancia_multiagente/enterprise/orchestration/goal_pursuit/dependency_resolver.py` | DependencyResolver: secuencia/paraleliza segun DAG, detecta ciclos (~200 LOC) |
| `src/vigilancia_multiagente/enterprise/orchestration/goal_pursuit/checkpoint_reporter.py` | CheckpointReporter: reporta progreso cada N pasos o al detectar bloqueo (~200 LOC) |
| `src/vigilancia_multiagente/enterprise/orchestration/goal_pursuit/approval_gate.py` | ApprovalGate: pausa en puntos criticos, reusa approval_queue (~150 LOC) |
| `src/vigilancia_multiagente/enterprise/orchestration/goal_pursuit/capability_token.py` | Modelo y logica de capability tokens con TTL + scopes (~150 LOC) |
| `src/vigilancia_multiagente/enterprise/orchestration/goal_pursuit/goal_executor.py` | Ejecutor principal: orquesta sub-goals, maneja pause/resume/cancel (~350 LOC) |
| `src/vigilancia_multiagente/infra/db/migrations/007_goal_pursuit.sql` | Migración SQL cruda: `ALTER TABLE subagents ADD COLUMN IF NOT EXISTS parent_goal_id UUID REFERENCES subagents(id)`, `capability_token JSONB`, `goal_dag JSONB` + índice. Aplicada por MigrationRunner. |
| `tests/enterprise/orchestration/goal_pursuit/test_decomposer.py` | Tests de descomposicion: objetivo complejo, objetivo vago, profundidad |
| `tests/enterprise/orchestration/goal_pursuit/test_dependency_resolver.py` | Tests de DAG: secuenciacion, paralelismo, deteccion ciclos |
| `tests/enterprise/orchestration/goal_pursuit/test_checkpoint_reporter.py` | Tests de reportes: cada N pasos, bloqueo, canal no disponible |
| `tests/enterprise/orchestration/goal_pursuit/test_capability_token.py` | Tests de tokens: emision, expiracion, re-autorizacion |
| `tests/enterprise/orchestration/goal_pursuit/test_goal_executor.py` | Tests e2e: flujo completo, pause/resume, restart recovery |

### Modified Files

| File | Changes |
|------|---------|
| `src/vigilancia_multiagente/enterprise/orchestration/__init__.py` | Registrar submodulo `goal_pursuit` (import aditivo) |

---

## Constitution Check (Pre-Design)

- **Gate result**: PASS
- **Alignment**:
  - Pensar Antes de Codificar: dependencias explicitas en specs 009/012; assumptions del spec (A-01..A-06) validadas; extension de schema documentada antes de implementar.
  - Simplicidad Obligatoria: 4 componentes core + 1 ejecutor + 1 modelo de token; cero abstracciones adicionales; DAG validation con DFS de stdlib sin deps externas.
  - Modularidad Primero: un archivo por componente con responsabilidad unica; decomposer solo descompone, resolver solo secuencia, reporter solo reporta, gate solo bloquea.
  - Cambios Quirurgicos y Trazables: cero modificaciones al 2.0; extension de schema via migración SQL cruda (`007_goal_pursuit.sql`) aplicada por MigrationRunner; cada FR traza a 03-playbooks-y-orquestacion.md.
  - Entrega Verificable: cada componente tiene tests dedicados; SC del spec medibles con escenarios automatizados.
- **Diseno de Software**: SRP (un componente = una responsabilidad), SoC (decomposer/resolver/reporter/gate separados), DIP (goal_executor depende de abstracciones no de implementaciones concretas), CQS (reporter solo lee y reporta, gate solo bloquea, executor muta estado), KISS (DAG con DFS topologico sin framework externo), DRY (reusa approval_queue existente en vez de reimplementar).

---

## Phases

### Phase 1 — Extension de schema y modelo de datos (1-2 dias)

1. Crear migración SQL cruda `src/vigilancia_multiagente/infra/db/migrations/007_goal_pursuit.sql` que extienda tabla `subagents` con columnas: `parent_goal_id UUID REFERENCES subagents(id)`, `capability_token JSONB` (almacena goal_id, ttl_seconds, scopes, issued_at, expires_at), `goal_dag JSONB` (DAG serializado con estado de cada nodo). Índice en `parent_goal_id`. DDL idempotente con `IF NOT EXISTS` / `ADD COLUMN IF NOT EXISTS`. Nota: `pause_reason`, `resume_token` y `last_progress_at` ya existen en 006_mvp_foundation.sql.
2. Crear `capability_token.py` con modelo `CapabilityToken(goal_id, ttl_seconds, scopes, issued_at, expires_at)` y metodos `is_expired()`, `remaining_seconds()`, `reissue(new_ttl)`.
3. Verificar idempotencia de la migración (aplicar 007 dos veces sin error) y aislamiento de tablas del 2.0.
4. Verificar que tablas del 2.0 y spec 009 no se afectan.

**Output**: schema extendido + modelo de token + migración idempotente verificada.

### Phase 2 — GoalDecomposer y DependencyResolver (3-4 dias)

1. Implementar `decomposer.py`: recibe objetivo en lenguaje natural + contexto (mode, company), invoca LLM con tool calling para producir lista de sub-goals con dependencias explicitas. Respeta `max_depth` configurable. Si el objetivo es demasiado vago, retorna error pidiendo clarificacion (EC-01).
2. Implementar `dependency_resolver.py`: recibe lista de sub-goals con dependencias, construye DAG, valida ausencia de ciclos con DFS topologico (FR-008), identifica pasos paralelizables vs secuenciales, retorna plan de ejecucion ordenado.
3. Tests: descomposicion de objetivo complejo (>= 3 sub-goals), objetivo vago (error), DAG con ciclo (rechazo), DAG valido con paralelismo.

**Output**: GoalDecomposer + DependencyResolver funcionales con tests verdes.

### Phase 3 — CheckpointReporter, ApprovalGate y capability tokens (2-3 dias)

1. Implementar `checkpoint_reporter.py`: monitorea progreso del goal, cada N pasos completados (N configurable por goal) genera reporte con: pasos completados, pasos pendientes, resultado parcial, bloqueos, ETA. Envia por canal Web/SSE. Si canal no disponible, persiste en log y reintenta (EC-05).
2. Implementar `approval_gate.py`: wrapper sobre `approval_queue.py` de governance adaptado a goal-pursuit. Pausa ejecucion en puntos criticos, presenta contexto al usuario, espera aprobacion explicita. Integra con capability token: si token expira durante espera, mantiene pausa.
3. Integrar capability tokens con goal_executor: emision al inicio del goal, verificacion antes de cada sub-goal, pausa automatica al expirar, re-solicitud de autorizacion.
4. Tests: reporte cada N pasos, bloqueo por approval, expiracion de token pausa goal, re-autorizacion reanuda.

**Output**: CheckpointReporter + ApprovalGate + tokens integrados con tests verdes.

### Phase 4 — GoalExecutor, playbook YAML y operaciones admin (3-4 dias)

1. Implementar `goal_executor.py`: orquestador principal que coordina decomposer, resolver, reporter y gate. Ejecuta sub-goals segun plan del resolver, persiste estado en `subagents` tras cada paso, soporta pause/resume/cancel, detecta goals ACTIVE tras restart y retoma desde ultimo checkpoint.
2. Crear `config/playbooks/goal-pursuit.yaml` con: mode_compatible (todos), intensity AUTONOMOUS, guardrails (max_depth, checkpoint_every_n_steps, capability_token_ttl_seconds: 28800), flow type dag.
3. Implementar operaciones administrativas: pause (ACTIVE -> PAUSED), resume (PAUSED/WAITING_APPROVAL -> ACTIVE), cancel (ACTIVE -> FAILED). Exponer via CLI `vigilador-admin subagent {pause,resume,cancel}`.
4. Test e2e: goal de 5 sub-goals con 2 checkpoints ejecuta completamente; restart mid-execution retoma correctamente; cancel marca FAILED en sub-goals activos; token expira y pausa.

**Output**: flujo goal-pursuit completo operativo con persistencia, recovery y operaciones admin verificadas.

---

## Rollout Strategy

**Tipo**: roadmap post-MVP. Este plan describe COMO se construiria al priorizarse tras completar specs 009 (MVP foundation) y 012 (app-development, que comparte infraestructura de approval gates).

- **Prerequisitos**: PlaybookRunner operativo con soporte para playbooks proactivos, tabla `subagents` con schema base, `approval_queue.py` de governance disponible, canal Web/SSE operativo.
- **Backward compatibility**: cero impacto en el 2.0. Extension de schema via migración SQL cruda aditiva (columnas nuevas nullable, DDL idempotente). Playbook es aditivo al catalogo.
- **Activacion**: disponible para todos los modos una vez desplegado; intensity AUTONOMOUS recomendada pero no obligatoria.
- **Coexistencia**: goals en ejecucion no interfieren con playbooks reactivos; operan en sesiones independientes con su propio budget de LLM calls.

---

## Success Criteria

- **SC-001**: Un goal de 5 sub-goals con 2 checkpoints se ejecuta completamente en menos de 8 horas, reportando progreso en cada checkpoint (traza a spec SC-001).
- **SC-002**: El sistema retoma correctamente un goal tras restart en 100% de los casos de test: restart tras paso 1, tras checkpoint, tras approval gate (traza a spec SC-002).
- **SC-003**: Expiracion de capability token pausa el goal en 100% de los casos; cero acciones autonomas tras expiracion (traza a spec SC-003).
- **SC-004**: ApprovalGate bloquea acciones criticas en 100% de los casos; sin aprobacion humana la accion no se ejecuta (traza a spec SC-004).
- **SC-005**: DependencyResolver detecta ciclos en el DAG y rechaza el plan en 100% de los casos con grafos ciclicos (traza a spec SC-005).

## Constitution Check (Post-Design)

- **Status**: PASS
- **Justification**: El plan respeta todos los principios de la constitucion v1.2.0. Simplicidad: 4 componentes core + 1 ejecutor, sin abstracciones adicionales; DAG con DFS stdlib. Modularidad: un archivo por componente (SRP), cada uno con responsabilidad unica (SoC): decomposer descompone, resolver secuencia, reporter reporta, gate bloquea. Cambios quirurgicos: cero modificaciones al 2.0; extension de schema via migración SQL cruda (`007_goal_pursuit.sql`) aplicada por MigrationRunner (forward-only, idempotente con `IF NOT EXISTS`); solo archivos nuevos bajo `enterprise/orchestration/goal_pursuit/`. Entrega verificable: 5 SC medibles con tests automatizados por componente y e2e. Manejo de errores estricto: fallos en sub-goals se propagan con contexto (EC-02), ciclos se rechazan explicitamente (FR-008), objetivo vago pide clarificacion (EC-01). DRY: reusa approval_queue existente. Archivos <= 400 LOC cada uno.
