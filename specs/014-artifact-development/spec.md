# Feature Specification: Artifact-Development (Dashboards, Pipelines y Metricas Auto-generadas)

**Feature ID**: 014-artifact-development
**Created**: 2026-05-29
**Status**: Roadmap (post-MVP, fase F4b/F5c segun 00b-mvp-scope-y-cronograma.md)
**Related plan documents**:
- [plan vigilador 3.0/03-playbooks-y-orquestacion.md](../../plan%20vigilador%203.0/03-playbooks-y-orquestacion.md) (seccion "Playbook artifact-development")
- [plan vigilador 3.0/00b-mvp-scope-y-cronograma.md](../../plan%20vigilador%203.0/00b-mvp-scope-y-cronograma.md) (tabla "Lo que NO entra en MVP": "Artifact-development (dashboards/pipelines auto-generados)")

---

## Problem Statement

El usuario empresarial necesita visualizar metricas, KPIs y datos de gestion de forma rapida sin construir una aplicacion completa. Actualmente, generar un dashboard, un pipeline de datos o un reporte programado requiere conocimiento tecnico o herramientas externas costosas. No existe un flujo que inventarie las fuentes de datos disponibles, modele las metricas deseadas, construya el artefacto de visualizacion y lo publique para consumo interno.

El plan v3.0 (correccion C0 del canon operativo) define el playbook `artifact-development` para crear artefactos de gestion (dashboards, pipelines, notebooks, reportes programados, graficas) sin pasar por el flujo completo de una aplicacion interna.

---

## Scope Boundaries

### In Scope

- Playbook `artifact-development` como flujo secuencial de 6 fases: source_inventory, metric_model, pipeline_plan, build, verify, publish.
- Agentes especializados por fase: inventario de fuentes, modelado de KPIs, construccion del artefacto.
- Tipos de artefactos soportados: dashboards HTML/Streamlit/React internos, pipelines de datos locales o cloud para KPIs, notebooks reproducibles, reportes programados, graficas para frontend o export a PDF (via WeasyPrint). Export a PPT fuera de scope MVP (skill futuro).
- Inventario automatico de fuentes de datos disponibles (indexadas en el sistema o accesibles via tools/MCPs).
- Definicion de contratos de datos y KPIs antes de construir el artefacto.
- Politica de refresco configurable por artefacto (refresh_policy).
- Registro del artefacto generado con su `artifact_path` y metadatos.
- Integracion con el indice empresarial para descubrir fuentes de datos ya indexadas.

### Out of Scope

- Aplicaciones internas completas con UI propia, persistencia o workflow (cubierto por spec 012 app-development).
- Ejecucion autonoma prolongada con checkpoints y capability tokens (cubierto por spec 013 goal-pursuit).
- Implementacion de skills de analytics (`analytics:source_profile`, `analytics:kpi_modeling`, `analytics:dashboard_generate`) — son dependencias que este spec consume pero no define.
- Diagnostico de brechas contra normas ISO/NTC (cubierto por playbook `company-optimization`).
- Frontend de visualizacion de artefactos generados (superficie "Artefactos" del frontend, diferida a F5c).
- Loops de autoaprendizaje sobre artefactos generados — roadmap F5b.

---

## Assumptions

- **A-01**: El `PlaybookRunner` esta operativo (dependencia en spec de orquestacion base F4a).
- **A-02**: El indice empresarial (TurboVecIndex o equivalente) esta disponible para buscar fuentes de datos indexadas.
- **A-03**: Los skills de analytics (`source_profile`, `kpi_modeling`, `dashboard_generate`) estan implementados o tienen stubs funcionales antes de activar este playbook.
- **A-04**: El MCP `sandbox` del 2.0 esta disponible para ejecucion aislada de codigo de construccion de artefactos.
- **A-05**: El skill `code:file_system` esta disponible para persistir artefactos generados en el directorio destino.
- **A-06**: El usuario tiene al menos una fuente de datos accesible (CSV, base de datos, API, documentos indexados) para que el inventario de fuentes produzca resultados.

---

## User Scenarios & Testing

### Primary User Story

Como usuario empresarial en modo CEO, quiero pedirle al Vigilador que cree un dashboard de KPIs de ventas a partir de mis datos en Drive y un CSV local, para visualizar el rendimiento del equipo sin necesidad de configurar herramientas de BI manualmente.

### Acceptance Scenarios

1. **Given** el playbook `artifact-development` activo y fuentes de datos accesibles, **When** el usuario pide "crea un dashboard con las ventas mensuales del ultimo ano", **Then** el `source_inventory_agent` identifica las fuentes disponibles (archivos indexados, CSVs, APIs) y presenta un inventario al usuario.

2. **Given** el inventario de fuentes completado, **When** el `metric_model_agent` procesa la solicitud, **Then** genera una definicion de KPIs con nombre, formula, fuente de datos, granularidad temporal y formato de visualizacion recomendado.

3. **Given** el modelo de metricas definido, **When** el `builder_agent` construye el artefacto, **Then** genera el dashboard/pipeline/notebook en el sandbox y lo verifica antes de publicar.

4. **Given** un artefacto construido y verificado, **When** la fase `publish` se completa, **Then** el sistema registra el artefacto con su `artifact_path`, tipo, fuentes de datos usadas, politica de refresco y lista de metricas incluidas.

5. **Given** un artefacto con `refresh_policy: "cada 15 minutos"`, **When** se consulta el registro del artefacto, **Then** la politica de refresco esta almacenada como metadato declarativo (la ejecución automática del refresh es scope de un spec futuro).

6. **Given** el usuario pide un artefacto pero no tiene fuentes de datos accesibles, **When** el `source_inventory_agent` ejecuta el inventario, **Then** reporta que no encontro fuentes y sugiere al usuario indexar datos o conectar fuentes antes de continuar.

### Edge Cases

- **EC-01**: La fuente de datos referenciada ya no esta disponible (archivo eliminado, API caida) — el `source_inventory_agent` la marca como no disponible y sugiere alternativas o solicita accion al usuario.
- **EC-02**: El modelo de metricas requiere datos que no existen en ninguna fuente inventariada — el `metric_model_agent` reporta la brecha y sugiere fuentes adicionales a conectar.
- **EC-03**: La construccion del artefacto falla en sandbox (dependencia faltante, error de datos) — el `builder_agent` reporta el error con contexto y sugiere correccion (max 2 reintentos).
- **EC-04**: El usuario solicita un tipo de artefacto no soportado — el sistema informa los tipos disponibles y sugiere el mas cercano a la solicitud.

---

## Functional Requirements

- **FR-001**: El sistema MUST cargar el playbook `artifact-development` desde `config/playbooks/artifact-development.yaml` con las 6 fases declaradas en orden secuencial: source_inventory, metric_model, pipeline_plan, build, verify, publish.
  - *Fuente*: 03-playbooks-y-orquestacion.md, seccion "Playbook artifact-development", campo `flow.fases_order`.

- **FR-002**: El sistema MUST proveer un `source_inventory_agent` que inventarie las fuentes de datos disponibles para el usuario (indexadas en el sistema, accesibles via tools/MCPs, archivos locales declarados).
  - *Fuente*: 03-playbooks-y-orquestacion.md, seccion "Playbook artifact-development", agente `source_inventory_agent`.

- **FR-003**: El sistema MUST proveer un `metric_model_agent` que defina KPIs y contratos de datos a partir de la solicitud del usuario y las fuentes inventariadas, incluyendo: nombre del KPI, formula, fuente, granularidad y formato de visualizacion.
  - *Fuente*: 03-playbooks-y-orquestacion.md, seccion "Playbook artifact-development", agente `metric_model_agent`.

- **FR-004**: El sistema MUST proveer un `builder_agent` que construya el artefacto (dashboard, pipeline, notebook, reporte, grafica) en sandbox a partir del modelo de metricas y el plan de pipeline.
  - *Fuente*: 03-playbooks-y-orquestacion.md, seccion "Playbook artifact-development", agente `builder_agent`.

- **FR-005**: El sistema MUST soportar al menos los siguientes tipos de artefactos: dashboards HTML/Streamlit/React internos, pipelines de datos locales, notebooks reproducibles, reportes programados, graficas exportables a PDF (via WeasyPrint). Export a PPT queda fuera de scope del MVP; se implementara como skill futuro (`documents:export_ppt`).
  - *Fuente*: 03-playbooks-y-orquestacion.md, seccion "Playbook artifact-development", lista "Artefactos soportados".

- **FR-006**: El sistema MUST registrar cada artefacto generado con metadatos: artifact_type, artifact_path, data_sources, refresh_policy, metrics.
  - *Fuente*: 03-playbooks-y-orquestacion.md, seccion "Playbook artifact-development", campo `output_schema`.

- **FR-007**: El sistema MUST declarar una `refresh_policy` por artefacto que indique la frecuencia de actualizacion de datos (ej: "cada 15 minutos", "diario", "manual"). **Nota**: en esta entrega, `refresh_policy` es solo METADATO DECLARATIVO almacenado en el registro del artefacto; la ejecución automática del refresh según la política es scope de un spec futuro.
  - *Fuente*: 03-playbooks-y-orquestacion.md, campo `output_schema.properties.refresh_policy`.

- **FR-008**: El sistema MUST declarar `mode_compatible` para el playbook, incluyendo al menos: CEO, CFO, Operaciones PYME, Marketing.
  - *Fuente*: 03-playbooks-y-orquestacion.md, seccion "Playbook artifact-development", campo `mode_compatible`.

- **FR-009**: El sistema MUST ejecutar la construccion del artefacto en sandbox (cero ejecucion directa en host) y solo publicar al directorio destino tras verificacion exitosa.
  - *Fuente*: derivado de la misma politica de seguridad de app-development (03-playbooks-y-orquestacion.md, seccion "Donde se ejecuta el codigo generado").

- **FR-010**: El sistema MUST diferenciar claramente cuando usar `artifact-development` vs `app-development`: si el objetivo es solo dashboard/pipeline de metricas, usar artifact-development; si requiere producto interno completo con UI/persistencia/workflow propio, usar app-development.
  - *Fuente*: 03-playbooks-y-orquestacion.md, seccion "Playbook artifact-development", parrafo "Diferencia con app-development".

---

## Key Entities

- **Artefacto**: producto generado por el playbook. Atributos: artifact_type, artifact_path, data_sources, refresh_policy, metrics, created_at, last_refreshed_at.
- **Fuente de datos (data source)**: origen de informacion inventariado. Atributos: nombre, tipo (CSV, API, DB, documento indexado), ubicacion, disponibilidad, ultima verificacion.
- **KPI/Metrica**: indicador definido por el metric_model_agent. Atributos: nombre, formula, fuente, granularidad, formato de visualizacion.
- **Refresh policy**: politica declarativa de actualizacion de datos del artefacto. Valores posibles: intervalo temporal, evento, manual.
- **Pipeline plan**: plan tecnico de como fluyen los datos desde las fuentes hasta la visualizacion final.

---

## Success Criteria

- **SC-001**: Un artefacto tipo dashboard se genera completamente (desde inventario de fuentes hasta publicacion) en menos de 30 minutos para un caso con 1-3 fuentes de datos y 3-5 KPIs.
- **SC-002**: El inventario de fuentes identifica correctamente al menos el 90% de las fuentes accesibles en los casos de test (fuentes indexadas + archivos locales declarados).
- **SC-003**: El artefacto generado es funcional y verificable: dashboards se renderizan sin errores, pipelines procesan datos correctamente, notebooks ejecutan sin excepciones.
- **SC-004**: Cada artefacto publicado tiene metadatos completos registrados (artifact_type, artifact_path, data_sources, refresh_policy, metrics) en el 100% de los casos.
- **SC-005**: La diferenciacion artifact-development vs app-development funciona correctamente: solicitudes de "dashboard de ventas" van a artifact-development; solicitudes de "herramienta interna para el equipo" van a app-development (verificable en 90% de 10 casos de test).

---

## Delivery Constraints

- Constitucion v1.2.0 — Simplicidad obligatoria (#2): el playbook tiene 6 fases claras sin abstracciones adicionales; cada agente tiene una sola responsabilidad.
- Constitucion v1.2.0 — Modularidad primero (#3): los agentes y el playbook YAML son modulos independientes; el modulo `enterprise/artifacts/` encapsula la logica de artefactos. **Nota**: `enterprise/artifacts/` es un módulo INDEPENDIENTE de `application/artifacts/` del 2.0; no lo extiende ni lo modifica. Ambos coexisten sin interferencia (el plan confirma 'no interfiere').
- Constitucion v1.2.0 — Manejo de errores estricto (#4): fallos en inventario, modelado o construccion se propagan con contexto; no se silencian.
- Constitucion v1.2.0 — Cambios quirurgicos (#5): este playbook no modifica componentes del 2.0 ni otros playbooks existentes.
- KISS: el flujo es lineal (6 fases secuenciales); no se introduce orquestacion compleja tipo DAG para este playbook.
- DRY respecto a spec 012: artifact-development NO replica el flujo Spec-Kit (constitution/specify/plan/tasks/analyze/implement); usa su propio flujo orientado a datos y metricas.

---

## Dependencies

- `PlaybookRunner` operativo (spec de orquestacion base F4a).
- Indice empresarial (TurboVecIndex) para inventario de fuentes indexadas (spec 010).
- MCP `sandbox` del 2.0 para ejecucion aislada.
- Skills de analytics: `source_profile`, `kpi_modeling`, `dashboard_generate` (a definir en spec de skills).
- Skill `code:file_system` (spec 011) para publicacion de artefactos.
- Skill `documents:template_render` (spec 011) para generacion de reportes.
