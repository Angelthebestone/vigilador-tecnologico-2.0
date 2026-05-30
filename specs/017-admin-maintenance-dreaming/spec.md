# Feature Specification: Admin Maintenance y Dreaming Mode

**Feature ID**: 017-admin-maintenance-dreaming
**Created**: 2026-05-29
**Status**: Draft (specification phase) -- MVP parcial F5a (memory consolidation + ingestion sync); resto es roadmap F5b
**Related plan documents**:
- [plan vigilador 3.0/05-autoaprendizaje-y-autonomia.md](../../plan%20vigilador%203.0/05-autoaprendizaje-y-autonomia.md)
- [plan vigilador 3.0/00b-mvp-scope-y-cronograma.md](../../plan%20vigilador%203.0/00b-mvp-scope-y-cronograma.md)
- [plan vigilador 3.0/00-canon-operativo-corregido.md](../../plan%20vigilador%203.0/00-canon-operativo-corregido.md)

---

## Problem Statement

El agente acumula sesiones, documentos indexados, skills aprendidos, configuracion empresarial y dependencias externas (repos de tools/MCPs) que requieren mantenimiento continuo. Sin un proceso automatizado de consolidacion, sincronizacion y revision, el sistema degrada: la memoria crece sin compresion, los indices se fragmentan, la normativa local queda desactualizada, y los repos de tools/MCPs acumulan versiones obsoletas o vulnerables.

El Dreaming mode (decision #17 del plan) resuelve esto como proceso nocturno/idle que ejecuta tareas de auto-mantenimiento sin intervencion humana. Este spec define las fases del Dreaming, los loops de autoaprendizaje que corren dentro de el, la indexacion empresarial incremental, la revision normativa localizada por `company_geo`, y el mantenimiento admin de repositorios clonados.

Este spec NO cubre el mecanismo de audit trail ni rollback (spec 016); consume `AgentModifier` de spec 016 para registrar sus cambios.

---

## Scope Boundaries

### Scope / MVP vs Roadmap

Segun `00b-mvp-scope-y-cronograma.md`:
- **MVP F5a (1 semana)**: Dreaming basico = memory consolidation + ingestion sync. Solo estas dos fases entran en MVP.
- **Roadmap F5b**: los 5+ loops de autoaprendizaje (Skill learning, Writing style, Prompt self-improvement, Tool composition, COMPANY self-update), regulatory/local watcher, admin repo maintenance, Dreaming Report completo.

Este spec documenta el sistema completo. Los FR marcados como "MVP" son los unicos obligatorios para la primera entrega.

### In Scope

- **Dreaming mode**: proceso que se activa por cron (3 AM) o por idle > 10 min.
- **Fase 1 - Memory consolidation** [MVP F5a]: recoger sesiones del dia, comprimir, fusionar en memoria de largo plazo.
- **Fase 5 - Enterprise ingestion sync** [MVP F5a]: sincronizacion incremental de conectores (Drive, OneDrive, local_fs) con documentos nuevos/modificados.
- **Fase 2 - Skill curator** [Roadmap F5b]: revalidar skills aprendidos contra ejecuciones recientes; deprecar los que fallan.
- **Fase 3 - Self-improvement** [Roadmap F5b]: analizar feedbacks negativos, generar variantes de prompts, ejecutar A/B tests.
- **Fase 4 - Config refresher** [Roadmap F5b]: detectar gaps en SOUL/COMPANY, proponer actualizaciones.
- **Fase 6 - Regulatory/local watch** [Roadmap F5b]: revisar cambios normativos/impuestos/normas por `company_geo`.
- **Fase 7 - Index maintenance** [Roadmap F5b]: vacuum/compact de TurboVecIndex.
- **Fase 8 - Scheduled artifacts/reports** [Roadmap F5b]: generar dashboards y reportes programados.
- **Fase 9 - Admin repo maintenance** [Roadmap F5b]: revisar repos clonados de tools/MCPs contra upstream.
- **Fase 10 - Audit report / Dreaming Report** [Roadmap F5b]: generar reporte con changelog del dia + metricas.
- **Loops de autoaprendizaje** (7 loops definidos en doc fuente) [Roadmap F5b].

### Out of Scope

- Mecanismo de audit trail, tabla `agent_modifications`, rollback, approval-gate (spec 016).
- AnomalyDetector y capability tokens (specs de gobernanza/seguridad, roadmap).
- Frontend completo de admin/Dreaming (roadmap F5c segun 00b).
- PI defense (spec separado).
- Implementacion de conectores de ingestion (spec 010 F2).
- TurboVecIndex (spec 010 F2).

---

## Assumptions

- **A-01**: El proceso Dreaming corre en la misma maquina que el agente principal, con acceso al filesystem local y a la metadata DB.
- **A-02**: El scheduler (cron 3 AM o idle trigger) es configurable via fields en `settings.py` (e.g. `dreaming_cron_hour`, `dreaming_idle_timeout_min`, `dreaming_enabled`). Fields nuevos con defaults:
  - `dreaming_enabled: bool = True`
  - `dreaming_cron_hour: int = 3`
  - `dreaming_idle_timeout_min: int = 10`
- **A-03**: Los conectores de ingestion (Drive, OneDrive, local_fs) ya estan implementados (spec 010) antes de que la Fase 5 se active.
- **A-04**: `AgentModifier` (spec 016) esta disponible para que los loops de autoaprendizaje registren sus cambios.
- **A-05**: El LLM activo esta disponible durante Dreaming para tareas que requieren generacion (diff_summary, variantes de prompts, resumen de sesiones).
- **A-06**: `company_geo` (pais, departamento, municipio, timezone) esta configurado en el onboarding (spec 009) antes de que la Fase 6 se active.
- **A-07**: Los repos de tools/MCPs estan clonados localmente y accesibles via git para la Fase 9.
- **A-08**: Para MVP F5a, solo se requiere que existan sesiones almacenadas y al menos un conector de ingestion configurado.

---

## User Scenarios & Testing

### Primary User Story

Como **operador del Vigilador 3.0**, quiero que el sistema ejecute automaticamente tareas de mantenimiento durante la noche o periodos de inactividad (consolidar memoria, sincronizar documentos, revisar normativa, mantener repos), para que el agente este siempre actualizado y optimizado sin requerir mi intervencion manual.

### Acceptance Scenarios

1. **Given** el sistema con sesiones del dia sin consolidar, **When** se activa Dreaming (cron 3 AM o idle > 10 min), **Then** la Fase 1 (memory consolidation) comprime las sesiones del dia en memoria de largo plazo y las sesiones originales se marcan como consolidadas. [MVP F5a]

2. **Given** conectores de ingestion configurados con documentos nuevos desde la ultima sincronizacion, **When** Dreaming ejecuta Fase 5, **Then** los documentos nuevos/modificados se indexan incrementalmente sin re-procesar documentos sin cambios. [MVP F5a]

3. **Given** un skill aprendido que fallo en sus ultimas 3 ejecuciones, **When** Dreaming ejecuta Fase 2 (Skill curator), **Then** el skill se marca como `deprecated` y deja de ofrecerse en el discovery. [Roadmap F5b]

4. **Given** 5+ feedbacks negativos sobre un prompt en los ultimos 7 dias, **When** Dreaming ejecuta Fase 3 (Self-improvement), **Then** se genera una variante del prompt y se activa un A/B test 50/50 para las siguientes sesiones. [Roadmap F5b]

5. **Given** el usuario pregunto algo que el agente no pudo responder por falta de informacion en COMPANY, **When** Dreaming ejecuta Fase 4 (Config refresher), **Then** se genera una propuesta de actualizacion a `config/company/*.md` y se aplica via `AgentModifier`. [Roadmap F5b]

6. **Given** `company_geo` configurado como Colombia/Santander/Barrancabermeja, **When** Dreaming ejecuta Fase 6 (Regulatory watch), **Then** se buscan fuentes oficiales vigentes y se genera una propuesta con citas si hay cambios relevantes, o se marca incertidumbre si no hay fuente suficiente. [Roadmap F5b]

7. **Given** un MCP clonado con nueva release upstream, **When** Dreaming ejecuta Fase 9 (Admin repo maintenance), **Then** se genera propuesta admin con diff, clasificacion de impacto (patch/feature/breaking/security) y resultado de tests, sin promover automaticamente. [Roadmap F5b]

8. **Given** Dreaming completo todas sus fases, **When** finaliza el ciclo, **Then** se genera un Dreaming Report con resumen de cambios aplicados, pendientes de aprobacion y metricas del dia. [Roadmap F5b]

### Edge Cases

- **EC-01**: Dreaming se activa pero el LLM no esta disponible. Las fases que requieren LLM (1, 3, 4, 5, 6, 10) se saltan con log de warning; las fases que no lo requieren (7, 9 parcial) se ejecutan normalmente.
- **EC-02**: Idle trigger se activa pero el usuario vuelve a interactuar. Dreaming se pausa al final de la fase actual y se reanuda en el proximo idle o cron.
- **EC-03**: Un conector de ingestion falla durante Fase 5. Se registra el error, se continua con los demas conectores y se reintenta el fallido en el proximo ciclo.
- **EC-04**: La Fase 9 detecta un breaking change en un MCP. Se genera propuesta con clasificacion `breaking` y NO se aplica automaticamente; queda como propuesta admin.
- **EC-05**: La Fase 6 no encuentra fuentes oficiales suficientes para una consulta normativa. Se marca como incertidumbre explicita y se pide revision humana en el Dreaming Report.
- **EC-06**: Memory consolidation encuentra sesiones corruptas o incompletas. Se saltan con log de error y se procesan las demas.

---

## Functional Requirements

### Dreaming mode - Orquestacion

- **FR-001**: El sistema MUST ejecutar Dreaming como proceso activable por cron configurable (default 3 AM timezone local) O por idle del usuario > 10 min (configurable). [MVP F5a para fases 1 y 5; roadmap para el resto]
- **FR-002**: Dreaming MUST ejecutar sus fases en orden secuencial (1 a 10); si una fase falla, MUST registrar el error y continuar con la siguiente.
- **FR-003**: Dreaming MUST pausarse al final de la fase actual si el usuario reanuda interaccion durante un ciclo idle-triggered.
- **FR-004**: Dreaming MUST registrar inicio, fin y resultado de cada fase en log estructurado JSONL en `~/.vigilador/audit/dreaming/<YYYY-MM-DD>.jsonl` (un archivo por dia, nombre = fecha ISO).

### Fase 1 - Memory consolidation [MVP F5a]

- **FR-005**: El sistema MUST recoger todas las sesiones del dia no consolidadas, comprimirlas (resumen + entidades clave + decisiones) y almacenarlas en memoria de largo plazo. La memoria consolidada se persiste como JSONL en `~/.vigilador/memory/consolidated.jsonl` (append-only, un registro JSON por sesion consolidada).
- **FR-006**: Las sesiones originales MUST marcarse como `consolidated = true` tras procesamiento exitoso, sin eliminarse (preservar raw data).
- **FR-007**: La consolidacion MUST ser idempotente: ejecutar dos veces sobre las mismas sesiones no genera duplicados en memoria de largo plazo.

### Fase 5 - Enterprise ingestion sync [MVP F5a]

- **FR-008**: El sistema MUST sincronizar incrementalmente documentos desde conectores configurados (Drive, OneDrive, local_fs), procesando solo documentos nuevos o modificados desde la ultima sincronizacion.
- **FR-009**: El sistema MUST registrar timestamp de ultima sincronizacion por conector para determinar delta en el proximo ciclo. El checkpoint se persiste en `~/.vigilador/memory/sync_checkpoints.jsonl` (un registro JSON por conector con campos `connector_id` y `last_sync_at` ISO 8601; se sobreescribe por conector en cada sync exitosa).
- **FR-010**: Si un conector falla, el sistema MUST continuar con los demas conectores y registrar el error para reintento en el proximo ciclo.

### Fase 2 - Skill curator [Roadmap F5b]

- **FR-011**: El sistema MUST revalidar skills aprendidos contra sus ejecuciones recientes (ultimos 30 dias).
- **FR-012**: Skills con tasa de fallo > 50% en las ultimas 5 ejecuciones MUST marcarse como `deprecated` y excluirse del discovery.
- **FR-013**: Skills promovidos a "estable" (5+ ejecuciones exitosas consecutivas) MUST dejar de requerir approval-gate.

### Fase 3 - Prompt self-improvement [Roadmap F5b]

- **FR-014**: El sistema MUST detectar prompts con 5+ feedbacks negativos en 7 dias y generar una variante mejorada usando el LLM.
- **FR-015**: La variante MUST entrar en A/B test (50% sesiones usan variante, 50% original) durante 20 sesiones o 7 dias (lo que ocurra primero).
- **FR-016**: Si la variante tiene mejor confianza de respuesta y menos feedbacks negativos, MUST promoverse a default via `AgentModifier`; si no, MUST descartarse.
- **FR-017**: Si la confianza de la variante cae mas de 10% respecto al original durante el A/B test, MUST revertirse inmediatamente.

### Fase 4 - Config refresher [Roadmap F5b]

- **FR-018**: El sistema MUST detectar gaps en COMPANY (preguntas que el agente no pudo responder por falta de informacion local) agrupados por categoria (organization/processes/systems).
- **FR-019**: Para cada gap detectado, MUST generar propuesta de parrafo o seccion a anadir al archivo correspondiente.
- **FR-020**: Propuestas a `identity.md` y `policies.md` MUST encolarse como `pending_approval` via `AgentModifier`; el resto se aplica directamente.
- **FR-021**: El agente MUST solo anadir o anotar como obsoleto; NUNCA eliminar contenido existente de archivos COMPANY.

### Loop 2 - Writing style learning [Roadmap F5b]

- **FR-022**: El sistema MUST analizar correos enviados/aprobados por el usuario para extraer estadisticas de tono, longitud, formalidad, vocativos, firma.
- **FR-023**: El resultado MUST actualizarse en `config/skills/learned/writing_style.yaml` via `AgentModifier`.
- **FR-024**: Si se detecta drift severo (cambio brusco vs baseline 30 dias), MUST flaggearse para revision humana sin bloquear la actualizacion.

### Fase 6 - Regulatory/local watch [Roadmap F5b]

- **FR-025**: El sistema MUST construir queries de busqueda basadas en `company_geo` (pais/departamento/municipio), sector de la empresa y modos activos.
- **FR-026**: El sistema MUST buscar fuentes oficiales vigentes (alcaldia, gobernacion, entidades nacionales, superintendencias) antes de generar cualquier resumen.
- **FR-027**: El sistema MUST comparar hallazgos contra lo guardado en `config/company/policies.md`, `processes.md` y evidencia indexada.
- **FR-028**: Si encuentra cambios relevantes, MUST generar propuesta con citas y fecha de consulta. Si no encuentra fuente oficial suficiente, MUST marcar incertidumbre explicita y pedir revision humana.
- **FR-029**: El sistema MUST NUNCA hardcodear valores tributarios o legales; toda informacion normativa MUST tener cita a fuente oficial.

### Fase 7 - Index maintenance [Roadmap F5b]

- **FR-030**: El sistema MUST ejecutar vacuum/compact sobre TurboVecIndex para eliminar vectores huerfanos y optimizar busqueda.
- **FR-031**: El sistema MUST registrar metricas pre/post mantenimiento (tamano indice, vectores activos, fragmentacion).

### Fase 9 - Admin repo maintenance [Roadmap F5b]

- **FR-032**: El sistema MUST revisar repos clonados de tools/MCPs contra upstream (releases, commits nuevos, CVEs).
- **FR-033**: El sistema MUST clasificar cada cambio detectado por impacto: patch, feature, breaking, security.
- **FR-034**: Para cambios tipo security o breaking, MUST generar propuesta admin con diff, changelog, riesgo y resultado de tests ejecutados en sandbox.
- **FR-035**: El sistema MUST NUNCA promover cambios a runtime estable sin aprobacion admin explicita.

### Fase 10 - Dreaming Report [Roadmap F5b]

- **FR-036**: Al finalizar cada ciclo Dreaming, el sistema MUST generar un reporte con: resumen ejecutivo, cambios aplicados (con links a rollback), pendientes de aprobacion, metricas del dia, salud del sistema.
- **FR-037**: El Dreaming Report MUST enviarse al canal preferido del usuario (configurado en settings).

### Loop de autoaprendizaje - Tool composition [Roadmap F5b]

- **FR-038**: El sistema MUST detectar secuencias de invocacion de tools repetidas 10+ veces en 30 dias.
- **FR-039**: Para cada secuencia detectada, MUST generar un skill compuesto que invoca esas tools en orden.
- **FR-040**: El skill compuesto MUST sugerirse al usuario en el Dreaming Report; si el usuario aprueba o si `mode_settings.intensity = AUTONOMOUS`, se crea via `AgentModifier`.
- **FR-041**: El sistema MUST NUNCA sobrescribir un skill existente; si hay conflicto de nombre, marca el anterior como `superseded`.

### Observabilidad

- **FR-042**: El sistema MUST emitir metricas Prometheus: `vigilador_dreaming_phase_duration_seconds{phase}`, `vigilador_dreaming_phase_status{phase, status}` (success/skipped/failed).
- **FR-043**: El sistema MUST emitir metricas: `vigilador_skill_learned_total{source}`, `vigilador_skill_curator_revalidated_total{result}`, `vigilador_regulatory_watch_total{geo, result}`, `vigilador_admin_repo_updates_detected_total{repo, impact}`.

---

## Key Entities

- **Dreaming cycle**: una ejecucion completa de las fases 1-10. Tiene timestamp de inicio/fin, fases ejecutadas y resultado por fase. Vive en JSONL de audit.
- **Consolidated memory**: resultado de comprimir sesiones del dia en entidades de largo plazo (resumen, entidades clave, decisiones). Vive en `~/.vigilador/memory/consolidated.jsonl` (append-only).
- **Ingestion sync checkpoint**: timestamp de ultima sincronizacion por conector. Vive en `~/.vigilador/memory/sync_checkpoints.jsonl`.
- **A/B test record**: registro de un test activo entre prompt original y variante, con metricas de confianza y feedback. Vive en metadata DB.
- **Admin proposal**: propuesta generada por Fase 9 con diff, impacto, tests y estado (pending/approved/rejected). Vive en metadata DB.
- **Dreaming Report**: documento generado al final de cada ciclo con resumen de actividad. Vive en filesystem y se envia al usuario.

---

## Success Criteria

- **SC-001**: Memory consolidation procesa el 100% de las sesiones del dia sin duplicados y en menos de 5 minutos para un dia tipico (50 sesiones). [MVP F5a]
- **SC-002**: Ingestion sync procesa solo documentos nuevos/modificados; re-ejecutar sin cambios en conectores resulta en 0 documentos procesados. [MVP F5a]
- **SC-003**: Un ciclo Dreaming completo (10 fases) finaliza en menos de 30 minutos para un tenant con 50 sesiones/dia, 500 documentos indexados y 20 tools registradas. [Roadmap F5b]
- **SC-004**: La Fase 6 (regulatory watch) genera propuestas con cita a fuente oficial en el 100% de los casos donde encuentra informacion; marca incertidumbre en el 100% de los casos donde no la encuentra. [Roadmap F5b]
- **SC-005**: La Fase 9 (admin repo maintenance) detecta el 100% de las nuevas releases de repos clonados y NUNCA promueve cambios sin aprobacion. [Roadmap F5b]
- **SC-006**: El A/B test de prompts (Fase 3) revierte automaticamente variantes que caen >10% en confianza, en menos de 24 horas desde la deteccion. [Roadmap F5b]
- **SC-007**: Dreaming se pausa correctamente cuando el usuario reanuda interaccion, sin corromper estado de la fase en curso. [MVP F5a]

---

## Traceability Matrix

| FR | Acceptance scenario | Success criterion | Fuente plan | Scope |
|----|---------------------|-------------------|-------------|-------|
| FR-001 | AS-1, AS-2 | SC-007 | 05 "Dreaming como motor" | MVP F5a |
| FR-002 | EC-01 | SC-003 | 05 fases secuenciales | MVP F5a |
| FR-003 | EC-02 | SC-007 | 05 idle trigger | MVP F5a |
| FR-004 | — | — | 05 audit | MVP F5a |
| FR-005 | AS-1 | SC-001 | 05 Fase 1 Memory consolidation | MVP F5a |
| FR-006 | AS-1 | SC-001 | 05 Fase 1 | MVP F5a |
| FR-007 | — | SC-001 | 05 idempotencia | MVP F5a |
| FR-008 | AS-2 | SC-002 | 05 Fase 5 Enterprise ingestion sync | MVP F5a |
| FR-009 | AS-2 | SC-002 | 05 sync incremental | MVP F5a |
| FR-010 | EC-03 | SC-002 | 05 resiliencia conectores | MVP F5a |
| FR-011 | AS-3 | SC-003 | 05 Loop 1 Skill learning / Fase 2 | Roadmap F5b |
| FR-012 | AS-3 | — | 05 Skill curator deprecation | Roadmap F5b |
| FR-013 | — | — | 05 Loop 1 promotion | Roadmap F5b |
| FR-014 | AS-4 | SC-006 | 05 Loop 3 Prompt self-improvement | Roadmap F5b |
| FR-015 | AS-4 | SC-006 | 05 A/B test | Roadmap F5b |
| FR-016 | AS-4 | SC-006 | 05 promotion | Roadmap F5b |
| FR-017 | — | SC-006 | 05 revert si cae >10% | Roadmap F5b |
| FR-018 | AS-5 | — | 05 Loop 5 COMPANY self-update | Roadmap F5b |
| FR-019 | AS-5 | — | 05 propuesta parrafo | Roadmap F5b |
| FR-020 | AS-5 | — | 05 approval identity/policies | Roadmap F5b |
| FR-021 | — | — | 05 "jamas elimina contenido" | Roadmap F5b |
| FR-022 | — | — | 05 Loop 2 Writing style | Roadmap F5b |
| FR-023 | — | — | 05 writing_style.yaml | Roadmap F5b |
| FR-024 | — | — | 05 drift detection | Roadmap F5b |
| FR-025 | AS-6 | SC-004 | 05 Loop 6 Regulatory watch | Roadmap F5b |
| FR-026 | AS-6 | SC-004 | 05 fuentes oficiales | Roadmap F5b |
| FR-027 | AS-6 | SC-004 | 05 comparacion | Roadmap F5b |
| FR-028 | AS-6, EC-05 | SC-004 | 05 propuesta con citas | Roadmap F5b |
| FR-029 | — | SC-004 | 05 "nunca hardcodea" | Roadmap F5b |
| FR-030 | — | SC-003 | 05 Fase 7 Index maintenance | Roadmap F5b |
| FR-031 | — | — | 05 metricas indice | Roadmap F5b |
| FR-032 | AS-7 | SC-005 | 05 Loop 7 Admin repo maintenance | Roadmap F5b |
| FR-033 | AS-7 | SC-005 | 05 clasificacion impacto | Roadmap F5b |
| FR-034 | AS-7, EC-04 | SC-005 | 05 propuesta admin | Roadmap F5b |
| FR-035 | AS-7 | SC-005 | 05 "no promueve sin aprobacion" | Roadmap F5b |
| FR-036 | AS-8 | SC-003 | 05 Dreaming Report | Roadmap F5b |
| FR-037 | AS-8 | — | 05 canal preferido | Roadmap F5b |
| FR-038 | — | — | 05 Loop 4 Tool composition | Roadmap F5b |
| FR-039 | — | — | 05 skill compuesto | Roadmap F5b |
| FR-040 | — | — | 05 sugerencia usuario | Roadmap F5b |
| FR-041 | — | — | 05 "nunca sobrescribe" | Roadmap F5b |
| FR-042 | — | SC-003 | 05 metricas Prometheus | Roadmap F5b |
| FR-043 | — | — | 05 metricas loops | Roadmap F5b |

---

## Delivery Constraints

- **Constitucion v1.2.0 -- Simplicidad obligatoria (#2)**: Dreaming es un orquestador secuencial de fases; no se introduce paralelismo ni DAGs complejos salvo que la duracion real lo exija.
- **Constitucion v1.2.0 -- Modularidad primero (#3)**: cada fase es un modulo independiente con interfaz clara (input: contexto del ciclo; output: resultado + metricas). El orquestador no conoce la logica interna de cada fase.
- **Constitucion v1.2.0 -- Manejo de errores estricto (#4)**: fallo en una fase no detiene el ciclo; se registra y se continua. Pero errores dentro de una fase se propagan con contexto, no se silencian.
- **Constitucion v1.2.0 -- Cambios quirurgicos (#5)**: este spec no modifica modulos del 2.0.
- **YAGNI**: las fases roadmap F5b se especifican aqui para completitud pero NO se implementan hasta que el MVP valide la arquitectura base.
- **DRY con spec 016**: este spec NO redefine el mecanismo de audit trail ni rollback; los loops invocan `AgentModifier` (spec 016) para registrar sus cambios.
- **SRP**: el Dreaming mode orquesta; cada loop/fase tiene su propio modulo con responsabilidad unica.

### Arquitectura: Fase vs Loop (delegacion)

- Una **fase** es una unidad de ejecucion del `DreamingOrchestrator` (un archivo Python, una clase que implementa `DreamingPhase`). El orquestador invoca `phase.execute(context)` secuencialmente.
- Un **loop** es un modulo de logica de autoaprendizaje (un archivo Python bajo `loops/`). Los loops NO son invocados directamente por el orquestador; son invocados por la fase que los orquesta (composicion).
- Relacion: una fase PUEDE delegar a uno o mas loops. Ejemplo: `Fase 3 (self_improvement.py)` invoca internamente `PromptSelfImprovementLoop`. La fase es la unidad de scheduling; el loop es la unidad de logica reutilizable.
- Interfaz de delegacion: cada loop expone `async def run(context: DreamingContext) -> LoopResult`. La fase lo instancia, invoca `run()`, y agrega el resultado a su `PhaseResult.metrics_dict`.

---

## Dependencies

- **spec 009-mvp-foundation**: infraestructura base (MigrationRunner + SQL crudo, HealthMonitor, ToolRegistry) debe existir.
- **spec 010 (F2 ingestion)**: conectores de ingestion deben existir para que Fase 5 funcione.
- **spec 016-audit-trail-y-rollback**: `AgentModifier` debe existir para que los loops de autoaprendizaje registren cambios (solo aplica a fases roadmap F5b).
- **spec 012 (F4a modos)**: `mode_settings` debe existir para configuracion de intensidad y approval por modo (solo aplica a fases roadmap F5b).
