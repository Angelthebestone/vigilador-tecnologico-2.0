# Implementation Plan: Audit Trail y Rollback

**Feature ID**: 016-audit-trail-y-rollback
**Created**: 2026-05-29
**Spec**: [spec.md](spec.md)

## Problem

La decision D4 del plan v3.0 otorga al agente autonomia completa para modificar configuracion del sistema (skills, tools, prompts, SOUL.md, COMPANY/*, templates, politicas, modos, playbooks). Sin un mecanismo de trazabilidad y reversion, el usuario pierde visibilidad sobre que cambio el agente, cuando, por que y como revertirlo. Actualmente no existe ningun modulo que registre, persista ni permita revertir modificaciones autonomas del agente a archivos bajo `config/`.

Este plan cubre exclusivamente el mecanismo de registro, persistencia, consulta y reversion. NO cubre los loops de autoaprendizaje ni Dreaming (spec 017). Segun `00b-mvp-scope-y-cronograma.md`, este spec es **roadmap F5b** en su totalidad (tabla SQL + rollback + approvals + CLI admin + UI changelog). La porcion JSONL basica que el MVP F5a necesita es un subconjunto minimo entregado por spec 017 como dependencia inversa ligera.

## Approach

Implementar un modulo `AgentModifier` como unico punto de entrada para modificaciones del agente a archivos bajo `config/`. El modulo orquesta: generacion de diff unificado, escritura atomica de archivos, persistencia con orden explícito y compensación en tabla PostgreSQL `agent_modifications` y replica JSONL diaria, approval-gate configurable, y rollback sin cascada. Se expone via CLI admin y vista web minima. La migración SQL cruda (`008_audit_trail.sql`) es forward-only (MigrationRunner) y depende de que `006_mvp_foundation.sql` esté aplicada.

**Scope MVP vs Roadmap**: este spec completo es roadmap F5b. Se implementa despues de que el MVP valide la arquitectura base (spec 009 + spec 017 F5a). El plan se estructura en fases secuenciales verificables que pueden entregarse incrementalmente una vez se active F5b.

---

## Technical Context

| Area | Decision |
|------|----------|
| Lenguaje | Python 3.11+ (mismo que 2.0 y enterprise/) |
| Persistencia | PostgreSQL existente, tabla `agent_modifications` via migración SQL cruda `008_audit_trail.sql` + MigrationRunner |
| Replica local | JSONL en `~/.vigilador/audit/agent_mods/<YYYY-MM-DD>.jsonl`, rotacion 30 dias |
| Escritura archivos | Atomica: write `.tmp` + fsync + rename |
| Diff | `difflib.unified_diff` de stdlib |
| Resumen LLM | Opcional (1-2 lineas via LLM activo); si no disponible, `diff_summary = null` |
| Rollback token | UUID v4 con prefijo `rt_` para identificacion rapida |
| CLI admin | Click (`click>=8.1`, a añadir en pyproject.toml) bajo entry point `vigilador-admin` (sección `[project.scripts]` a crear) |
| Observabilidad | Prometheus counters/gauges via `prometheus-client` (ya instalado por spec 009) |
| Frontend | Vista minima `/admin/audit/changelog` en React bajo `frontend/src/enterprise/admin/` |

## External Constraints

| Constraint | Impact |
|------------|--------|
| Constitucion v1.2.0 #5 Cambios quirurgicos | Cero modificaciones a modulos del 2.0. Solo archivos nuevos bajo `enterprise/` y migración SQL en `infra/db/migrations/`. |
| Dependencia spec 009 | Migración `006_mvp_foundation.sql` debe estar aplicada (MigrationRunner) y estructura `enterprise/` debe existir antes. |
| DRY con spec 017 | Este plan NO define loops de autoaprendizaje ni fases de Dreaming. Solo provee el mecanismo que ellos consumen. |
| Scope roadmap F5b | No se implementa hasta que MVP valide arquitectura base. |
| Archivos <= 400 LOC | Cada modulo nuevo respeta el limite. `AgentModifier` se divide en core + persistence + cli. |

---

## Files to Create / Modify

### New Files

| File | Purpose |
|------|---------|
| `src/vigilancia_multiagente/enterprise/governance/__init__.py` | Marker subpaquete governance |
| `src/vigilancia_multiagente/enterprise/governance/agent_modifier.py` | Modulo central: propose_and_apply, rollback, approve, list_pending (~300 LOC) |
| `src/vigilancia_multiagente/enterprise/governance/audit_persistence.py` | Persistencia a tabla SQL + replica JSONL (~200 LOC). Separado de logica de dominio (SRP). |
| `src/vigilancia_multiagente/enterprise/governance/atomic_writer.py` | Escritura atomica de archivos: write-tmp + fsync + rename (~80 LOC) |
| `src/vigilancia_multiagente/enterprise/governance/diff_engine.py` | Generacion de diff unificado + resumen LLM opcional (~100 LOC) |
| `src/vigilancia_multiagente/enterprise/governance/approval_gate.py` | Logica de approval-gate configurable por modo (~80 LOC) |
| `src/vigilancia_multiagente/enterprise/governance/superseded_chain.py` | Logica de cadena superseded al modificar mismo archivo (~60 LOC) |
| `src/vigilancia_multiagente/enterprise/governance/models.py` | Dataclasses: ModificationRecord, ModificationResult, RollbackResult (~80 LOC) |
| `src/vigilancia_multiagente/enterprise/governance/metrics.py` | Prometheus counters/gauges del audit trail (~50 LOC) |
| `src/vigilancia_multiagente/infra/db/migrations/008_audit_trail.sql` | Migración SQL cruda: tabla `agent_modifications` + indices. Forward-only (MigrationRunner). |
| `src/vigilancia_multiagente/cli/__init__.py` | Marker subpaquete CLI (si no existe) |
| `src/vigilancia_multiagente/cli/audit_commands.py` | Comandos Click: changelog, show, rollback, pending-approvals, approve (~250 LOC) |
| `src/vigilancia_multiagente/api/routes/enterprise_audit.py` | Endpoints REST para changelog + rollback desde frontend (~150 LOC) |
| `frontend/src/enterprise/admin/AuditChangelogPage.tsx` | Vista web tabla de cambios + boton revertir (~200 LOC) |
| `frontend/src/enterprise/admin/RollbackModal.tsx` | Modal confirmacion con preview diff inverso (~100 LOC) |
| `frontend/src/enterprise/api/auditClient.ts` | Cliente HTTP para endpoints audit (~50 LOC) |
| `tests/enterprise/governance/test_agent_modifier.py` | Tests unitarios del modulo core |
| `tests/enterprise/governance/test_audit_persistence.py` | Tests de persistencia SQL + JSONL |
| `tests/enterprise/governance/test_rollback.py` | Tests de rollback + deteccion conflicto |
| `tests/enterprise/governance/test_approval_gate.py` | Tests de approval-gate |
| `tests/enterprise/governance/test_superseded_chain.py` | Tests de cadena superseded |
| `tests/enterprise/migrations/test_008_audit_trail.py` | Tests de migración: idempotencia (aplicar 2 veces sin error) + aislamiento de tablas del 2.0 |
| `tests/enterprise/cli/test_audit_commands.py` | Tests del CLI admin |

### Modified Files

| File | Changes |
|------|---------|
| `src/vigilancia_multiagente/api/app.py` | Registrar router `enterprise_audit`. Solo linea aditiva. |
| `src/vigilancia_multiagente/api/dependencies.py` | Wirear `AgentModifier` como singleton. Solo lineas aditivas. |
| `pyproject.toml` | Añadir dependencia `click>=8.1`, crear sección `[project.scripts]` con entry point `vigilador-admin`. |

---

## Constitution Check (Pre-Design)

- **Gate result**: PASS
- **Alignment**:
  - **Pensar Antes de Codificar**: Supuestos A-01..A-06 del spec declarados explicitamente. Dependencia secuencial con spec 009 documentada. Scope roadmap F5b declarado en Approach.
  - **Simplicidad Obligatoria**: `AgentModifier` es un modulo con responsabilidad clara. Sin factories ni strategies. La division en submodulos (persistence, atomic_writer, diff_engine, approval_gate) responde a SRP real, no a abstraccion especulativa.
  - **Modularidad Primero**: Cada archivo tiene un unico concern. Persistencia separada de logica de dominio. CLI separado de core. Frontend separado de backend.
  - **Cambios Quirurgicos y Trazables**: Solo 3 archivos existentes modificados, todos en modo aditivo (registrar router, wirear dependency, añadir entry point + dependencia click). Migración via MigrationRunner + SQL crudo (forward-only), sin Alembic.
  - **Entrega Verificable**: Cada fase produce artefactos verificables con tests. SC del spec mapeados a fases.
- **Diseno de Software**: SRP (cada modulo un concern), SoC (governance no mezcla con persistence ni CLI), DIP (AgentModifier depende de abstracciones de persistence, no de implementacion concreta), CQS (list_pending_approvals es query pura; propose_and_apply/rollback son commands), DRY (no redefine loops de spec 017), KISS (diff con stdlib, no libreria externa).

---

## Phases

### Phase 1 -- Migracion y modelos (2 dias)

1. Crear `enterprise/governance/models.py` con dataclasses: `ModificationRecord`, `ModificationResult`, `RollbackResult`, `TriggerKind` (enum).
2. Crear `src/vigilancia_multiagente/infra/db/migrations/008_audit_trail.sql` con tabla `agent_modifications` segun FR-007/FR-008/FR-009/FR-010. DDL idempotente (`CREATE TABLE IF NOT EXISTS`).
3. Verificar migración: aplicar `008_audit_trail.sql` dos veces sin error (idempotencia) + verificar que `DROP TABLE IF EXISTS agent_modifications CASCADE` limpia sin afectar otras tablas.
4. Crear `tests/enterprise/migrations/test_008_audit_trail.py`.

**Output**: tabla creada e idempotente, modelos definidos, tests verdes. Traza: FR-007, FR-008, FR-009, FR-010, SC-005.

### Phase 2 -- Core AgentModifier (3 dias)

1. Crear `enterprise/governance/atomic_writer.py`: funcion `write_atomically(path, content)` con write-tmp + fsync + rename.
2. Crear `enterprise/governance/diff_engine.py`: funcion `compute_diff(old, new) -> str` (unified diff) + `generate_summary(diff, llm_client) -> str | None`.
3. Crear `enterprise/governance/approval_gate.py`: funcion `requires_approval(target_file, mode_settings) -> bool`.
4. Crear `enterprise/governance/superseded_chain.py`: funcion `mark_superseded(tenant_id, target_file, new_id, db_session)`.
5. Crear `enterprise/governance/audit_persistence.py`: clase `AuditPersistence` con metodos `persist_to_db(record)`, `persist_to_jsonl(record)`, `rotate_jsonl(max_days=30)`.
6. Crear `enterprise/governance/agent_modifier.py`: clase `AgentModifier` con `propose_and_apply()`, `rollback()`, `approve()`, `list_pending_approvals()`. Orquesta los submodulos anteriores.
7. Tests unitarios para cada submodulo + integracion del `AgentModifier`.

**Output**: `AgentModifier` funcional con persistencia dual (SQL + JSONL), escritura atomica, approval-gate, cadena superseded. Traza: FR-001..FR-006, FR-011..FR-018, FR-024, SC-001..SC-004, SC-006, SC-007.

### Phase 3 -- CLI admin (2 dias)

1. Crear `cli/audit_commands.py` con grupo Click `audit` y subcomandos: `changelog`, `show`, `rollback`, `pending-approvals`, `approve`.
2. Registrar entry point `vigilador-admin` en `pyproject.toml`.
3. Tests del CLI con `CliRunner` de Click.

**Output**: CLI operativo para las 5 operaciones de audit. Traza: FR-019..FR-023, SC-002.

### Phase 4 -- Observabilidad (1 dia)

1. Crear `enterprise/governance/metrics.py` con counters Prometheus: `vigilador_agent_modifications_total`, `vigilador_agent_modifications_reverted_total`, gauge `vigilador_agent_modifications_pending_approval`.
2. Integrar emisiones en `AgentModifier` (llamadas a increment en propose_and_apply, rollback, approve).
3. Tests que verifican incremento de metricas.

**Output**: metricas Prometheus emitidas por cada operacion. Traza: FR-025, FR-026, FR-027.

### Phase 5 -- API REST y frontend (3 dias)

1. Crear `api/routes/enterprise_audit.py` con endpoints: `GET /api/v2/enterprise/audit/changelog`, `GET /api/v2/enterprise/audit/{token}`, `POST /api/v2/enterprise/audit/rollback/{token}`, `GET /api/v2/enterprise/audit/pending`, `POST /api/v2/enterprise/audit/approve/{token}`.
2. Registrar router en `app.py`.
3. Crear `frontend/src/enterprise/admin/AuditChangelogPage.tsx`: tabla con columnas fecha, archivo, resumen, triggered_by, agent, status, boton revertir.
4. Crear `frontend/src/enterprise/admin/RollbackModal.tsx`: modal con preview diff inverso + confirmacion.
5. Crear `frontend/src/enterprise/api/auditClient.ts`.
6. Tests backend (endpoints) + tests frontend (Vitest).

**Output**: vista web funcional con changelog y rollback de un click. Traza: FR-019..FR-023 (via REST), SC-002.

### Phase 6 -- Verificacion integral (1 dia)

1. Correr toda la bateria `pytest` y verificar 0 regresiones en el 2.0.
2. Verificar SC-001..SC-009 del spec con evidencia.
3. Verificar edge cases EC-01..EC-06 con tests dedicados.
4. Verificar `scripts/check-layer-imports.py` sin violaciones.

**Output**: spec 016 completado, listo para que spec 017 (roadmap F5b) consuma `AgentModifier`.

---

## Rollout Strategy

**Scope**: este spec completo es roadmap F5b. No se implementa hasta que el MVP (specs 009-013) valide la arquitectura base.

**Estrategia incremental**:
- Phase 1-2 se entregan primero: `AgentModifier` operativo sin UI.
- Phase 3 habilita operacion via CLI para testing interno.
- Phase 4-5 completan la experiencia de usuario.
- Cada fase es independientemente verificable.

**Backward compatibility**: cero cambios al 2.0. La tabla `agent_modifications` es nueva. El CLI `vigilador-admin` es un entry point nuevo. Las rutas frontend viven bajo `/enterprise/admin/*`.

**Coexistencia con MVP F5a**: spec 017 (MVP F5a) implementa Dreaming basico (memory consolidation + ingestion sync) sin necesitar `AgentModifier` porque esas fases no modifican archivos de config. Cuando F5b se active, los loops de autoaprendizaje de spec 017 consumiran `AgentModifier` de este spec.

**Rollback del deploy**: ejecutar `DROP TABLE IF EXISTS agent_modifications CASCADE` elimina la tabla sin afectar otras tablas. Remover routers de `app.py` restaura el estado anterior.

---

## Success Criteria

- **SC-001**: El 100% de las modificaciones autonomas del agente a archivos bajo `config/` quedan registradas en `agent_modifications` Y en JSONL sin excepciones.
- **SC-002**: Un rollback ejecutado via CLI o UI revierte el archivo al estado anterior en menos de 2 segundos.
- **SC-003**: La deteccion de conflicto en rollback (archivo modificado externamente) funciona correctamente en el 100% de los casos de prueba.
- **SC-004**: Cambios a `policies.md` NUNCA se aplican sin aprobacion explicita del usuario (0% de bypass en tests).
- **SC-005**: La migración es idempotente: aplicar `008_audit_trail.sql` dos veces consecutivas no produce error ni duplica objetos. La reversibilidad se verifica ejecutando `DROP TABLE IF EXISTS agent_modifications CASCADE` sin afectar otras tablas.
- **SC-006**: La cadena `superseded` se mantiene consistente: para un archivo con N modificaciones, exactamente N-1 tienen status `superseded` y 1 tiene status `applied`.
- **SC-007**: La rotacion JSONL elimina archivos de mas de 30 dias sin afectar archivos recientes.
- **SC-008**: Los 5 comandos CLI (`changelog`, `show`, `rollback`, `pending-approvals`, `approve`) ejecutan correctamente y retornan salida coherente en el 100% de los casos de prueba.
- **SC-009**: Las métricas Prometheus (`vigilador_agent_modifications_total`, `vigilador_agent_modifications_reverted_total`, `vigilador_agent_modifications_pending_approval`) se incrementan/actualizan correctamente tras cada operación correspondiente.

## Constitution Check (Post-Design)

- **Status**: PASS
- **Justification**:
  - **Pensar Antes de Codificar**: scope roadmap F5b declarado explicitamente. Dependencias con spec 009 y spec 017 documentadas. Supuestos del spec preservados.
  - **Simplicidad Obligatoria**: 9 archivos funcionales nuevos en backend, cada uno con responsabilidad unica y <= 300 LOC. Sin abstracciones especulativas. Sin factories ni strategies.
  - **Modularidad Primero**: governance/ contiene 7 modulos con interfaces claras. CLI, API y frontend son capas separadas que consumen el core sin conocer su implementacion interna.
  - **Cambios Quirurgicos y Trazables**: 3 archivos existentes modificados en modo aditivo. Cero refactors laterales. Migración via MigrationRunner + SQL crudo (forward-only), sin Alembic. Cada archivo nuevo traza a FRs del spec.
  - **Entrega Verificable**: 6 fases con output verificable. 7 SC medibles. Tests por fase. Edge cases cubiertos.
  - **Diseno de Software**: SRP (un modulo = un concern), SoC (dominio/persistencia/presentacion separados), DIP (AgentModifier depende de abstracciones), CQS (queries vs commands separados), DRY (no duplica logica de spec 017), KISS (stdlib para diff, Click para CLI), YAGNI (no implementa AnomalyDetector ni capability tokens -- esos son specs separados).
