# Feature Specification: Audit Trail y Rollback

**Feature ID**: 016-audit-trail-y-rollback
**Created**: 2026-05-29
**Status**: Draft (specification phase) -- Roadmap F5b (no entra en MVP segun 00b)
**Related plan documents**:
- [plan vigilador 3.0/05-autoaprendizaje-y-autonomia.md](../../plan%20vigilador%203.0/05-autoaprendizaje-y-autonomia.md)
- [plan vigilador 3.0/00b-mvp-scope-y-cronograma.md](../../plan%20vigilador%203.0/00b-mvp-scope-y-cronograma.md)
- [plan vigilador 3.0/00-canon-operativo-corregido.md](../../plan%20vigilador%203.0/00-canon-operativo-corregido.md)

---

## Problem Statement

La decision D4 del plan v3.0 otorga al agente autonomia completa para modificar configuracion del sistema (skills, tools, prompts, SOUL.md, COMPANY/*, templates, politicas, modos, playbooks). Sin un mecanismo de trazabilidad y reversion, el usuario pierde visibilidad sobre que cambio el agente, cuando, por que y como revertirlo. El audit trail con diff/timestamp/rollback resuelve este problema: cada modificacion queda registrada con evidencia suficiente para que el usuario revise, apruebe o revierta cualquier cambio con un click.

Este spec cubre exclusivamente el mecanismo de registro, persistencia, consulta y reversion de modificaciones autonomas del agente. NO cubre los loops de autoaprendizaje que generan esas modificaciones (spec 017), ni el Dreaming mode (spec 017), ni el frontend de admin (roadmap F5c segun 00b).

---

## Scope Boundaries

### Scope / MVP vs Roadmap

Segun `00b-mvp-scope-y-cronograma.md`:
- **MVP (F5a)**: audit trail basico operativo en JSONL (criterio de salida #9 del MVP). La tabla SQL `agent_modifications` y los 5 loops de autoaprendizaje son roadmap F5b.
- **Este spec**: cubre la implementacion completa (tabla SQL + JSONL + rollback + approvals residuales + CLI admin + UI changelog). Es **roadmap F5b**. La porcion JSONL basica que el MVP necesita es un subconjunto minimo que se puede entregar antes sin la tabla SQL.

### In Scope

- Tabla `agent_modifications` en PostgreSQL con schema completo (diff, timestamp, rollback_token, agent_id, session_id, triggered_by, justification, status, superseded_by).
- Replica JSONL diaria en `~/.vigilador/audit/agent_mods/<fecha>.jsonl` con rotacion a 30 dias.
- Modulo `AgentModifier` como unico punto de entrada para modificaciones del agente a archivos de configuracion.
- Escritura atomica de archivos (write-tmp + fsync + rename).
- Generacion de diff unificado y resumen LLM de 1-2 lineas por cambio.
- Rollback de un cambio especifico por `rollback_token` (sin cascada).
- Approval-gate para `config/company/policies.md` (status `pending_approval` hasta confirmacion humana).
- Approval-gate configurable por Modo via `mode_settings.audit.approval_required_for_files`.
- CLI admin: `vigilador-admin audit changelog`, `show`, `rollback`, `pending-approvals`, `approve`.
- Vista web `/admin/audit/changelog` con tabla de cambios y boton revertir.
- Migración SQL cruda `src/vigilancia_multiagente/infra/db/migrations/008_audit_trail.sql` aplicada por MigrationRunner para crear tabla `agent_modifications` con indices.
- Metricas Prometheus: `vigilador_agent_modifications_total`, `vigilador_agent_modifications_reverted_total`, `vigilador_agent_modifications_pending_approval`.

### Out of Scope

- Los 5+ loops de autoaprendizaje que generan modificaciones (spec 017 y roadmap F5b).
- Dreaming mode y sus fases (spec 017).
- AnomalyDetector completo (spec de gobernanza/seguridad, roadmap).
- Capability tokens (spec de gobernanza/seguridad, roadmap).
- Frontend completo de admin (roadmap F5c segun 00b; este spec define solo la vista changelog minima).
- Indexacion empresarial, memory consolidation, normativa localizada (spec 017).
- Mantenimiento admin de repos tools/MCPs (spec 017).

---

## Assumptions

- **A-01**: La metadata DB PostgreSQL existente soporta la extension `uuidv7()` o se usa un generador equivalente en la capa de aplicacion.
- **A-02**: El filesystem local (`~/.vigilador/audit/`) es accesible con permisos de escritura por el proceso del agente.
- **A-03**: Los archivos de configuracion modificables por el agente viven bajo `config/` en el repositorio y son archivos de texto (YAML, Markdown, JSON). Paths/globs aceptados por `AgentModifier`: `config/settings.yaml`, `config/company/**/*.md`, `config/skills/**/*.yaml`, `config/modes/**/*.yaml`, `config/playbooks/**/*.yaml`, `config/templates/**/*`, `config/mcp/**/*.yaml`, `config/prompt_overrides/**/*`, `config/workstream_overrides.json`.
- **A-04**: El LLM activo (Xiaomimimo u otro) esta disponible para generar `diff_summary` de 1-2 lineas; si no esta disponible, el campo queda null sin bloquear la operacion.
- **A-05**: El usuario accede al CLI admin desde la misma maquina donde corre el agente (acceso local a la DB y al filesystem).
- **A-06**: La migración de este spec (`008_audit_trail.sql`) depende de que `006_mvp_foundation.sql` esté aplicada (MigrationRunner ejecuta en orden secuencial).

---

## User Scenarios & Testing

### Primary User Story

Como **operador del Vigilador 3.0**, quiero que cada modificacion autonoma del agente a mis archivos de configuracion quede registrada con diff completo, justificacion y un mecanismo de reversion inmediata, para mantener control sobre mi sistema sin sacrificar la autonomia del agente.

### Acceptance Scenarios

1. **Given** el agente modifica `config/soul.md` via `AgentModifier`, **When** consulto la tabla `agent_modifications`, **Then** existe una entrada con `target_file = "config/soul.md"`, `diff` no vacio, `rollback_token` unico, `status = "applied"` y `applied_at` con timestamp UTC.

2. **Given** una entrada en `agent_modifications` con status `applied`, **When** ejecuto `vigilador-admin audit rollback <rollback_token>`, **Then** el archivo vuelve al contenido anterior al cambio, el status pasa a `reverted`, `reverted_at` se llena y `reverted_by` registra el user_id.

3. **Given** el agente intenta modificar `config/company/policies.md`, **When** `AgentModifier.propose_and_apply()` se ejecuta, **Then** el cambio NO se aplica al archivo, el status queda `pending_approval` y aparece en `vigilador-admin audit pending-approvals`.

4. **Given** un cambio en status `pending_approval`, **When** el usuario ejecuta `vigilador-admin audit approve <rollback_token>`, **Then** el cambio se aplica al archivo, el status pasa a `applied` y se registra `applied_at`.

5. **Given** el agente modifica el mismo archivo 3 veces en un dia, **When** consulto el changelog, **Then** las dos primeras entradas tienen `status = "superseded"` con `superseded_by` apuntando a la siguiente, y solo la tercera tiene `status = "applied"`.

6. **Given** una modificacion aplicada, **When** reviso `~/.vigilador/audit/agent_mods/<fecha>.jsonl`, **Then** existe una linea JSON con los mismos campos clave (id, target_file, diff, rollback_token, applied_at).

7. **Given** la vista web `/admin/audit/changelog` abierta, **When** hago click en `[Revertir]` junto a un cambio, **Then** se muestra modal con preview del diff inverso y tras confirmar se ejecuta el rollback.

### Edge Cases

- **EC-01**: Rollback de un cambio ya revertido retorna error explicito "ya revertido" sin modificar el archivo.
- **EC-02**: Rollback de un cambio `superseded` aplica el diff inverso de ese cambio especifico; no revierte los cambios posteriores (sin cascada).
- **EC-03**: Si el archivo fue modificado manualmente por el usuario despues del cambio del agente, el rollback detecta conflicto (contenido actual != contenido post-cambio esperado) y falla con error explicito sin corromper el archivo.
- **EC-04**: Si la DB no esta disponible al momento de persistir el audit, el cambio al archivo NO se aplica (atomicidad: audit y archivo van juntos o ninguno).
- **EC-05**: Si el LLM no esta disponible para generar `diff_summary`, la modificacion se aplica igual con `diff_summary = null`.
- **EC-06**: Rotacion JSONL: archivos con mas de 30 dias se eliminan automaticamente en el siguiente ciclo de escritura.

---

## Functional Requirements

### Modulo AgentModifier

- **FR-001**: El sistema MUST proveer un modulo `AgentModifier` como unico punto de entrada para que cualquier componente del agente modifique archivos bajo `config/`.
- **FR-002**: `AgentModifier.propose_and_apply()` MUST generar un diff unificado entre el contenido actual y el nuevo contenido antes de aplicar cualquier cambio.
- **FR-003**: `AgentModifier` MUST escribir archivos de forma atomica (write a `.tmp`, fsync, rename) para prevenir corrupcion por crash mid-write.
- **FR-004**: `AgentModifier` MUST generar un `rollback_token` unico por cada modificacion, utilizable para revertir ese cambio especifico.
- **FR-005**: `AgentModifier` MUST rechazar la aplicacion directa de cambios a archivos listados en `mode_settings.audit.approval_required_for_files` (default: `config/company/policies.md`), encolandolos como `pending_approval`.
- **FR-006**: `AgentModifier` MUST persistir la entrada de audit siguiendo un orden explícito con compensación: 1) commit en tabla `agent_modifications`, 2) escritura en JSONL del día, 3) escritura atómica del archivo destino. Si el paso 3 falla, se marca el registro DB como `failed` (compensación); si el paso 2 falla, se hace rollback del commit DB. El cambio al archivo no se aplica si algún paso previo falla.

### Tabla agent_modifications

- **FR-007**: La migracion MUST crear la tabla `agent_modifications` con columnas: `id` (UUID PK), `tenant_id` (UUID NOT NULL), `target_file` (TEXT NOT NULL), `target_kind` (TEXT NOT NULL), `diff` (TEXT NOT NULL), `diff_summary` (TEXT nullable), `applied_at` (TIMESTAMPTZ NOT NULL), `rollback_token` (TEXT NOT NULL UNIQUE), `agent_id` (TEXT NOT NULL), `session_id` (UUID nullable), `triggered_by` (TEXT NOT NULL), `justification` (TEXT nullable), `status` (TEXT NOT NULL DEFAULT 'applied'), `reverted_at` (TIMESTAMPTZ nullable), `reverted_by` (TEXT nullable), `superseded_by` (UUID FK nullable).
- **FR-008**: La migracion MUST crear indices sobre: `(tenant_id, applied_at DESC)`, `(target_file, applied_at DESC)`, `(rollback_token)`.
- **FR-009**: La migración MUST ser reversible mediante script idempotente `DROP TABLE IF EXISTS agent_modifications CASCADE` que elimina la tabla y sus indices sin afectar otras tablas. No existe downgrade automático (MigrationRunner es forward-only).
- **FR-010**: El campo `status` MUST aceptar solo los valores: `applied`, `pending_approval`, `reverted`, `superseded`.

### Rollback

- **FR-011**: `AgentModifier.rollback(rollback_token, user_id)` MUST revertir el archivo al estado anterior aplicando el diff inverso, actualizar `status` a `reverted`, llenar `reverted_at` y `reverted_by`.
- **FR-012**: El rollback MUST fallar con error explicito si el contenido actual del archivo no coincide con el estado post-cambio esperado (deteccion de conflicto).
- **FR-013**: El rollback MUST ser una operacion sin cascada: solo revierte el cambio identificado por el token, sin afectar cambios posteriores al mismo archivo.

### Approval gate

- **FR-014**: Cambios con status `pending_approval` MUST NO aplicarse al archivo hasta que el usuario ejecute `approve`.
- **FR-015**: `AgentModifier.approve(rollback_token, user_id)` MUST aplicar el cambio al archivo y actualizar status a `applied`.
- **FR-016**: `AgentModifier.list_pending_approvals(tenant_id)` MUST retornar todos los cambios pendientes ordenados por `applied_at` descendente.

### Replica JSONL

- **FR-017**: Cada modificacion registrada MUST escribirse tambien como una linea JSON en `~/.vigilador/audit/agent_mods/<YYYY-MM-DD>.jsonl` con campos: id, tenant_id, target_file, triggered_by, diff, diff_summary, applied_at, rollback_token.
- **FR-018**: Archivos JSONL con mas de 30 dias MUST eliminarse automaticamente en el siguiente ciclo de escritura.

### CLI admin

- **FR-019**: El comando `vigilador-admin audit changelog --since <date> --tenant <uuid>` MUST listar modificaciones desde la fecha indicada, mostrando: fecha, archivo, resumen, triggered_by, agent, status.
- **FR-020**: El comando `vigilador-admin audit show <rollback_token>` MUST mostrar el diff completo del cambio.
- **FR-021**: El comando `vigilador-admin audit rollback <rollback_token>` MUST ejecutar el rollback y confirmar resultado.
- **FR-022**: El comando `vigilador-admin audit pending-approvals` MUST listar cambios pendientes de aprobacion.
- **FR-023**: El comando `vigilador-admin audit approve <rollback_token>` MUST aprobar y aplicar un cambio pendiente.

### Superseded chain

- **FR-024**: Cuando el agente modifica un archivo que ya tiene una entrada `applied` previa para el mismo `target_file` y `tenant_id`, la entrada previa MUST actualizarse a `status = "superseded"` con `superseded_by` apuntando al nuevo id.

### Observabilidad

- **FR-025**: El sistema MUST emitir metricas Prometheus: `vigilador_agent_modifications_total{target_kind, triggered_by, status}` incrementada por cada modificacion.
- **FR-026**: El sistema MUST emitir metrica `vigilador_agent_modifications_reverted_total{target_kind, reason}` incrementada por cada rollback exitoso.
- **FR-027**: El sistema MUST emitir gauge `vigilador_agent_modifications_pending_approval{tenant_id}` con el conteo actual de pendientes.

---

## Key Entities

- **Agent modification record (`agent_modifications`)**: registro completo de una modificacion autonoma del agente. Incluye diff, justificacion, token de rollback y cadena de superseded. Vive en PostgreSQL.
- **JSONL audit line**: replica ligera de cada modificacion para consulta rapida sin DB. Vive en filesystem local con rotacion 30 dias.
- **Rollback token**: identificador unico que permite revertir un cambio especifico. Generado por `AgentModifier`, entregado al usuario en reportes y UI.
- **AgentModifier**: modulo central que orquesta la logica de proponer, validar, aplicar, persistir y revertir modificaciones.

---

## Success Criteria

- **SC-001**: El 100% de las modificaciones autonomas del agente a archivos bajo `config/` quedan registradas en `agent_modifications` Y en JSONL sin excepciones.
- **SC-002**: Un rollback ejecutado via CLI o UI revierte el archivo al estado anterior en menos de 2 segundos.
- **SC-003**: La deteccion de conflicto en rollback (archivo modificado externamente) funciona correctamente en el 100% de los casos de prueba.
- **SC-004**: Cambios a `policies.md` NUNCA se aplican sin aprobacion explicita del usuario (0% de bypass en tests).
- **SC-005**: La migración es idempotente: aplicar `008_audit_trail.sql` dos veces consecutivas no produce error ni duplica objetos. La reversibilidad se verifica ejecutando `DROP TABLE IF EXISTS agent_modifications CASCADE` sin afectar otras tablas.
- **SC-006**: La cadena `superseded` se mantiene consistente: para un archivo con N modificaciones, exactamente N-1 tienen status `superseded` y 1 tiene status `applied` (o `reverted` si se revirtio la ultima).
- **SC-007**: La rotacion JSONL elimina archivos de mas de 30 dias sin afectar archivos recientes.
- **SC-008**: Los 5 comandos CLI (`changelog`, `show`, `rollback`, `pending-approvals`, `approve`) ejecutan correctamente y retornan salida coherente en el 100% de los casos de prueba.
- **SC-009**: Las métricas Prometheus (`vigilador_agent_modifications_total`, `vigilador_agent_modifications_reverted_total`, `vigilador_agent_modifications_pending_approval`) se incrementan/actualizan correctamente tras cada operación correspondiente.

---

## Traceability Matrix

| FR | Acceptance scenario | Success criterion | Fuente plan |
|----|---------------------|-------------------|-------------|
| FR-001 | AS-1 | SC-001 | 05 seccion "Arquitectura del audit trail" |
| FR-002 | AS-1 | SC-001 | 05 seccion "Implementacion AgentModifier" |
| FR-003 | EC-04 | SC-002 | 05 guardrail `_write_file_atomically` |
| FR-004 | AS-1, AS-2 | SC-002 | 05 seccion "rollback_token" |
| FR-005 | AS-3 | SC-004 | 05 decision D4 excepcion policies.md |
| FR-006 | AS-6, EC-04 | SC-001 | 05 seccion "Replica JSONL diaria" |
| FR-007 | AS-1 | SC-005 | 05 tabla `agent_modifications` SQL |
| FR-008 | — | SC-005 | 05 indices SQL |
| FR-009 | — | SC-005 | 05 migracion |
| FR-010 | AS-5 | SC-006 | 05 constraint valid_status |
| FR-011 | AS-2 | SC-002 | 05 seccion "UI de rollback" |
| FR-012 | EC-03 | SC-003 | 05 guardrails internos |
| FR-013 | EC-02 | SC-002 | 05 "Sin cascada" |
| FR-014 | AS-3 | SC-004 | 05 decision D4 approval-gate |
| FR-015 | AS-4 | SC-004 | 05 CLI admin approve |
| FR-016 | AS-3 | SC-004 | 05 list_pending_approvals |
| FR-017 | AS-6 | SC-001 | 05 seccion "Replica JSONL diaria" |
| FR-018 | EC-06 | SC-007 | 05 "rotacion a 30 dias" |
| FR-019 | AS-7 | SC-008 | 05 CLI admin fallback |
| FR-020 | AS-7 | SC-008 | 05 CLI admin show |
| FR-021 | AS-2 | SC-002, SC-008 | 05 CLI admin rollback |
| FR-022 | AS-3 | SC-008 | 05 CLI admin pending-approvals |
| FR-023 | AS-4 | SC-004, SC-008 | 05 CLI admin approve |
| FR-024 | AS-5 | SC-006 | 05 "superseded_by mantiene la cadena" |
| FR-025 | — | SC-001, SC-009 | 05 metricas Prometheus |
| FR-026 | — | SC-009 | 05 metricas Prometheus |
| FR-027 | — | SC-004, SC-009 | 05 metricas Prometheus |

---

## Delivery Constraints

- **Constitucion v1.2.0 -- Simplicidad obligatoria (#2)**: `AgentModifier` es un unico modulo con responsabilidad clara; no se introducen abstracciones adicionales (factories, strategies) salvo que la complejidad real lo exija.
- **Constitucion v1.2.0 -- Modularidad primero (#3)**: el modulo de audit trail no mezcla logica de orquestacion con persistencia; la escritura a DB y a JSONL son operaciones separadas invocadas secuencialmente.
- **Constitucion v1.2.0 -- Manejo de errores estricto (#4)**: errores de escritura a DB o filesystem se propagan con contexto; no se silencian.
- **Constitucion v1.2.0 -- Cambios quirurgicos (#5)**: este spec no modifica tablas ni modulos del 2.0.
- **CQS**: `AgentModifier` separa queries (list_pending_approvals, changelog) de commands (propose_and_apply, rollback, approve).
- **DRY con spec 017**: este spec NO define los loops de autoaprendizaje ni las fases de Dreaming; solo provee el mecanismo que ellos consumen.

---

## Dependencies

- **spec 009-mvp-foundation**: la migración `006_mvp_foundation.sql` debe estar aplicada (MigrationRunner) y la estructura `enterprise/` debe existir antes de aplicar la migración de este spec.
- **spec 017-admin-maintenance-dreaming**: consume `AgentModifier` para registrar cambios generados por los loops de autoaprendizaje y Dreaming.
