# Implementation Plan: Artifact-Development (Dashboards, Pipelines y Metricas Auto-generadas)

**Feature ID**: 014-artifact-development
**Created**: 2026-05-29
**Spec**: [spec.md](spec.md)

## Problem

El usuario empresarial necesita visualizar metricas, KPIs y datos de gestion rapidamente sin construir una aplicacion completa. Generar un dashboard, pipeline de datos o reporte programado requiere conocimiento tecnico o herramientas externas costosas. No existe un flujo que inventarie fuentes de datos disponibles, modele las metricas deseadas, construya el artefacto de visualizacion y lo publique para consumo interno. Se necesita un playbook `artifact-development` con flujo orientado a datos y metricas, diferenciado del flujo Spec-Kit completo de `app-development`.

## Approach

Este plan es **roadmap post-MVP**. Describe COMO se construiria el playbook `artifact-development` al priorizarse, con dependencias en specs 009 (MVP foundation: PlaybookRunner), 010 (ingestion/indice empresarial para inventario de fuentes) y 012 (app-development, que establece la infraestructura de sandbox y copia final). La implementacion se estructura en 4 fases: (1) playbook YAML y modulo `enterprise/artifacts/`, (2) agente de inventario de fuentes con discovery en indice empresarial, (3) agente de modelado de KPIs y builder en sandbox, (4) verificacion, publicacion y registro de metadatos. El flujo es lineal (6 fases secuenciales) sin orquestacion DAG compleja, diferenciandose explicitamente de app-development.

---

## Technical Context

| Area | Decision |
|------|----------|
| Ubicacion modulo | `src/vigilancia_multiagente/enterprise/artifacts/` |
| Ubicacion playbook YAML | `config/playbooks/artifact-development.yaml` |
| Inventario de fuentes | Consulta indice empresarial (TurboVecIndex, spec 010) + archivos locales declarados |
| Sandbox | MCP `sandbox` del 2.0 via skill `code:e2b_sandbox` |
| Registro de artefactos | JSONL como persistencia DEFAULT (sin migración SQL); tabla SQL como extensión futura explícita |
| Skills requeridos | `analytics:source_profile`, `analytics:kpi_modeling`, `analytics:dashboard_generate` (definidos en spec de skills) |
| LLM | Adapter activo segun `llm.default` |
| Diferenciacion con 012 | Flujo propio de 6 fases orientado a datos; NO replica constitution/specify/plan/tasks/analyze/implement |

## External Constraints

| Constraint | Impact |
|------------|--------|
| Dependencia en PlaybookRunner (spec 009 F4a) | Runner debe estar operativo para cargar el playbook |
| Dependencia en indice empresarial (spec 010) | Inventario de fuentes requiere TurboVecIndex para buscar datos indexados |
| Dependencia en skills de analytics | source_profile, kpi_modeling, dashboard_generate deben existir o tener stubs |
| Dependencia en skill `code:file_system` (spec 011) | Publicacion de artefactos al directorio destino |
| Constitucion v1.2.0 #5 Cambios quirurgicos | Cero modificaciones al 2.0 ni a otros playbooks |
| DRY respecto a spec 012 | NO replica flujo Spec-Kit; usa su propio flujo orientado a datos |
| KISS | Flujo lineal de 6 fases secuenciales; sin DAG ni orquestacion compleja |
| Archivos <= 400 LOC | Cada agente y componente en su propio archivo |

---

## Files to Create / Modify

### New Files

| File | Purpose |
|------|---------|
| `config/playbooks/artifact-development.yaml` | Declaracion del playbook: 6 fases, agentes, mode_compatible, output_schema |
| `src/vigilancia_multiagente/enterprise/artifacts/__init__.py` | Marker del subpaquete |
| `src/vigilancia_multiagente/enterprise/artifacts/source_inventory_agent.py` | Agente fase source_inventory: inventaria fuentes disponibles (~250 LOC) |
| `src/vigilancia_multiagente/enterprise/artifacts/metric_model_agent.py` | Agente fase metric_model: define KPIs y contratos de datos (~200 LOC) |
| `src/vigilancia_multiagente/enterprise/artifacts/pipeline_planner.py` | Helper interno del coordinator (NO agente autónomo): planifica flujo de datos fuente->visualizacion (~150 LOC) |
| `src/vigilancia_multiagente/enterprise/artifacts/builder_agent.py` | Agente fase build: construye artefacto en sandbox (~300 LOC) |
| `src/vigilancia_multiagente/enterprise/artifacts/verifier.py` | Agente fase verify: valida artefacto funcional en sandbox (~150 LOC) |
| `src/vigilancia_multiagente/enterprise/artifacts/publisher.py` | Agente fase publish: copia al destino y registra metadatos (~200 LOC) |
| `src/vigilancia_multiagente/enterprise/artifacts/artifact_registry.py` | Registro de artefactos generados con metadatos completos (~150 LOC) |
| `src/vigilancia_multiagente/enterprise/artifacts/artifact_coordinator.py` | Coordinador secuencial de las 6 fases (~250 LOC) |
| `tests/enterprise/artifacts/test_source_inventory_agent.py` | Tests de inventario: fuentes encontradas, sin fuentes, fuente no disponible |
| `tests/enterprise/artifacts/test_metric_model_agent.py` | Tests de modelado: KPIs generados, brecha de datos |
| `tests/enterprise/artifacts/test_builder_agent.py` | Tests de construccion: dashboard, pipeline, notebook |
| `tests/enterprise/artifacts/test_artifact_coordinator.py` | Tests e2e: flujo completo, diferenciacion con app-development |

### Modified Files

| File | Changes |
|------|---------|
| `src/vigilancia_multiagente/enterprise/__init__.py` | Registrar submodulo `artifacts` (import aditivo) |

---

## Constitution Check (Pre-Design)

- **Gate result**: PASS
- **Alignment**:
  - Pensar Antes de Codificar: dependencias explicitas en specs 009/010/011/012; assumptions del spec (A-01..A-06) documentadas; diferenciacion con app-development declarada antes de implementar.
  - Simplicidad Obligatoria: 6 fases lineales sin abstracciones adicionales; cero orquestacion DAG; cada agente tiene una sola responsabilidad.
  - Modularidad Primero: un archivo por agente/componente bajo `enterprise/artifacts/`; coordinador separado de agentes; registro de artefactos separado de construccion.
  - Cambios Quirurgicos y Trazables: cero modificaciones al 2.0; solo un import aditivo en `enterprise/__init__.py`; cada FR traza a 03-playbooks-y-orquestacion.md seccion "Playbook artifact-development".
  - Entrega Verificable: cada fase produce artefacto verificable; SC del spec medibles con tests automatizados.
- **Diseno de Software**: SRP (un agente = una fase), SoC (inventario/modelado/construccion/verificacion/publicacion separados), DIP (agentes dependen de abstracciones ToolWrapper no de implementaciones), CQS (verifier solo valida, publisher solo persiste), KISS (flujo lineal secuencial), DRY (NO replica flujo Spec-Kit de spec 012; usa flujo propio orientado a datos).

---

## Phases

### Phase 1 — Playbook YAML y estructura del modulo (1-2 dias)

1. Crear `config/playbooks/artifact-development.yaml` con: id, display_name, mode_compatible (CEO, CFO, Operaciones PYME, Marketing), flow sequential con fases_order [source_inventory, metric_model, pipeline_plan, build, verify, publish], agents (3 declaraciones: source_inventory_agent, metric_model_agent, builder_agent), output_schema (artifact_type, artifact_path, data_sources, refresh_policy, metrics), guardrails.
2. Crear estructura `enterprise/artifacts/` con `__init__.py` y archivos placeholder.
3. Validar que el YAML es parseable por `PlaybookRunner.validate()`.
4. Verificar diferenciacion con app-development: el YAML no contiene fases constitution/specify/plan/tasks/analyze/implement.

**Output**: `artifact-development.yaml` validado + estructura de modulo creada.

### Phase 2 — Source Inventory Agent (2-3 dias)

1. Implementar `source_inventory_agent.py`: consulta indice empresarial (TurboVecIndex) para fuentes indexadas, escanea archivos locales declarados por el usuario, verifica disponibilidad de cada fuente (archivo existe, API responde, DB accesible), genera inventario con: nombre, tipo (CSV, API, DB, documento indexado), ubicacion, disponibilidad.
2. Manejar edge cases: fuente no disponible (marca como no disponible, sugiere alternativas — EC-01), cero fuentes encontradas (reporta al usuario, sugiere indexar datos — scenario 6).
3. Tests: inventario con 3 fuentes disponibles, fuente eliminada, sin fuentes.

**Output**: source_inventory_agent funcional con tests verdes.

### Phase 3 — Metric Model Agent y Builder Agent (3-4 dias)

1. Implementar `metric_model_agent.py`: recibe inventario de fuentes + solicitud del usuario, define KPIs con: nombre, formula, fuente de datos, granularidad temporal, formato de visualizacion recomendado. Detecta brechas (datos requeridos no disponibles en fuentes — EC-02).
2. Implementar `pipeline_planner.py` como helper interno del coordinator (NO agente autónomo — KISS): genera plan tecnico de flujo de datos desde fuentes hasta visualizacion final, incluyendo transformaciones necesarias y refresh_policy.
3. Implementar `builder_agent.py`: construye el artefacto en sandbox segun tipo solicitado (dashboard HTML/Streamlit/React, pipeline local, notebook, reporte, grafica). Usa skills `analytics:dashboard_generate` y `code:e2b_sandbox`. Maneja error de construccion con max 2 reintentos (EC-03).
4. Tests: KPIs generados correctamente, brecha de datos detectada, dashboard construido en sandbox, tipo no soportado (EC-04).

**Output**: metric_model_agent + pipeline_planner + builder_agent funcionales con tests verdes.

### Phase 4 — Verificacion, publicacion y registro (2-3 dias)

1. Implementar `verifier.py`: valida artefacto funcional en sandbox (dashboard renderiza sin errores, pipeline procesa datos, notebook ejecuta sin excepciones). Reporta resultado de verificacion.
2. Implementar `publisher.py`: copia artefacto verificado al directorio destino via `code:file_system`. Solo publica tras verificacion exitosa (FR-009).
3. Implementar `artifact_registry.py`: registra cada artefacto publicado con metadatos completos: artifact_type, artifact_path, data_sources, refresh_policy, metrics, created_at. Persiste en JSONL como almacenamiento DEFAULT (sin migración SQL nueva; tabla SQL como extensión futura explícita).
4. Implementar `artifact_coordinator.py`: orquesta las 6 fases secuencialmente, pasa contexto entre fases (inventario -> modelo -> plan -> build -> verify -> publish).
5. Test e2e: solicitud de dashboard con 2 fuentes y 3 KPIs ejecuta las 6 fases, produce artefacto funcional, registra metadatos completos.
6. Test de diferenciacion: solicitud de "dashboard de ventas" va a artifact-development; solicitud de "herramienta interna para el equipo" va a app-development (FR-010).

**Output**: flujo completo operativo con verificacion, publicacion y registro verificados.

---

## Rollout Strategy

**Tipo**: roadmap post-MVP. Este plan describe COMO se construiria al priorizarse tras completar specs 009 (MVP foundation), 010 (ingestion/indice empresarial) y 012 (app-development, que establece infraestructura compartida de sandbox).

- **Prerequisitos**: PlaybookRunner operativo, indice empresarial (TurboVecIndex) disponible para inventario de fuentes, skills de analytics implementados o con stubs funcionales, MCP sandbox accesible.
- **Backward compatibility**: cero impacto en el 2.0. Playbook aditivo al catalogo. Modulo `enterprise/artifacts/` no interfiere con `application/artifacts/` existente del 2.0.
- **Activacion**: disponible para modos CEO, CFO, Operaciones PYME, Marketing una vez desplegado.
- **Coexistencia con app-development**: el routing entre ambos playbooks se basa en la naturaleza de la solicitud: metricas/visualizacion/pipeline -> artifact-development; producto interno completo con UI/persistencia/workflow -> app-development. El ComplexityClassifier o el PlaybookRunner determina cual activar.

---

## Success Criteria

- **SC-001**: Un artefacto tipo dashboard se genera completamente (inventario a publicacion) en menos de 30 minutos para 1-3 fuentes y 3-5 KPIs (traza a spec SC-001).
- **SC-002**: El inventario de fuentes identifica correctamente al menos 90% de las fuentes accesibles en casos de test (traza a spec SC-002).
- **SC-003**: El artefacto generado es funcional: dashboards renderizan sin errores, pipelines procesan datos, notebooks ejecutan sin excepciones (traza a spec SC-003).
- **SC-004**: Cada artefacto publicado tiene metadatos completos registrados (artifact_type, artifact_path, data_sources, refresh_policy, metrics) en 100% de los casos (traza a spec SC-004).
- **SC-005**: La diferenciacion artifact-development vs app-development funciona correctamente en 90% de 10 casos de test (traza a spec SC-005).

## Constitution Check (Post-Design)

- **Status**: PASS
- **Justification**: El plan respeta todos los principios de la constitucion v1.2.0. Simplicidad: flujo lineal de 6 fases sin orquestacion DAG compleja (KISS). Modularidad: un archivo por agente/componente bajo `enterprise/artifacts/` con responsabilidad unica (SRP, SoC). Cambios quirurgicos: cero modificaciones al 2.0; solo archivos nuevos; no interfiere con `application/artifacts/` existente. Entrega verificable: 5 SC medibles con tests automatizados. DRY: NO replica flujo Spec-Kit de spec 012; usa flujo propio de 6 fases orientado a datos y metricas. DIP: agentes dependen de abstracciones (ToolWrapper, skills). CQS: verifier solo valida, publisher solo persiste, builder solo construye. Archivos <= 400 LOC cada uno.
