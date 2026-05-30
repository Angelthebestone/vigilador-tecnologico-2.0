# Tasks: Playbook App-Development (Spec-Kit Pipeline Interno)

**Input**: `specs/012-playbook-app-development-spec-kit/spec.md`, `specs/012-playbook-app-development-spec-kit/plan.md`
**Feature**: Playbook `app-development` que adopta el flujo Spec-Kit (constitution, specify, plan, tasks, analyze, implement, test) como pipeline interno reutilizable con gates de aprobacion humana, ejecucion en sandbox y routing por complejidad.

**Status**: Roadmap post-MVP. Tareas gated hasta priorizacion. Dependencias bloqueantes: spec 009 (PlaybookRunner, SubagentRegistry, tabla subagents), spec 010 (ingestion/indice empresarial), spec 011 (skills file_system, template_render).

**User Stories del spec**:
- **US1 (P1)**: Operador en modo Operaciones PYME genera herramienta interna describiendo lo que necesita en lenguaje natural; el sistema produce codigo funcional y verificado sin que el usuario programe.

**Testing strategy**: test-before-implementation por componente. Cada agente tiene tests unitarios dedicados antes de su implementacion. Tests e2e validan el flujo completo.

---

## Phase 1: Declaracion YAML del playbook y estructura

Objetivo: declarar el playbook en YAML parseable por PlaybookRunner y crear la estructura de modulo.

- [ ] T001 [P] Crear `config/playbooks/app-development.yaml` con estructura completa: id `app-development`, display_name, version, mode_compatible [Operaciones PYME, CEO, default, CFO], complexity_routing (SIMPLE skip redirige a general, MODERADA 5 fases, COMPLEJA 7 fases), agents (7 declaraciones con role/skills_allowed/instructions), flow (sequential, fases_order [constitution, specify, plan, tasks, analyze, implement, test], approval_at_end_of [constitution, analyze]), output_schema, guardrails (max_total_llm_calls: 500, max_session_duration_seconds: 86400, cove_required: true, sandbox_required: true) (FR-001, FR-002, FR-003, FR-005, FR-010, FR-011)
- [ ] T002 [P] Crear `src/vigilancia_multiagente/enterprise/orchestration/app_development/__init__.py` como marker del subpaquete
- [ ] T003 Registrar submodulo `app_development` en `src/vigilancia_multiagente/enterprise/orchestration/__init__.py` con import aditivo (sin tocar imports existentes) (FR-001)

**Independent Test Criteria for Phase 1**: YAML parseable sin errores de schema; estructura de modulo importable sin excepciones; `complexity_routing.SIMPLE.skip: true` presente en YAML.

---

## Phase 2: Templates Jinja2 y scaffolds por tipo de app

Objetivo: crear los 6 templates de fase y los 4 scaffolds base para tipos de app soportados (FR-006, FR-007).

- [ ] T004 [P] Crear `config/templates/app-development/constitution.template.md` con variables de contexto documentadas (project_name, stack, constraints, target_directory, user_requirements) (FR-006)
- [ ] T005 [P] Crear `config/templates/app-development/spec.template.md` con variables (project_name, functional_requirements, success_criteria, scope) (FR-006)
- [ ] T006 [P] Crear `config/templates/app-development/plan.template.md` con variables (project_name, architecture, dependencies, phases) (FR-006)
- [ ] T007 [P] Crear `config/templates/app-development/tasks.template.md` con variables (project_name, tasks_list, dependencies) (FR-006)
- [ ] T008 [P] Crear `config/templates/app-development/analyze-report.template.md` con variables (project_name, inconsistencies, status, recommendations) (FR-006)
- [ ] T009 [P] Crear `config/templates/app-development/checklist.template.md` con variables (project_name, test_results, coverage, pass_fail) (FR-006)
- [ ] T010 [P] Crear scaffold `config/templates/app-development/src/python_cli/` con main.py + requirements.txt + README.md placeholder (FR-007)
- [ ] T011 [P] Crear scaffold `config/templates/app-development/src/python_streamlit_dashboard/` con app.py + pages/.gitkeep + requirements.txt placeholder (FR-007)
- [ ] T012 [P] Crear scaffold `config/templates/app-development/src/python_fastapi_internal/` con main.py + routes/.gitkeep + requirements.txt placeholder (FR-007)
- [ ] T013 [P] Crear scaffold `config/templates/app-development/src/jupyter_notebook/` con notebook.ipynb + requirements.txt placeholder (FR-007)

**Independent Test Criteria for Phase 2**: cada template contiene variables Jinja2 validas ({{ variable }}); cada scaffold contiene al menos los archivos declarados; templates renderizables con datos de ejemplo sin errores de sintaxis Jinja2.

---

## Phase 3: Agentes especializados por fase

Objetivo: implementar los 7 agentes con responsabilidad unica (SRP) y el coordinador de fases con gates de aprobacion (FR-002, FR-003, FR-004, FR-012).

### F3.1 -- Tests de agentes y coordinador

- [ ] T014 [P] [US1] Crear `tests/enterprise/orchestration/app_development/test_routing.py` con 4 tests: SIMPLE redirige a playbook general; MODERADA activa 5 fases [constitution, specify, plan, tasks, implement]; COMPLEJA activa 7 fases; routing con clasificacion invalida retorna error (FR-005, SC-004)
- [ ] T015 [P] [US1] Crear `tests/enterprise/orchestration/app_development/test_agents.py` con 7 tests unitarios (uno por agente): constitution_agent genera constitution.md con stack/restricciones/directorio; specify_agent genera spec.md con FRs; plan_agent genera plan.md; tasks_agent genera tasks.md; analyze_agent detecta inconsistencia y bloquea; implement_agent genera codigo en sandbox; test_agent ejecuta tests en sandbox. Todos con mocks de LLM y skills (FR-002, FR-012)
- [ ] T016 [US1] Crear `tests/enterprise/orchestration/app_development/test_phase_coordinator.py` con 6 tests: flujo COMPLEJA ejecuta 7 fases en orden; gate en constitution bloquea sin aprobacion; gate en analyze bloquea sin aprobacion; cancelacion mid-implement persiste estado parcial (EC-01); sandbox falla reporta error con max 2 reintentos (EC-02); analyze sin issues genera reporte "sin issues" y gate se presenta igualmente — al aprobar continua a implement (EC-04) (FR-003, SC-002)

### F3.2 -- Implementacion de agentes

- [ ] T017 [US1] Implementar `src/vigilancia_multiagente/enterprise/orchestration/app_development/constitution_agent.py` (~200 LOC): interactua con usuario para definir stack/restricciones/directorio destino, renderiza template, genera constitution.md (FR-002)
- [ ] T018 [US1] Implementar `src/vigilancia_multiagente/enterprise/orchestration/app_development/specify_agent.py` (~150 LOC): lee constitution.md, genera spec.md con requisitos funcionales y criterios de exito (FR-002)
- [ ] T019 [US1] Implementar `src/vigilancia_multiagente/enterprise/orchestration/app_development/plan_agent.py` (~150 LOC): lee constitution.md + spec.md, genera plan.md con arquitectura y dependencias (FR-002)
- [ ] T020 [US1] Implementar `src/vigilancia_multiagente/enterprise/orchestration/app_development/tasks_agent.py` (~150 LOC): lee plan.md, genera tasks.md con tareas ordenadas por dependencias (FR-002)
- [ ] T021 [US1] Implementar `src/vigilancia_multiagente/enterprise/orchestration/app_development/analyze_agent.py` (~200 LOC): verifica coherencia entre constitution/spec/plan/tasks, genera analyze-report.md, bloquea si detecta inconsistencias criticas (FR-012)
- [ ] T022 [US1] Implementar `src/vigilancia_multiagente/enterprise/orchestration/app_development/implement_agent.py` (~250 LOC): itera tareas en sandbox via skill `code:e2b_sandbox`, genera codigo, valida cada tarea contra su criterio de done (FR-004)
- [ ] T023 [US1] Implementar `src/vigilancia_multiagente/enterprise/orchestration/app_development/test_agent.py` (~200 LOC): ejecuta tests en sandbox, genera checklist.md, bloquea si fallan con max 2 reintentos; cada reintento REPORTA el contexto del fallo al usuario antes de reintentar (constitucion #4) (FR-004, EC-02)

### F3.3 -- Coordinador de fases

- [ ] T024 [US1] Implementar `src/vigilancia_multiagente/enterprise/orchestration/app_development/phase_coordinator.py` (~300 LOC): carga YAML, determina fases activas segun complejidad, ejecuta secuencialmente, implementa gates de aprobacion (bloquea hasta respuesta del usuario), persiste estado parcial en tabla `subagents` para resume (FR-001, FR-003, FR-005, EC-01). Hacer T016 verde

**Independent Test Criteria for Phase 3**: `pytest tests/enterprise/orchestration/app_development/` verde; cada agente genera el artefacto esperado con mocks; gates bloquean sin aprobacion; routing por complejidad funciona correctamente.

---

## Phase 4: Integracion sandbox, audit trail y copia final

Objetivo: integrar ejecucion en sandbox, registro de audit trail y copia final al destino del usuario (FR-004, FR-008, FR-009).

- [ ] T025 [US1] Integrar ejecucion exclusiva en sandbox para fases implement y test en `phase_coordinator.py`: toda invocacion de codigo pasa por skill `code:e2b_sandbox`, cero procesos hijo en host (FR-004, SC-003)
- [ ] T026 [US1] Implementar registro de audit trail en `phase_coordinator.py`: cada fase completada genera entrada con `triggered_by: app_development_phase` y `target_file: <project>/{fase}.md` en tabla `agent_modifications` o fallback JSONL (FR-009, SC-005)
- [ ] T027 [US1] Implementar copia final en `phase_coordinator.py`: tras aprobacion del usuario al final del flujo, copiar archivos del sandbox al directorio destino declarado en constitution.md via skill `code:file_system` (FR-008)
- [ ] T028 [US1] Manejar edge case EC-03 en `phase_coordinator.py`: directorio destino no existe o sin permisos de escritura -- detectar antes de copia final y solicitar correccion al usuario
- [ ] T029 [US1] Test e2e `tests/enterprise/orchestration/app_development/test_e2e_flow.py`: solicitud COMPLEJA ejecuta 7 fases, produce codigo funcional con tests pasando en sandbox, copia al destino, audit trail completo (SC-001, SC-003, SC-005)

**Independent Test Criteria for Phase 4**: test e2e verde; cero procesos hijo en host durante implement/test (verificable por mock de sandbox); audit trail con entradas por cada fase; copia final solo tras aprobacion.

---

## Phase 5: Verificacion final y guardrails

Objetivo: validar SC completos, guardrails operativos y cero regresiones.

- [ ] T030 [P] Correr `pytest tests/enterprise/orchestration/app_development/` completo y verificar verde
- [ ] T031 [P] Correr `ruff check src/vigilancia_multiagente/enterprise/orchestration/app_development/ tests/enterprise/orchestration/app_development/` sin issues
- [ ] T032 [P] Correr `python -m basedpyright src/vigilancia_multiagente/enterprise/orchestration/app_development/` sin nuevos errores
- [ ] T033 [P] Verificar que `config/playbooks/app-development.yaml` contiene guardrails completos: max_total_llm_calls, max_session_duration_seconds, cove_required, sandbox_required (FR-010)
- [ ] T034 Verificar SC-004: ejecutar 10 mensajes de ejemplo y confirmar que SIMPLE redirige a playbook general en al menos 90% de los casos
- [ ] T035 Verificar SC-002: simular flujo sin aprobacion en gates constitution y analyze; confirmar que fases posteriores no se ejecutan en 100% de los casos
- [ ] T036 Verificar SC-006: simular exceso de `max_total_llm_calls` y `max_session_duration_seconds`; confirmar que el sistema detiene la ejecucion con error explicito indicando el guardrail violado y el valor alcanzado (FR-010, SC-006)

---

## Dependencies

- **Phase 1** must complete before **Phase 2** y **Phase 3** (YAML y estructura necesarios).
- **Phase 2** (templates) es independiente de **Phase 3** (agentes) -- pueden ejecutarse en paralelo.
- **Phase 3 F3.1** (tests) must complete before **Phase 3 F3.2** (implementacion de agentes).
- **Phase 3 F3.2** (agentes) must complete before **Phase 3 F3.3** (coordinador).
- **Phase 3** must complete before **Phase 4** (integracion requiere agentes funcionales).
- **Phase 4** must complete before **Phase 5** (verificacion final).
- **Dependencias externas bloqueantes**: spec 009 (PlaybookRunner, SubagentRegistry, tabla subagents), spec 010 (indice empresarial), spec 011 (skills file_system, template_render).
- T014, T015, T016 son independientes entre si (archivos distintos).
- T017..T023 son secuenciales respecto a sus tests pero independientes entre si (archivos distintos, pueden paralelizarse entre desarrolladores).
- T004..T013 son todos independientes entre si (archivos distintos sin dependencia).

---

## Parallel Execution Examples

### Phase 2 Parallel Block

- Run T004, T005, T006, T007, T008, T009, T010, T011, T012, T013 en paralelo (archivos distintos sin dependencias).

### Phase 3 -- Tests Parallel Block

- Run T014, T015 en paralelo (archivos distintos).
- T016 puede ejecutarse en paralelo con T014 y T015.

### Phase 3 -- Agentes Parallel Block

Tras tests verdes, distribuir entre desarrolladores:

- **Dev A**: T017, T018 (constitution + specify).
- **Dev B**: T019, T020 (plan + tasks).
- **Dev C**: T021, T022 (analyze + implement).
- **Dev D**: T023 (test_agent).
- Finalmente T024 secuencial (coordinador integra todos).

### Phase 5 Parallel Block

- Run T030, T031, T032, T033 en paralelo (verificaciones independientes).

---

## Implementation Strategy

1. **Gated hasta priorizacion**: este spec es roadmap post-MVP. No se implementa hasta que specs 009, 010 y 011 esten operativos y el equipo priorice este playbook.
2. **Phase 1 primero**: declarar YAML + estructura. Esto valida que el PlaybookRunner puede cargar el playbook.
3. **Phase 2 y Phase 3 en paralelo**: templates (Phase 2) y agentes (Phase 3) no tienen dependencia entre si; pueden avanzar simultaneamente.
4. **Test-before-implementation**: dentro de Phase 3, los tests (T014-T016) se escriben antes que los agentes (T017-T024).
5. **Phase 4 como integracion**: solo tras agentes funcionales se integra sandbox + audit + copia final.
6. **Phase 5 como gate final**: nada se considera entregado hasta que SC verificados y linters verdes.
7. **Diferenciacion con spec 014**: este playbook maneja aplicaciones internas completas (UI/persistencia/workflow); spec 014 maneja dashboards/pipelines/metricas. No duplicar funcionalidad.
