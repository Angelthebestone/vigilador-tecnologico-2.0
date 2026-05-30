# Tasks: Artifact-Development (Dashboards, Pipelines y Metricas Auto-generadas)

**Input**: `specs/014-artifact-development/spec.md`, `specs/014-artifact-development/plan.md`
**Feature**: Playbook `artifact-development` con flujo de 6 fases orientado a datos y metricas (source_inventory, metric_model, pipeline_plan, build, verify, publish) para generar dashboards, pipelines, notebooks, reportes y graficas sin pasar por el flujo Spec-Kit completo.

**Status**: Roadmap post-MVP. Tareas gated hasta priorizacion. Dependencias bloqueantes: spec 009 (PlaybookRunner), spec 010 (indice empresarial TurboVecIndex para inventario de fuentes), spec 011 (skills file_system, template_render), spec 012 (infraestructura sandbox compartida).

**User Stories del spec**:
- **US1 (P1)**: Usuario empresarial en modo CEO pide un dashboard de KPIs a partir de sus datos; el sistema inventaria fuentes, modela metricas, construye el artefacto y lo publica sin configuracion manual de herramientas BI.

**Testing strategy**: test-before-implementation por componente. Cada agente tiene tests dedicados antes de su implementacion. Test e2e valida flujo completo y diferenciacion con app-development. **Excepción documentada**: T008 (PipelinePlanner), T011 (Verifier), T012 (Publisher) y T013 (ArtifactRegistry) son helpers simples con responsabilidad única y baja complejidad ciclomática; se validan indirectamente via el test e2e del coordinator (T015). Si se requiere cobertura unitaria adicional, se añade post-implementación.

---

## Phase 1: Playbook YAML y estructura del modulo

Objetivo: declarar el playbook en YAML y crear la estructura de modulo bajo `enterprise/artifacts/` (FR-001, FR-008).

- [ ] T001 [P] Crear `config/playbooks/artifact-development.yaml` con estructura completa: id `artifact-development`, display_name, mode_compatible [CEO, CFO, Operaciones PYME, Marketing], flow sequential con fases_order [source_inventory, metric_model, pipeline_plan, build, verify, publish], agents (source_inventory_agent, metric_model_agent, builder_agent con roles/skills_allowed), output_schema (artifact_type, artifact_path, data_sources, refresh_policy, metrics), guardrails (sandbox_required: true) (FR-001, FR-008)
- [ ] T002 [P] Crear `src/vigilancia_multiagente/enterprise/artifacts/__init__.py` como marker del subpaquete
- [ ] T003 Registrar submodulo `artifacts` en `src/vigilancia_multiagente/enterprise/__init__.py` con import aditivo (sin tocar imports existentes)

**Independent Test Criteria for Phase 1**: YAML parseable sin errores; estructura de modulo importable; fases_order no contiene fases de spec 012 (constitution/specify/plan/tasks/analyze/implement); mode_compatible incluye CEO, CFO, Operaciones PYME, Marketing.

---

## Phase 2: Source Inventory Agent

Objetivo: implementar inventario automatico de fuentes de datos disponibles (FR-002).

- [ ] T004 [US1] Crear `tests/enterprise/artifacts/test_source_inventory_agent.py` con 4 tests: inventario con 3 fuentes disponibles retorna nombre/tipo/ubicacion/disponibilidad; fuente eliminada marcada como no disponible con sugerencia de alternativas (EC-01); cero fuentes encontradas reporta al usuario sugiriendo indexar datos (scenario 6); fuentes del indice empresarial descubiertas correctamente (FR-002, SC-002)
- [ ] T005 [US1] Implementar `src/vigilancia_multiagente/enterprise/artifacts/source_inventory_agent.py` (~250 LOC): clase `SourceInventoryAgent` que consulta indice empresarial (TurboVecIndex) para fuentes indexadas, escanea archivos locales declarados por el usuario, verifica disponibilidad de cada fuente (archivo existe, API responde, DB accesible), genera inventario con nombre, tipo (CSV, API, DB, documento indexado), ubicacion, disponibilidad. Hacer T004 verde (FR-002, EC-01, SC-002)

**Independent Test Criteria for Phase 2**: tests de inventario verdes; fuentes disponibles identificadas correctamente; edge cases manejados sin silenciar errores.

---

## Phase 3: Metric Model Agent, Pipeline Planner y Builder Agent

Objetivo: implementar modelado de KPIs, planificacion de pipeline y construccion de artefactos en sandbox (FR-003, FR-004, FR-005, FR-007, FR-009).

- [ ] T006 [US1] Crear `tests/enterprise/artifacts/test_metric_model_agent.py` con 4 tests: KPIs generados con nombre/formula/fuente/granularidad/formato; brecha de datos detectada y reportada (EC-02); solicitud sin metricas claras pide clarificacion; refresh_policy declarada por artefacto (FR-003, FR-007)
- [ ] T007 [US1] Implementar `src/vigilancia_multiagente/enterprise/artifacts/metric_model_agent.py` (~200 LOC): clase `MetricModelAgent` que recibe inventario de fuentes + solicitud del usuario, define KPIs con nombre, formula, fuente de datos, granularidad temporal, formato de visualizacion recomendado. Detecta brechas (datos requeridos no disponibles). Hacer T006 verde (FR-003, FR-007, EC-02)
- [ ] T008 [P] [US1] Implementar `src/vigilancia_multiagente/enterprise/artifacts/pipeline_planner.py` (~150 LOC): clase `PipelinePlanner` — helper interno del `ArtifactCoordinator` (NO agente autónomo; KISS) — que genera plan tecnico de flujo de datos desde fuentes hasta visualizacion final, incluyendo transformaciones necesarias y refresh_policy
- [ ] T009 [US1] Crear `tests/enterprise/artifacts/test_builder_agent.py` con 4 tests: dashboard construido en sandbox correctamente; pipeline generado; tipo no soportado informa tipos disponibles (EC-04); error de construccion reintenta max 2 veces (EC-03) (FR-004, FR-005, FR-009, SC-003)
- [ ] T010 [US1] Implementar `src/vigilancia_multiagente/enterprise/artifacts/builder_agent.py` (~300 LOC): clase `BuilderAgent` que construye artefacto en sandbox segun tipo solicitado (dashboard HTML/Streamlit/React, pipeline local, notebook, reporte, grafica). Usa skills `analytics:dashboard_generate` y `code:e2b_sandbox`. Max 2 reintentos en error. Hacer T009 verde (FR-004, FR-005, FR-009, EC-03, EC-04)

**Independent Test Criteria for Phase 3**: tests de metric_model y builder verdes; KPIs con campos completos; artefactos construidos en sandbox; tipos no soportados manejados con error informativo.

---

## Phase 4: Verificacion, publicacion, registro y coordinador

Objetivo: implementar verificacion funcional, publicacion al destino, registro de metadatos y coordinador secuencial (FR-006, FR-009, FR-010, SC-004).

- [ ] T011 [US1] Implementar `src/vigilancia_multiagente/enterprise/artifacts/verifier.py` (~150 LOC): clase `Verifier` que valida artefacto funcional en sandbox (dashboard renderiza sin errores, pipeline procesa datos, notebook ejecuta sin excepciones). Reporta resultado de verificacion (FR-009, SC-003)
- [ ] T012 [US1] Implementar `src/vigilancia_multiagente/enterprise/artifacts/publisher.py` (~200 LOC): clase `Publisher` que copia artefacto verificado al directorio destino via skill `code:file_system`. Solo publica tras verificacion exitosa. Registra en artifact_registry (FR-009)
- [ ] T013 [US1] Implementar `src/vigilancia_multiagente/enterprise/artifacts/artifact_registry.py` (~150 LOC): clase `ArtifactRegistry` que registra cada artefacto publicado con metadatos completos: artifact_type, artifact_path, data_sources, refresh_policy, metrics, created_at. Persiste en JSONL como almacenamiento DEFAULT (sin migración SQL); persistencia en tabla SQL queda como extensión futura explícita (FR-006, SC-004)
- [ ] T014 [US1] Implementar `src/vigilancia_multiagente/enterprise/artifacts/artifact_coordinator.py` (~250 LOC): clase `ArtifactCoordinator` que orquesta las 6 fases secuencialmente, pasa contexto entre fases (inventario -> modelo -> plan -> build -> verify -> publish) (FR-001)
- [ ] T015 [US1] Crear `tests/enterprise/artifacts/test_artifact_coordinator.py` con 4 tests: flujo completo de 6 fases con 2 fuentes y 3 KPIs produce artefacto funcional; metadatos completos registrados (SC-004); diferenciacion con app-development -- solicitud de "dashboard de ventas" va a artifact-development (FR-010, SC-005); solicitud de "herramienta interna" NO activa este playbook (SC-001, SC-005)
- [ ] T016 [US1] Hacer T015 verde: integrar coordinator con todos los agentes y verificar flujo e2e

**Independent Test Criteria for Phase 4**: test e2e verde; metadatos completos en registry; artefacto funcional verificado en sandbox; publicacion solo tras verificacion exitosa; diferenciacion con app-development correcta.

---

## Phase 5: Verificacion final

Objetivo: validar SC completos y cero regresiones.

- [ ] T017 [P] Correr `pytest tests/enterprise/artifacts/` completo y verificar verde
- [ ] T018 [P] Correr `ruff check src/vigilancia_multiagente/enterprise/artifacts/ tests/enterprise/artifacts/` sin issues
- [ ] T019 [P] Correr `python -m basedpyright src/vigilancia_multiagente/enterprise/artifacts/` sin nuevos errores
- [ ] T020 Verificar SC-001: ejecutar solicitud de dashboard con 1-3 fuentes y 3-5 KPIs; confirmar generacion completa en menos de 30 minutos
- [ ] T021 Verificar SC-005: ejecutar 10 mensajes de ejemplo y confirmar diferenciacion artifact-development vs app-development en al menos 90% de los casos
- [ ] T022 Verificar SC-004: confirmar que 100% de artefactos publicados tienen metadatos completos (artifact_type, artifact_path, data_sources, refresh_policy, metrics)

---

## Dependencies

- **Phase 1** must complete before **Phase 2**, **Phase 3** y **Phase 4** (YAML y estructura necesarios).
- **Phase 2** must complete before **Phase 3** (metric_model necesita inventario de fuentes como input).
- **Phase 3** must complete before **Phase 4** (coordinator necesita todos los agentes).
- **Phase 4** must complete before **Phase 5** (verificacion final).
- **Dependencias externas bloqueantes**: spec 009 (PlaybookRunner), spec 010 (TurboVecIndex para inventario), spec 011 (skills file_system, analytics), spec 012 (infraestructura sandbox).
- T004 bloquea T005; T006 bloquea T007; T009 bloquea T010 (test-before-implementation).
- T008 es independiente de T006/T007 (archivo distinto, sin dependencia directa).
- T011, T012, T013 son secuenciales (publisher depende de verifier; registry es usado por publisher).
- T014 depende de T011, T012, T013 (coordinator integra todos).
- T015 bloquea T016 (test-before-implementation del e2e).

---

## Parallel Execution Examples

### Phase 1 Parallel Block

- Run T001, T002 en paralelo (archivos distintos).
- T003 espera a T002 (necesita __init__.py creado).

### Phase 3 Parallel Block

- Run T006 y T009 en paralelo (tests de componentes distintos).
- T008 puede ejecutarse en paralelo con T006 y T009 (archivo independiente).

### Phase 5 Parallel Block

- Run T017, T018, T019 en paralelo (verificaciones independientes).

---

## Implementation Strategy

1. **Gated hasta priorizacion**: este spec es roadmap post-MVP. No se implementa hasta que specs 009, 010, 011 y 012 esten operativos.
2. **Phase 1 primero**: declarar YAML + estructura. Valida que PlaybookRunner puede cargar el playbook y que las fases son distintas de spec 012.
3. **Flujo secuencial Phase 2 -> Phase 3 -> Phase 4**: el inventario alimenta el modelado, que alimenta la construccion, que alimenta la publicacion. No hay paralelismo entre fases funcionales.
4. **Test-before-implementation**: T004->T005, T006->T007, T009->T010, T015->T016.
5. **Phase 5 como gate final**: SC verificados + linters verdes.
6. **Diferenciacion explicita con spec 012**: este playbook usa flujo propio de 6 fases orientado a datos (source_inventory, metric_model, pipeline_plan, build, verify, publish). NO replica el flujo Spec-Kit (constitution/specify/plan/tasks/analyze/implement/test) de spec 012. El routing entre ambos se basa en la naturaleza de la solicitud: metricas/visualizacion -> artifact-development; producto interno completo -> app-development.
7. **No duplicar con spec 013**: este playbook es secuencial simple (6 fases lineales); spec 013 maneja DAG de sub-goals con ejecucion prolongada. Si un artefacto requiere ejecucion de horas, se delega a goal-pursuit.
