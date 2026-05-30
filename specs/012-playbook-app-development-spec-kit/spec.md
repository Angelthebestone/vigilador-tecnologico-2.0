# Feature Specification: Playbook App-Development (Spec-Kit Pipeline Interno)

**Feature ID**: 012-playbook-app-development-spec-kit
**Created**: 2026-05-29
**Status**: Roadmap (post-MVP, fase F4b segun 00b-mvp-scope-y-cronograma.md)
**Related plan documents**:
- [plan vigilador 3.0/03-playbooks-y-orquestacion.md](../../plan%20vigilador%203.0/03-playbooks-y-orquestacion.md) (seccion "Playbook app-development", decision D3)
- [plan vigilador 3.0/00b-mvp-scope-y-cronograma.md](../../plan%20vigilador%203.0/00b-mvp-scope-y-cronograma.md) (tabla "Lo que NO entra en MVP")

---

## Problem Statement

El usuario empresarial necesita generar aplicaciones internas (dashboards con persistencia, automatizaciones con workflow propio, herramientas CLI/GUI para equipos) dentro de su PC sin depender de un desarrollador externo. Actualmente no existe un flujo estructurado que guie al agente desde la captura de requisitos hasta la entrega verificada de codigo funcional.

El plan v3.0 (decision D3) adopta el flujo Spec-Kit (`constitution -> specify -> plan -> tasks -> analyze -> implement`) como playbook interno reutilizable. Este spec define los requisitos para ese playbook, sus agentes secuenciales, gates de aprobacion y guardrails de ejecucion segura.

---

## Scope Boundaries

### In Scope

- Definicion del playbook `app-development` como flujo secuencial de 7 fases: constitution, specify, plan, tasks, analyze, implement, test.
- Agentes especializados por fase con responsabilidad unica (SRP).
- Gates de aprobacion humana al final de las fases `constitution` y `analyze`.
- Ejecucion de codigo generado exclusivamente en sandbox (cero ejecucion directa en host).
- Copia del resultado final al directorio destino del usuario solo tras aprobacion.
- Templates Jinja2 para cada fase (`config/templates/app-development/`).
- Scaffolds base por tipo de app (python_cli, python_streamlit_dashboard, python_fastapi_internal, jupyter_notebook).
- Integracion con `ComplexityClassifier` para routing: SIMPLE redirige a playbook `general`, MODERADA omite fase `analyze` y `test`, COMPLEJA ejecuta las 7 fases.
- Guardrails: max_total_llm_calls, max_session_duration_seconds, cove_required, sandbox_required.
- Audit trail: cada fase deja entrada en `agent_modifications` con `triggered_by: app_development_phase`.

### Out of Scope

- Generacion de apps para distribucion a clientes finales del usuario (packaging, deployment, soporte externo).
- Dashboards y pipelines de metricas sin logica de aplicacion propia (cubierto por spec 014 artifact-development).
- Goal-pursuit de larga duracion con checkpoints autonomos (cubierto por spec 013 goal-pursuit).
- Implementacion del `ComplexityClassifier` o `SubagentRegistry` (pertenecen a spec de orquestacion base, fase F4a MVP).
- Implementacion del sandbox MCP `e2b_sandbox` (ya existe como MCP `sandbox` del 2.0).
- Loops de autoaprendizaje (Prompt self-improvement sobre playbooks) — roadmap F5b.

---

## Assumptions

- **A-01**: El `PlaybookRunner` y `ComplexityClassifier` estan operativos antes de implementar este playbook (dependencia en spec de orquestacion base).
- **A-02**: El MCP `sandbox` del 2.0 esta disponible y funcional para ejecucion aislada de codigo generado.
- **A-03**: El skill `code:file_system` (spec 011) esta disponible para copiar artefactos finales al directorio destino del usuario.
- **A-04**: El usuario declara en la fase `constitution` el directorio destino absoluto donde se copiara el proyecto final.
- **A-05**: El LLM activo (Xiaomimimo `mimo-v2-flash` u otro configurado) soporta tool calling para que los agentes invoquen skills.
- **A-06**: La tabla `agent_modifications` esta disponible para audit trail (dependencia en spec de gobernanza F5b; si no existe, se usa JSONL como fallback).

---

## User Scenarios & Testing

### Primary User Story

Como operador en modo `Operaciones PYME`, quiero pedirle al Vigilador que genere una herramienta interna para mi empresa describiendo lo que necesito en lenguaje natural, para que el sistema produzca codigo funcional y verificado sin que yo tenga que programar.

### Acceptance Scenarios

1. **Given** el playbook `app-development` cargado y el modo `Operaciones PYME` activo, **When** el usuario pide "necesito un script Python que procese facturas XML y genere un resumen en Excel", **Then** el `ComplexityClassifier` clasifica como MODERADA o COMPLEJA y el `PlaybookRunner` inicia el flujo secuencial correspondiente.

2. **Given** la fase `constitution` ejecutandose, **When** el `constitution_agent` genera `constitution.md` con stack, restricciones y directorio destino, **Then** el sistema presenta el documento al usuario y espera aprobacion explicita antes de avanzar a `specify`.

3. **Given** las fases `constitution` a `tasks` completadas, **When** el `analyze_agent` detecta una inconsistencia critica entre `spec.md` y `plan.md`, **Then** el sistema bloquea el avance, reporta la inconsistencia al usuario y espera decision (corregir o aprobar con observacion).

4. **Given** la fase `implement` activa, **When** el `implement_agent` genera codigo, **Then** toda ejecucion de tests y validacion ocurre dentro del sandbox, sin ejecutar nada directamente en el host del usuario.

5. **Given** la fase `test` completada con todos los tests pasando, **When** el usuario aprueba el resultado final, **Then** el sistema copia los archivos generados al directorio destino declarado en `constitution.md` y reporta la ruta final.

6. **Given** una solicitud clasificada como SIMPLE por el `ComplexityClassifier`, **When** el `PlaybookRunner` evalua el routing, **Then** redirige al playbook `general` sin iniciar el flujo `app-development`.

### Edge Cases

- **EC-01**: El usuario cancela en medio de la fase `implement` — el sistema persiste el estado parcial en `subagents` y permite retomar desde la ultima tarea completada.
- **EC-02**: El sandbox falla durante ejecucion de tests — el `test_agent` reporta el error con contexto y sugiere correccion sin reintentar indefinidamente (max 2 reintentos).
- **EC-03**: El directorio destino declarado en `constitution.md` no existe o no tiene permisos de escritura — el sistema detecta esto antes de la copia final y solicita correccion al usuario.
- **EC-04**: El `analyze_agent` no encuentra inconsistencias — genera `analyze-report.md` con status "sin issues" y el gate de aprobacion se presenta igualmente para confirmacion.

---

## Functional Requirements

- **FR-001**: El sistema MUST cargar el playbook `app-development` desde `config/playbooks/app-development.yaml` con las 7 fases declaradas en orden secuencial: constitution, specify, plan, tasks, analyze, implement, test.
  - *Fuente*: 03-playbooks-y-orquestacion.md, seccion "Playbook app-development", campo `flow.fases_order`.

- **FR-002**: El sistema MUST asignar un agente especializado por fase, cada uno con su propio `role`, `skills_allowed` e `instructions`, sin mezclar responsabilidades entre fases.
  - *Fuente*: 03-playbooks-y-orquestacion.md, seccion "Playbook app-development", campo `agents`.

- **FR-003**: El sistema MUST implementar gates de aprobacion humana al final de las fases `constitution` y `analyze`, bloqueando el avance hasta recibir aprobacion explicita del usuario.
  - *Fuente*: 03-playbooks-y-orquestacion.md, campo `flow.approval_at_end_of`.

- **FR-004**: El sistema MUST ejecutar todo codigo generado exclusivamente dentro del sandbox (MCP `sandbox`); cero ejecucion directa en el host del usuario durante las fases implement y test.
  - *Fuente*: 03-playbooks-y-orquestacion.md, campo `guardrails.sandbox_required: true`.

- **FR-005**: El sistema MUST aplicar routing por complejidad: SIMPLE redirige a playbook `general`; MODERADA activa fases [constitution, specify, plan, tasks, implement]; COMPLEJA activa las 7 fases.
  - *Fuente*: 03-playbooks-y-orquestacion.md, campo `complexity_routing`.

- **FR-006**: El sistema MUST proveer templates Jinja2 en `config/templates/app-development/` para cada fase (constitution.template.md, spec.template.md, plan.template.md, tasks.template.md, analyze-report.template.md, checklist.template.md).
  - *Fuente*: 03-playbooks-y-orquestacion.md, seccion "Templates Jinja2 asociados".

- **FR-007**: El sistema MUST proveer scaffolds base por tipo de app en `config/templates/app-development/src/` (python_cli, python_streamlit_dashboard, python_fastapi_internal, jupyter_notebook).
  - *Fuente*: 03-playbooks-y-orquestacion.md, seccion "Templates Jinja2 asociados".

- **FR-008**: El sistema MUST copiar los archivos finales al directorio destino del usuario solo tras aprobacion explicita al final del flujo, usando el path absoluto declarado en `constitution.md`.
  - *Fuente*: 03-playbooks-y-orquestacion.md, seccion "Donde se ejecuta el codigo generado".

- **FR-009**: El sistema MUST registrar cada fase completada como entrada en el audit trail con `triggered_by: app_development_phase` y `target_file: <project>/{fase}.md`. La tabla `agent_modifications` es responsabilidad del spec de gobernanza (F5b / spec 016); hasta que exista, el fallback JSONL es el path por defecto para audit trail.
  - *Fuente*: 03-playbooks-y-orquestacion.md, seccion "Audit trail".

- **FR-010**: El sistema MUST aplicar guardrails configurables: `max_total_llm_calls` (default 500), `max_session_duration_seconds` (default 86400), `cove_required: true`.
  - *Fuente*: 03-playbooks-y-orquestacion.md, campo `guardrails`.

- **FR-011**: El sistema MUST declarar `mode_compatible` para el playbook, incluyendo al menos: Operaciones PYME, CEO, default, CFO.
  - *Fuente*: 03-playbooks-y-orquestacion.md, campo `mode_compatible`.

- **FR-012**: El `analyze_agent` MUST bloquear el avance a `implement` si detecta inconsistencias criticas entre los documentos generados (constitution, spec, plan, tasks), reportando las inconsistencias al usuario.
  - *Fuente*: 03-playbooks-y-orquestacion.md, instrucciones del `analyze_agent`.

---

## Key Entities

- **App-development playbook YAML** (`config/playbooks/app-development.yaml`): declaracion del flujo, agentes, routing por complejidad, guardrails y output_schema.
- **Project workspace**: directorio temporal en sandbox donde se generan los documentos de fase y el codigo. Se copia al destino final solo tras aprobacion.
- **Phase document**: artefacto generado por cada fase (constitution.md, spec.md, plan.md, tasks.md, analyze-report.md, checklist.md). Persiste como evidencia del proceso.
- **Approval gate**: punto de control donde el flujo se detiene hasta recibir confirmacion humana.

---

## Success Criteria

- **SC-001**: Una solicitud de app COMPLEJA (ej: "script Python que procese CSV y genere histograma") ejecuta las 7 fases en orden y produce codigo funcional con tests pasando en sandbox, en un tiempo total de ejecucion automatica menor a 2 horas (excluye tiempo de espera en gates de aprobacion humana).
- **SC-002**: Los gates de aprobacion bloquean efectivamente el avance: sin aprobacion del usuario, las fases posteriores no se ejecutan (verificable en 100% de los casos de test).
- **SC-003**: Cero ejecucion de codigo generado fuera del sandbox durante las fases implement y test (verificable por ausencia de procesos hijo en el host durante ejecucion del playbook).
- **SC-004**: El routing por complejidad redirige correctamente solicitudes SIMPLE al playbook `general` en al menos el 90% de los casos de test (10 mensajes de ejemplo).
- **SC-005**: Cada fase completada deja entrada verificable en el audit trail con los campos requeridos (triggered_by, target_file).
- **SC-006**: Al exceder `max_total_llm_calls` o `max_session_duration_seconds`, el sistema detiene la ejecucion del playbook con un error explicito que indica el guardrail violado y el valor alcanzado.

---

## Delivery Constraints

- Constitucion v1.2.0 — Simplicidad obligatoria (#2): el playbook no introduce abstracciones mas alla de las 7 fases declaradas; cada agente tiene una sola responsabilidad.
- Constitucion v1.2.0 — Modularidad primero (#3): cada agente es un modulo independiente con interfaz clara (role + skills_allowed + instructions).
- Constitucion v1.2.0 — Manejo de errores estricto (#4): fallos en sandbox o en gates se propagan con contexto; no se silencian.
- Constitucion v1.2.0 — Cambios quirurgicos (#5): este playbook no modifica componentes del 2.0 ni otros playbooks existentes.
- SRP (SOLID): un agente por fase, una responsabilidad por agente.
- CQS: los agentes generan documentos (comando) o verifican coherencia (query), nunca ambos en la misma operacion.

---

## Dependencies

- `PlaybookRunner` y `ComplexityClassifier` operativos (spec de orquestacion base, F4a MVP).
- MCP `sandbox` del 2.0 funcional.
- Skill `code:file_system` (spec 011).
- Skill `documents:template_render` (spec 011).
- Tabla `agent_modifications` o fallback JSONL para audit trail.
- `SubagentRegistry` para persistencia de estado parcial y resume.
