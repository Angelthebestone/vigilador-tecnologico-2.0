# Implementation Plan: Playbook App-Development (Spec-Kit Pipeline Interno)

**Feature ID**: 012-playbook-app-development-spec-kit
**Created**: 2026-05-29
**Spec**: [spec.md](spec.md)

## Problem

El sistema carece de un flujo estructurado que guie al agente desde la captura de requisitos hasta la entrega verificada de codigo funcional para aplicaciones internas. El usuario empresarial no puede generar herramientas internas (dashboards con persistencia, automatizaciones con workflow propio, CLIs/GUIs) sin depender de un desarrollador externo. Se necesita implementar el playbook `app-development` que adopta el flujo Spec-Kit (constitution, specify, plan, tasks, analyze, implement, test) como pipeline interno reutilizable con gates de aprobacion humana, ejecucion en sandbox y routing por complejidad.

## Approach

Este plan es **roadmap post-MVP**. Describe COMO se construiria el playbook `app-development` al priorizarse, con dependencias en specs 009 (MVP foundation: PlaybookRunner, SubagentRegistry, tabla subagents) y 010 (ingestion/indice empresarial). La implementacion se estructura en 4 fases: (1) declaracion YAML del playbook con routing por complejidad, (2) templates Jinja2 y scaffolds por tipo de app, (3) agentes especializados por fase con gates de aprobacion, (4) integracion con sandbox, audit trail y copia final al destino del usuario. Cada fase produce artefactos verificables sin tocar componentes del 2.0.

---

## Technical Context

| Area | Decision |
|------|----------|
| Ubicacion playbook YAML | `config/playbooks/app-development.yaml` |
| Ubicacion templates | `config/templates/app-development/` |
| Modulo agentes | `src/vigilancia_multiagente/enterprise/orchestration/app_development/` |
| Sandbox | MCP `sandbox` del 2.0 via skill `code:e2b_sandbox` |
| Audit trail | Tabla `agent_modifications` con fallback JSONL si no existe |
| LLM | Adapter activo segun `llm.default` (Xiaomimimo default MVP); el YAML del playbook referencia el provider activo via configuracion, NO hardcodea modelo (ej: NO usar `base_llm: minimax-m-2.7`) |
| Persistencia estado | Tabla `subagents` (spec 009) para resume de fases parciales |
| Routing | `ComplexityClassifier` (spec 009) determina fases activas |

## External Constraints

| Constraint | Impact |
|------------|--------|
| Dependencia en PlaybookRunner (spec 009 F4a) | No se puede implementar hasta que el runner este operativo |
| Dependencia en ComplexityClassifier (spec 009) | Routing SIMPLE/MODERADA/COMPLEJA requiere clasificador funcional |
| Dependencia en skill `code:file_system` (spec 011) | Copia final al directorio destino requiere este skill |
| Dependencia en skill `documents:template_render` (spec 011) | Renderizado de templates Jinja2 por fase |
| Constitucion v1.2.0 #5 Cambios quirurgicos | Cero modificaciones a componentes del 2.0 ni otros playbooks |
| Archivos <= 400 LOC | Cada agente en su propio archivo con responsabilidad unica |
| Sandbox obligatorio | Cero ejecucion de codigo generado en host durante implement/test |

---

## Files to Create / Modify

### New Files

| File | Purpose |
|------|---------|
| `config/playbooks/app-development.yaml` | Declaracion del playbook: fases, agentes, routing, guardrails, output_schema |
| `config/templates/app-development/constitution.template.md` | Template Jinja2 para fase constitution |
| `config/templates/app-development/spec.template.md` | Template Jinja2 para fase specify |
| `config/templates/app-development/plan.template.md` | Template Jinja2 para fase plan |
| `config/templates/app-development/tasks.template.md` | Template Jinja2 para fase tasks |
| `config/templates/app-development/analyze-report.template.md` | Template Jinja2 para fase analyze |
| `config/templates/app-development/checklist.template.md` | Template Jinja2 para fase test |
| `config/templates/app-development/src/python_cli/.gitkeep` | Scaffold base para apps CLI Python |
| `config/templates/app-development/src/python_streamlit_dashboard/.gitkeep` | Scaffold base para dashboards Streamlit |
| `config/templates/app-development/src/python_fastapi_internal/.gitkeep` | Scaffold base para APIs internas FastAPI |
| `config/templates/app-development/src/jupyter_notebook/.gitkeep` | Scaffold base para notebooks |
| `src/vigilancia_multiagente/enterprise/orchestration/app_development/__init__.py` | Marker del subpaquete |
| `src/vigilancia_multiagente/enterprise/orchestration/app_development/constitution_agent.py` | Agente fase constitution (~200 LOC) |
| `src/vigilancia_multiagente/enterprise/orchestration/app_development/specify_agent.py` | Agente fase specify (~150 LOC) |
| `src/vigilancia_multiagente/enterprise/orchestration/app_development/plan_agent.py` | Agente fase plan (~150 LOC) |
| `src/vigilancia_multiagente/enterprise/orchestration/app_development/tasks_agent.py` | Agente fase tasks (~150 LOC) |
| `src/vigilancia_multiagente/enterprise/orchestration/app_development/analyze_agent.py` | Agente fase analyze con bloqueo por inconsistencias (~200 LOC) |
| `src/vigilancia_multiagente/enterprise/orchestration/app_development/implement_agent.py` | Agente fase implement iterativo en sandbox (~250 LOC) |
| `src/vigilancia_multiagente/enterprise/orchestration/app_development/test_agent.py` | Agente fase test con checklist final (~200 LOC) |
| `src/vigilancia_multiagente/enterprise/orchestration/app_development/phase_coordinator.py` | Coordinador secuencial de fases con gates de aprobacion (~300 LOC) |
| `tests/enterprise/orchestration/app_development/test_phase_coordinator.py` | Tests del coordinador: flujo completo, gates, routing |
| `tests/enterprise/orchestration/app_development/test_agents.py` | Tests unitarios de cada agente con mocks |
| `tests/enterprise/orchestration/app_development/test_routing.py` | Tests de routing por complejidad |

### Modified Files

| File | Changes |
|------|---------|
| `src/vigilancia_multiagente/enterprise/orchestration/__init__.py` | Registrar submodulo `app_development` (import aditivo) |

---

## Constitution Check (Pre-Design)

- **Gate result**: PASS
- **Alignment**:
  - Pensar Antes de Codificar: dependencias explicitas en specs 009/010/011; assumptions del spec declaradas y validadas antes de implementar.
  - Simplicidad Obligatoria: 7 fases declaradas sin abstracciones adicionales; cada agente tiene una sola responsabilidad; cero capas intermedias innecesarias.
  - Modularidad Primero: un archivo por agente, coordinador separado, templates separados del codigo; interfaces claras entre fases via documentos generados.
  - Cambios Quirurgicos y Trazables: cero modificaciones al 2.0; solo un import aditivo en `__init__.py` de orchestration; cada FR traza a 03-playbooks-y-orquestacion.md.
  - Entrega Verificable: cada fase produce artefacto verificable (documento o codigo); SC del spec medibles con tests automatizados.
- **Diseno de Software**: SRP (un agente = una fase = una responsabilidad), SoC (coordinador orquesta, agentes ejecutan, templates definen formato), DIP (agentes dependen de abstracciones ToolWrapper/PlaybookRunner no de implementaciones concretas), CQS (analyze_agent solo verifica/reporta, implement_agent solo genera), KISS (flujo lineal secuencial sin DAG complejo).

---

## Phases

### Phase 1 — Declaracion YAML del playbook (1-2 dias)

1. Crear `config/playbooks/app-development.yaml` con la estructura completa: id, display_name, version, mode_compatible, complexity_routing (SIMPLE skip, MODERADA 5 fases, COMPLEJA 7 fases), agents (7 declaraciones con role/skills_allowed/instructions), flow (sequential, fases_order, approval_at_end_of), output_schema, guardrails (max_total_llm_calls: 500, max_session_duration_seconds: 86400, cove_required: true, sandbox_required: true).
2. Validar que el YAML es parseable por `PlaybookRunner.validate()` (schema correcto, modes referenciados existen, skills referenciados existen).
3. Verificar que `complexity_routing.SIMPLE.skip: true` redirige al playbook `general`.

**Output**: `app-development.yaml` validado y cargable por el PlaybookRunner.

### Phase 2 — Templates Jinja2 y scaffolds (2-3 dias)

1. Crear los 6 templates Jinja2 en `config/templates/app-development/` con variables de contexto documentadas (project_name, stack, constraints, user_requirements, etc.).
2. Crear scaffolds base en `config/templates/app-development/src/` para los 4 tipos de app: python_cli (main.py + requirements.txt + README.md), python_streamlit_dashboard (app.py + pages/ + requirements.txt), python_fastapi_internal (main.py + routes/ + requirements.txt), jupyter_notebook (notebook.ipynb + requirements.txt).
3. Verificar que cada template renderiza correctamente con datos de ejemplo via `documents:template_render`.

**Output**: 6 templates + 4 scaffolds funcionales y renderizables.

### Phase 3 — Agentes especializados y coordinador (4-5 dias)

1. Implementar `phase_coordinator.py`: carga el YAML, determina fases activas segun complejidad, ejecuta secuencialmente, implementa gates de aprobacion (bloquea hasta respuesta del usuario), persiste estado parcial en `subagents` para resume.
2. Implementar `constitution_agent.py`: interactua con usuario para definir stack/restricciones/directorio destino, renderiza template, genera `constitution.md`.
3. Implementar `specify_agent.py`: lee constitution.md, genera spec.md con requisitos funcionales y criterios de exito.
4. Implementar `plan_agent.py`: lee constitution.md + spec.md, genera plan.md con arquitectura y dependencias.
5. Implementar `tasks_agent.py`: lee plan.md, genera tasks.md con tareas ordenadas por dependencias.
6. Implementar `analyze_agent.py`: verifica coherencia entre los 4 documentos, genera analyze-report.md, bloquea si detecta inconsistencias criticas (FR-012).
7. Implementar `implement_agent.py`: itera tareas en sandbox, genera codigo, valida cada tarea contra su criterio de done.
8. Implementar `test_agent.py`: ejecuta tests en sandbox, genera checklist.md, bloquea si fallan (max 2 reintentos; cada reintento REPORTA el contexto del fallo al usuario antes de reintentar, constitucion #4).

**Output**: 7 agentes + coordinador implementados con tests unitarios.

### Phase 4 — Integracion sandbox, audit trail y copia final (2-3 dias)

1. Integrar ejecucion exclusiva en sandbox para fases implement y test: toda invocacion de codigo pasa por skill `code:e2b_sandbox`, cero procesos hijo en host.
2. Implementar registro de audit trail: cada fase completada genera entrada con `triggered_by: app_development_phase` y `target_file`.
3. Implementar copia final: tras aprobacion del usuario al final del flujo, copiar archivos del sandbox al directorio destino declarado en constitution.md via `code:file_system`.
4. Validar edge cases: cancelacion mid-implement (persiste estado parcial), sandbox falla (reporta error, max 2 reintentos), directorio destino no existe (solicita correccion).
5. Test e2e: solicitud COMPLEJA ejecuta las 7 fases, produce codigo funcional con tests pasando en sandbox, copia al destino.

**Output**: flujo completo operativo con sandbox, audit y copia final verificados.

---

## Rollout Strategy

**Tipo**: roadmap post-MVP. Este plan describe COMO se construiria al priorizarse tras completar specs 009 (MVP foundation) y 010 (ingestion). No se implementa durante el MVP.

- **Prerequisitos**: PlaybookRunner operativo, ComplexityClassifier funcional, skills `code:file_system` y `documents:template_render` disponibles, MCP sandbox del 2.0 accesible.
- **Backward compatibility**: cero impacto en el 2.0. El playbook es aditivo; se registra en el catalogo sin modificar playbooks existentes.
- **Activacion**: disponible automaticamente para modos declarados en `mode_compatible` una vez desplegado.
- **Coexistencia**: solicitudes SIMPLE siguen yendo a playbook `general`; solo MODERADA/COMPLEJA activan app-development.

---

## Success Criteria

- **SC-001**: Una solicitud COMPLEJA ejecuta las 7 fases en orden y produce codigo funcional con tests pasando en sandbox en menos de 2 horas de ejecucion automatica (excluye tiempo de espera en gates de aprobacion) (traza a spec SC-001).
- **SC-002**: Gates de aprobacion bloquean el avance en 100% de los casos sin aprobacion del usuario (traza a spec SC-002).
- **SC-003**: Cero ejecucion de codigo generado fuera del sandbox durante implement/test, verificable por ausencia de procesos hijo en host (traza a spec SC-003).
- **SC-004**: Routing por complejidad redirige SIMPLE a playbook `general` en al menos 90% de 10 casos de test (traza a spec SC-004).
- **SC-005**: Cada fase completada deja entrada verificable en audit trail con campos requeridos (traza a spec SC-005).
- **SC-006**: Al exceder `max_total_llm_calls` o `max_session_duration_seconds`, el sistema detiene la ejecucion con error explicito indicando el guardrail violado (traza a spec SC-006).

## Constitution Check (Post-Design)

- **Status**: PASS
- **Justification**: El plan respeta todos los principios de la constitucion v1.2.0. Simplicidad: flujo lineal de 7 fases sin abstracciones adicionales. Modularidad: un archivo por agente con responsabilidad unica (SRP), coordinador separado (SoC). Cambios quirurgicos: cero modificaciones al 2.0, solo archivos nuevos bajo `enterprise/orchestration/app_development/` y `config/`. Entrega verificable: 5 SC medibles con tests automatizados. DIP: agentes dependen de abstracciones (ToolWrapper, PlaybookRunner). CQS: analyze solo verifica, implement solo genera. Archivos <= 400 LOC cada uno.
