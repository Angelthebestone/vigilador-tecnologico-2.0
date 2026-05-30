# Feature Specification: Goal-Pursuit (Ejecucion Autonoma Prolongada con Checkpoints)

**Feature ID**: 013-goal-pursuit
**Created**: 2026-05-29
**Status**: Roadmap (post-MVP, fase F4b segun 00b-mvp-scope-y-cronograma.md)
**Related plan documents**:
- [plan vigilador 3.0/03-playbooks-y-orquestacion.md](../../plan%20vigilador%203.0/03-playbooks-y-orquestacion.md) (seccion "Goal-pursuit")
- [plan vigilador 3.0/00b-mvp-scope-y-cronograma.md](../../plan%20vigilador%203.0/00b-mvp-scope-y-cronograma.md) (tabla "Lo que NO entra en MVP": "Goal-pursuit con horizon de horas/dias")

---

## Problem Statement

Los playbooks reactivos del sistema (general, decision-debate, deep-research) responden a una pregunta puntual y terminan. Sin embargo, muchos objetivos empresariales requieren ejecucion prolongada (horas o dias) con multiples pasos, dependencias entre sub-tareas, checkpoints de progreso y aprobaciones humanas intermedias. Actualmente no existe un mecanismo que descomponga un objetivo complejo en sub-goals, los secuencie segun dependencias, reporte progreso periodicamente y sobreviva reinicios del sistema.

El plan v3.0 (decisiones #100-#101) define el playbook `goal-pursuit` como flujo proactivo que persigue objetivos de larga duracion con capability tokens de TTL limitado y un checkpoint reporter que mantiene al usuario informado.

---

## Scope Boundaries

### In Scope

- Playbook `goal-pursuit` como flujo proactivo (no reactivo) que persigue un objetivo durante horas o dias.
- Componente `GoalDecomposer`: descompone un objetivo complejo en sub-goals con dependencias explicitas (DAG).
- Componente `DependencyResolver`: secuencia y paraleliza pasos segun el DAG de dependencias.
- Componente `CheckpointReporter`: reporta progreso al usuario por canal cada N pasos o al detectar bloqueo.
- Componente `ApprovalGate`: solicita aprobacion humana en puntos criticos (reusa `approval_queue.py` de governance).
- Capability tokens con TTL configurable (default 8 horas); si expira mid-loop, re-solicita aprobacion.
- Persistencia de estado en tabla `subagents` con columnas extendidas (`parent_goal_id`) y columnas ya existentes (`status`, `pause_reason`, `resume_token`, `last_progress_at`). Migración 007 añade además `capability_token JSONB` (almacena goal_id, ttl_seconds, scopes, issued_at, expires_at) y `goal_dag JSONB` (almacena el DAG serializado de sub-goals con dependencias). Sobrevive restart del proceso.
- Operaciones administrativas: pause, resume, cancel de goals en ejecucion.
- Integracion con `ComplexityClassifier` para determinar profundidad de descomposicion.

### Out of Scope

- Flujo Spec-Kit de generacion de aplicaciones internas (cubierto por spec 012 app-development).
- Generacion de dashboards, pipelines o metricas (cubierto por spec 014 artifact-development).
- Implementacion del `SubagentRegistry` base o la tabla `subagents` (pertenecen a spec 009 MVP foundation).
- Implementacion de `approval_queue.py` de governance (pertenece a spec 016-audit-trail-y-rollback, subpaquete governance; la tabla `pending_approvals` ya existe en 006_mvp_foundation.sql).
- Triggers proactivos event-driven (email, webhook, metric anomaly) — son disparadores que PUEDEN invocar goal-pursuit pero no son parte de este spec.
- Loops de autoaprendizaje sobre goals completados — roadmap F5b.
- Anomaly detector sobre progreso de goals — roadmap post-MVP.

---

## Assumptions

- **A-01**: La tabla `subagents` (creada en spec 009, migración 006_mvp_foundation.sql) ya incluye `pause_reason`, `resume_token` y `last_progress_at`; este spec extiende el schema con 3 columnas nuevas: `parent_goal_id UUID REFERENCES subagents(id)`, `capability_token JSONB`, `goal_dag JSONB` (migración 007_goal_pursuit.sql).
- **A-02**: El `PlaybookRunner` y `ComplexityClassifier` estan operativos (dependencia en spec de orquestacion base F4a).
- **A-03**: El modulo `approval_queue.py` de governance (spec 016-audit-trail-y-rollback) esta disponible para gates de aprobacion humana; la tabla `pending_approvals` ya existe en 006_mvp_foundation.sql.
- **A-04**: El canal de comunicacion con el usuario (Web/SSE) esta operativo para recibir reportes de checkpoint.
- **A-05**: El capability token es un mecanismo de autorizacion temporal que limita el alcance de acciones autonomas del agente; su implementacion se basa en TTL + scopes declarados.
- **A-06**: El sistema puede persistir estado suficiente para sobrevivir un restart del proceso y retomar ejecucion desde el ultimo checkpoint completado.

---

## User Scenarios & Testing

### Primary User Story

Como usuario empresarial, quiero asignarle al Vigilador un objetivo complejo que requiere multiples pasos durante varias horas (ej: "consigue 10 leads B2B sector logistica Colombia y agendalos en HubSpot"), para que el sistema lo persiga autonomamente reportandome progreso y pidiendo aprobacion en puntos criticos, sin que yo tenga que supervisar cada paso.

### Acceptance Scenarios

1. **Given** el playbook `goal-pursuit` activo y un objetivo complejo asignado, **When** el `GoalDecomposer` procesa el objetivo, **Then** produce un DAG de sub-goals con dependencias explicitas (al menos 3 sub-goals para un objetivo de complejidad COMPLEJA).

2. **Given** un DAG de sub-goals con dependencias, **When** el `DependencyResolver` evalua el grafo, **Then** identifica correctamente cuales pasos pueden ejecutarse en paralelo y cuales requieren completar prerequisitos.

3. **Given** un goal en ejecucion con `checkpoint_every_n_steps: 3`, **When** se completan 3 pasos, **Then** el `CheckpointReporter` envia un reporte de progreso al usuario por el canal activo con: pasos completados, pasos pendientes, resultado parcial y tiempo estimado restante.

4. **Given** un goal en ejecucion que llega a un punto critico (ej: enviar emails, crear registros en CRM), **When** el `ApprovalGate` se activa, **Then** el sistema pausa la ejecucion, presenta al usuario el contexto de la accion pendiente y espera aprobacion explicita antes de continuar.

5. **Given** un capability token con TTL de 8 horas emitido al inicio del goal, **When** el TTL expira durante la ejecucion, **Then** el sistema pausa el goal, notifica al usuario que el token expiro y solicita re-autorizacion para continuar.

6. **Given** un goal pausado (por expiracion de token o por solicitud del admin), **When** el admin ejecuta la operacion `resume`, **Then** el sistema retoma la ejecucion desde el ultimo sub-goal completado sin repetir trabajo previo.

7. **Given** el proceso del Vigilador reiniciado mientras un goal estaba en ejecucion, **When** el sistema arranca nuevamente, **Then** detecta goals con status ACTIVE en la tabla `subagents`, verifica el ultimo checkpoint y retoma la ejecucion desde ese punto.

### Edge Cases

- **EC-01**: El `GoalDecomposer` no puede descomponer el objetivo (demasiado vago) — reporta al usuario pidiendo clarificacion en lugar de intentar ejecutar un plan incompleto.
- **EC-02**: Un sub-goal falla tras 3 reintentos — el sistema marca ese sub-goal como FAILED, pausa el goal completo y reporta al usuario con contexto del fallo para decision (reintentar, omitir, cancelar).
- **EC-03**: El usuario cancela un goal mid-execution — el sistema marca status FAILED en todos los sub-goals activos, persiste el estado parcial y reporta lo completado hasta ese punto.
- **EC-04**: Dependencia circular detectada en el DAG — el `DependencyResolver` rechaza el plan con error explicito y solicita re-descomposicion al `GoalDecomposer`.
- **EC-05**: El canal de comunicacion con el usuario no esta disponible para el checkpoint — el sistema persiste el reporte en log y reintenta en el proximo ciclo; no bloquea la ejecucion del goal.

---

## Functional Requirements

- **FR-001**: El sistema MUST proveer un componente `GoalDecomposer` que reciba un objetivo en lenguaje natural y produzca un DAG de sub-goals con dependencias explicitas entre ellos.
  - *Fuente*: 03-playbooks-y-orquestacion.md, seccion "Goal-pursuit", tabla de componentes, fila `decomposer.py`.

- **FR-002**: El sistema MUST proveer un componente `DependencyResolver` que reciba el DAG de sub-goals y determine el orden de ejecucion, identificando pasos paralelizables y secuenciales.
  - *Fuente*: 03-playbooks-y-orquestacion.md, seccion "Goal-pursuit", tabla de componentes, fila `dependency_resolver.py`.

- **FR-003**: El sistema MUST proveer un componente `CheckpointReporter` que reporte progreso al usuario cada N pasos completados (N configurable por goal) o al detectar un bloqueo.
  - *Fuente*: 03-playbooks-y-orquestacion.md, seccion "Goal-pursuit", tabla de componentes, fila `checkpoint_reporter.py`.

- **FR-004**: El sistema MUST proveer un componente `ApprovalGate` que pause la ejecucion en puntos criticos y espere aprobacion humana explicita antes de continuar, reusando `approval_queue.py` de governance.
  - *Fuente*: 03-playbooks-y-orquestacion.md, seccion "Goal-pursuit", tabla de componentes, fila `approval_gate.py`.

- **FR-005**: El sistema MUST emitir un capability token con TTL configurable (default 8 horas) al inicio de cada goal; si el TTL expira durante ejecucion, el goal se pausa y se re-solicita autorizacion.
  - *Fuente*: 03-playbooks-y-orquestacion.md, seccion "Goal-pursuit", parrafo "Ejecucion autonoma extendida".

- **FR-006**: El sistema MUST persistir el estado de cada goal y sus sub-goals en la tabla `subagents` con campos suficientes para sobrevivir un restart del proceso y retomar desde el ultimo checkpoint. Campos clave: `parent_goal_id` (jerarquía goal→sub-goal), `capability_token JSONB` (token activo con TTL/scopes para re-validar tras restart), `goal_dag JSONB` (DAG serializado con estado de cada nodo), `last_progress_at` (timestamp del último checkpoint), `resume_token` (punto de reanudación).
  - *Fuente*: 03-playbooks-y-orquestacion.md, seccion "Goal-pursuit", parrafo "Persistencia".

- **FR-007**: El sistema MUST soportar operaciones administrativas sobre goals: pause (ACTIVE -> PAUSED), resume (PAUSED/WAITING_APPROVAL -> ACTIVE), cancel (ACTIVE -> FAILED).
  - *Fuente*: 03-playbooks-y-orquestacion.md, seccion "SubagentRegistry", operaciones CLI.

- **FR-008**: El sistema MUST validar que el DAG de sub-goals no contenga ciclos; si detecta dependencia circular, MUST rechazar el plan con error explicito.
  - *Fuente*: derivado de constitucion v1.2.0 principio #4 (manejo de errores estricto) aplicado al DependencyResolver.

- **FR-009**: El sistema MUST respetar el `max_depth` configurable del playbook para sub-goals anidados; si un sub-goal intenta spawnear por encima del limite, MUST fallar con error explicito.
  - *Fuente*: 03-playbooks-y-orquestacion.md, seccion "SubagentRegistry", guardrails depth-aware.

- **FR-010**: El sistema MUST declarar `mode_compatible: todos los modos` con `intensity: AUTONOMOUS` recomendado para el playbook goal-pursuit.
  - *Fuente*: 03-playbooks-y-orquestacion.md, tabla "Catalogo de playbooks", fila goal-pursuit.

- **FR-011**: El `CheckpointReporter` MUST incluir en cada reporte: pasos completados, pasos pendientes, resultado parcial acumulado, bloqueos detectados y tiempo estimado restante.
  - *Fuente*: 03-playbooks-y-orquestacion.md, seccion "Goal-pursuit", ejemplo de ejecucion.

---

## Key Entities

- **Goal**: objetivo de alto nivel asignado por el usuario, con TTL de capability token, modo activo y canal de reporte. Persiste como registro padre en `subagents`.
- **Sub-goal**: paso atomico dentro del DAG de un goal. Atributos: id, parent_goal_id, dependencias, status (ACTIVE/PAUSED/COMPLETED/FAILED/WAITING_APPROVAL), resultado parcial.
- **Capability token**: autorizacion temporal con TTL que limita el alcance de acciones autonomas. Atributos: goal_id, ttl_seconds, scopes, issued_at, expires_at.
- **Checkpoint report**: mensaje de progreso enviado al usuario. Atributos: goal_id, step_number, completed_steps, pending_steps, partial_result, blockers, eta.
- **DAG de dependencias**: grafo dirigido aciclico que representa el orden de ejecucion de sub-goals.

---

## Success Criteria

- **SC-001**: Un goal de 5 sub-goals con 2 checkpoints se ejecuta completamente en menos de 8 horas, reportando progreso en cada checkpoint configurado.
- **SC-002**: El sistema retoma correctamente un goal tras restart del proceso en el 100% de los casos de test (3 escenarios: restart tras paso 1, tras checkpoint, tras approval gate).
- **SC-003**: La expiracion de capability token pausa efectivamente el goal en el 100% de los casos; cero acciones autonomas se ejecutan tras expiracion del token.
- **SC-004**: El `ApprovalGate` bloquea acciones criticas en el 100% de los casos de test; sin aprobacion humana, la accion no se ejecuta.
- **SC-005**: El `DependencyResolver` detecta ciclos en el DAG y rechaza el plan en el 100% de los casos de test con grafos ciclicos.

---

## Delivery Constraints

- Constitucion v1.2.0 — Simplicidad obligatoria (#2): los 4 componentes (decomposer, dependency_resolver, checkpoint_reporter, approval_gate) tienen responsabilidad unica; no se fusionan.
- Constitucion v1.2.0 — Modularidad primero (#3): cada componente vive en su propio archivo bajo `enterprise/orchestration/goal_pursuit/`.
- Constitucion v1.2.0 — Manejo de errores estricto (#4): fallos en sub-goals se propagan con contexto; no se silencian ni se reintentan indefinidamente.
- Constitucion v1.2.0 — Entrega verificable (#6): cada sub-goal tiene criterio de completitud explicito definido por el `GoalDecomposer`.
- SoC: el checkpoint reporter solo reporta; el approval gate solo bloquea; el decomposer solo descompone; el resolver solo secuencia.

---

## Dependencies

- Tabla `subagents` con schema base (spec 009 MVP foundation).
- `PlaybookRunner` y `ComplexityClassifier` operativos (spec de orquestacion base F4a).
- Modulo `approval_queue.py` de governance (spec 016-audit-trail-y-rollback; tabla `pending_approvals` ya en 006).
- Canal de comunicacion Web/SSE operativo para reportes de checkpoint.
- `ToolRegistry` para discovery de tools necesarias en cada sub-goal.
