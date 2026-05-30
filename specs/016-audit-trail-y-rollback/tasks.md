# Tasks: Audit Trail y Rollback

**Input**: `specs/016-audit-trail-y-rollback/spec.md`, `specs/016-audit-trail-y-rollback/plan.md`
**Feature**: F5b completo -- mecanismo de registro, persistencia, consulta y reversion de modificaciones autonomas del agente a archivos bajo `config/`. Incluye tabla SQL `agent_modifications`, replica JSONL, rollback sin cascada, approval-gate, CLI admin, vista web changelog y metricas Prometheus.

**Scope**: este spec completo es **roadmap F5b**. Se implementa despues de que el MVP (specs 009-013) valide la arquitectura base. El `AgentModifier` resultante es consumido por spec 017 (loops de autoaprendizaje) sin redefinirse alli (DRY).

**User Stories del spec**:
- **US1 (P1)**: Operador mantiene control sobre modificaciones autonomas del agente con audit trail completo, rollback y approval-gate.

**Testing strategy**: test-before-implementation por componente. Cada submodulo tiene tests unitarios antes de su implementacion. Tests de integracion verifican el flujo completo.

---

## Phase 1: Migracion y modelos base

Crear tabla SQL, modelos de dominio y verificar reversibilidad de la migracion.

- [x] T001 Verificar que `src/vigilancia_multiagente/enterprise/governance/__init__.py` existe como marker del subpaquete governance (ya creado)
- [ ] T002 [P] Crear `src/vigilancia_multiagente/enterprise/governance/models.py` con dataclasses: `ModificationRecord` (id, tenant_id, target_file, target_kind, diff, diff_summary, applied_at, rollback_token, agent_id, session_id, triggered_by, justification, status, reverted_at, reverted_by, superseded_by), `ModificationResult` (success, record, error), `RollbackResult` (success, previous_content, error), enum `TriggerKind` (dreaming_loop, skill_curator, config_refresher, regulatory_watch, admin_repo, manual), enum `ModificationStatus` (applied, pending_approval, reverted, superseded). Traza: FR-007, FR-010
- [ ] T003 Crear migración SQL cruda `src/vigilancia_multiagente/infra/db/migrations/008_audit_trail.sql` con DDL idempotente (`CREATE TABLE IF NOT EXISTS agent_modifications`): columnas id (UUID PK), tenant_id (UUID NOT NULL), target_file (TEXT NOT NULL), target_kind (TEXT NOT NULL), diff (TEXT NOT NULL), diff_summary (TEXT nullable), applied_at (TIMESTAMPTZ NOT NULL), rollback_token (TEXT NOT NULL UNIQUE), agent_id (TEXT NOT NULL), session_id (UUID nullable), triggered_by (TEXT NOT NULL), justification (TEXT nullable), status (TEXT NOT NULL DEFAULT 'applied'), reverted_at (TIMESTAMPTZ nullable), reverted_by (TEXT nullable), superseded_by (UUID FK nullable). Indices: (tenant_id, applied_at DESC), (target_file, applied_at DESC), (rollback_token). Reversibilidad = `DROP TABLE IF EXISTS agent_modifications CASCADE` (idempotente, sin downgrade). Traza: FR-007, FR-008, FR-009, FR-010
- [ ] T004 Test migracion: crear `tests/enterprise/migrations/test_008_audit_trail.py` con tests de idempotencia (aplicar `008_audit_trail.sql` 2 veces sin error) + verificación de aislamiento (tablas del 2.0 y de spec 009 quedan intactas tras DROP TABLE). Traza: SC-005
- [ ] T005 Ejecutar MigrationRunner para aplicar `008_audit_trail.sql` + verificar idempotencia (aplicar 2 veces) + ejecutar `DROP TABLE IF EXISTS agent_modifications CASCADE` y confirmar limpieza. Resultado verde de T004

**Independent Test Criteria for Phase 1**: migración aplica 2 veces sin error (idempotencia); `DROP TABLE` limpia sin afectar otras tablas; modelos importables sin errores de tipo; `basedpyright` sin nuevos errores en archivos creados.

---

## Phase 2: Core AgentModifier

Implementar los submodulos del core y el modulo orquestador `AgentModifier`.

### 2.1 -- Submodulos auxiliares

- [ ] T006 [P] Test `tests/enterprise/governance/test_atomic_writer.py`: 3 tests (escritura atomica crea archivo correcto; crash simulado no deja archivo corrupto; permisos del archivo resultante). Traza: FR-003
- [ ] T007 [P] Test `tests/enterprise/governance/test_diff_engine.py`: 3 tests (diff unificado correcto entre dos strings; diff vacio si contenido identico; generate_summary retorna null si LLM no disponible). Traza: FR-002, EC-05
- [ ] T008 [P] Test `tests/enterprise/governance/test_approval_gate.py`: 3 tests (policies.md requiere approval por default; archivo no listado no requiere approval; configuracion custom por modo respetada). Traza: FR-005, FR-014, SC-004
- [ ] T009 [P] Test `tests/enterprise/governance/test_superseded_chain.py`: 3 tests (primera modificacion queda applied; segunda marca la primera como superseded filtrando por mismo `target_file` + `tenant_id`; N modificaciones dejan N-1 superseded y 1 applied). Traza: FR-024, SC-006
- [ ] T010 [P] Test `tests/enterprise/governance/test_audit_persistence.py`: 4 tests (persist_to_db inserta registro correcto; persist_to_jsonl escribe linea valida; rotacion elimina archivos >30 dias; rotacion no elimina archivos recientes). Traza: FR-006, FR-017, FR-018, SC-001, SC-007
- [ ] T011 [P] Implementar `src/vigilancia_multiagente/enterprise/governance/atomic_writer.py`: funcion `write_atomically(path, content)` con write a `.tmp` + fsync + rename (~80 LOC). Hacer T006 verde. Traza: FR-003
- [ ] T012 [P] Implementar `src/vigilancia_multiagente/enterprise/governance/diff_engine.py`: funcion `compute_diff(old_content, new_content, filename) -> str` usando `difflib.unified_diff` + funcion `generate_summary(diff, llm_client) -> str | None` (~100 LOC). Hacer T007 verde. Traza: FR-002
- [ ] T013 [P] Implementar `src/vigilancia_multiagente/enterprise/governance/approval_gate.py`: funcion `requires_approval(target_file, mode_settings) -> bool` que consulta lista configurable (default incluye `config/company/policies.md`) (~80 LOC). Hacer T008 verde. Traza: FR-005, FR-014
- [ ] T014 [P] Implementar `src/vigilancia_multiagente/enterprise/governance/superseded_chain.py`: funcion `mark_superseded(tenant_id, target_file, new_id, db_session)` que actualiza entradas previas `applied` del mismo archivo y `tenant_id` (~60 LOC). Hacer T009 verde. Traza: FR-024
- [ ] T015 [P] Implementar `src/vigilancia_multiagente/enterprise/governance/audit_persistence.py`: clase `AuditPersistence` con metodos `persist_to_db(record, db_session)`, `persist_to_jsonl(record)`, `rotate_jsonl(max_days=30)` (~200 LOC). Hacer T010 verde. Traza: FR-006, FR-017, FR-018

### 2.2 -- Modulo central AgentModifier

- [ ] T016 Test `tests/enterprise/governance/test_agent_modifier.py`: 7 tests (propose_and_apply registra en DB + JSONL + escribe archivo; propose_and_apply con approval-gate deja pending sin escribir archivo; rollback revierte archivo y actualiza status; rollback falla si archivo modificado externamente; rollback falla si ya revertido; approve aplica cambio pendiente; list_pending_approvals retorna solo pendientes). Traza: FR-001..FR-006, FR-011..FR-016, SC-001..SC-004, SC-006
- [ ] T017 Implementar `src/vigilancia_multiagente/enterprise/governance/agent_modifier.py`: clase `AgentModifier` con metodos `propose_and_apply(tenant_id, target_file, new_content, agent_id, session_id, triggered_by, justification) -> ModificationResult`, `rollback(rollback_token, user_id) -> RollbackResult`, `approve(rollback_token, user_id) -> ModificationResult`, `list_pending_approvals(tenant_id) -> list[ModificationRecord]`. Orquesta atomic_writer, diff_engine, approval_gate, superseded_chain, audit_persistence (~300 LOC). Hacer T016 verde. Traza: FR-001..FR-006, FR-011..FR-016
- [ ] T018 Test de rollback con conflicto: `tests/enterprise/governance/test_rollback.py` con 4 tests dedicados (rollback exitoso; conflicto por edicion externa; rollback de superseded aplica diff inverso correcto; rollback de pending_approval rechaza). Traza: FR-011, FR-012, FR-013, SC-002, SC-003, EC-01, EC-02, EC-03
- [ ] T019 Wirear `AgentModifier` en `src/vigilancia_multiagente/api/dependencies.py` como singleton lazy. Solo lineas aditivas. Traza: FR-001

**Independent Test Criteria for Phase 2**: `pytest tests/enterprise/governance/` verde; propose_and_apply persiste en DB + JSONL con orden explícito y compensación (si falla un paso, rollback de los anteriores); rollback revierte correctamente; approval-gate bloquea policies.md; cadena superseded consistente (filtro por `target_file` + `tenant_id`).

---

## Phase 3: CLI admin

Implementar comandos Click para operaciones de audit trail.

- [ ] T020 Test `tests/enterprise/cli/test_audit_commands.py`: 5 tests con `CliRunner` (changelog lista modificaciones filtradas por fecha; show muestra diff completo; rollback ejecuta y confirma; pending-approvals lista pendientes; approve aplica cambio). Traza: FR-019..FR-023
- [ ] T021 Implementar `src/vigilancia_multiagente/cli/__init__.py` como marker del subpaquete CLI (si no existe)
- [ ] T022 Implementar `src/vigilancia_multiagente/cli/audit_commands.py`: grupo Click `audit` con subcomandos `changelog --since --tenant`, `show <token>`, `rollback <token>`, `pending-approvals`, `approve <token>` (~250 LOC). Hacer T020 verde. Traza: FR-019..FR-023, SC-002
- [ ] T023 Registrar entry point `vigilador-admin` en `pyproject.toml`: añadir dependencia `click>=8.1` y crear sección `[project.scripts]` con `vigilador-admin = "vigilancia_multiagente.cli:main"`. Traza: FR-019

**Independent Test Criteria for Phase 3**: `pytest tests/enterprise/cli/` verde; `vigilador-admin audit --help` muestra los 5 subcomandos; cada subcomando ejecuta la operacion correspondiente via AgentModifier.

---

## Phase 4: Observabilidad

Metricas Prometheus para el audit trail.

- [ ] T024 [P] Test `tests/enterprise/governance/test_metrics_audit.py`: 3 tests (counter modifications_total se incrementa en propose_and_apply; counter reverted_total se incrementa en rollback; gauge pending_approval refleja conteo correcto). Traza: FR-025, FR-026, FR-027
- [ ] T025 [P] Implementar `src/vigilancia_multiagente/enterprise/governance/metrics.py`: counters `vigilador_agent_modifications_total{target_kind, triggered_by, status}`, `vigilador_agent_modifications_reverted_total{target_kind, reason}`, gauge `vigilador_agent_modifications_pending_approval{tenant_id}` (~50 LOC). Traza: FR-025, FR-026, FR-027
- [ ] T026 Integrar emisiones de metricas en `agent_modifier.py`: llamadas a increment en propose_and_apply, rollback, approve. Hacer T024 verde. Traza: FR-025, FR-026, FR-027

**Independent Test Criteria for Phase 4**: metricas se emiten correctamente en cada operacion; `pytest tests/enterprise/governance/test_metrics_audit.py` verde.

---

## Phase 5: API REST y frontend

Endpoints REST para changelog y rollback desde frontend; vista web minima.

### 5.1 -- Backend API

- [ ] T027 [P] Test `tests/enterprise/api/test_audit_endpoints.py`: 5 tests (GET changelog retorna lista paginada; GET show retorna detalle con diff; POST rollback ejecuta y retorna resultado; GET pending retorna pendientes; POST approve aplica). Traza: FR-019..FR-023
- [ ] T028 Implementar `src/vigilancia_multiagente/api/routes/enterprise_audit.py` con endpoints: `GET /api/v2/enterprise/audit/changelog?since=&tenant=`, `GET /api/v2/enterprise/audit/{token}`, `POST /api/v2/enterprise/audit/rollback/{token}`, `GET /api/v2/enterprise/audit/pending`, `POST /api/v2/enterprise/audit/approve/{token}` (~150 LOC). Hacer T027 verde. Traza: FR-019..FR-023
- [ ] T029 Registrar router en `src/vigilancia_multiagente/api/app.py` bajo prefijo `/api/v2/enterprise/audit`. Solo linea aditiva

### 5.2 -- Frontend

- [ ] T030 [P] Crear `frontend/src/enterprise/api/auditClient.ts`: cliente HTTP para endpoints audit (getChangelog, getDetail, rollback, getPending, approve) (~50 LOC)
- [ ] T031 [P] Implementar `frontend/src/enterprise/admin/AuditChangelogPage.tsx`: tabla con columnas fecha, archivo, resumen, triggered_by, agent, status, boton revertir. Paginacion. Auto-refresh (~200 LOC). Traza: AS-7
- [ ] T032 [P] Implementar `frontend/src/enterprise/admin/RollbackModal.tsx`: modal con preview diff inverso + boton confirmar/cancelar (~100 LOC). Traza: AS-7
- [ ] T033 [P] Test Vitest `frontend/src/enterprise/admin/__tests__/audit-changelog.test.tsx`: render con datos mock, click revertir abre modal, confirmar ejecuta rollback. Traza: AS-7
- [ ] T034 Anadir rutas `/enterprise/admin/audit` en `frontend/src/App.tsx`. Solo linea aditiva

**Independent Test Criteria for Phase 5**: `pytest tests/enterprise/api/test_audit_endpoints.py` verde; frontend renderiza changelog y ejecuta rollback via modal; tests Vitest verdes.

---

## Phase 6: Verificacion integral

Validacion final, cero regresiones, SC verificados.

- [ ] T035 [P] Correr suite completa `pytest` y verificar 0 regresiones (2.0 + enterprise)
- [ ] T036 [P] Correr `scripts/check-layer-imports.py` y verificar 0 violaciones nuevas
- [ ] T037 [P] Correr `basedpyright src/vigilancia_multiagente/` y verificar 0 nuevos errores
- [ ] T038 [P] Correr `ruff check src/ tests/` + `ruff format src/ tests/` sin issues
- [ ] T039 [P] Correr tests frontend `npm test --prefix frontend` con cobertura en archivos nuevos
- [ ] T040 Verificar SC-001: ejecutar propose_and_apply 10 veces y confirmar 10 registros en DB + 10 lineas JSONL
- [ ] T041 Verificar SC-002: ejecutar rollback via CLI y medir tiempo < 2 segundos
- [ ] T042 Verificar SC-003: modificar archivo manualmente, intentar rollback, confirmar error de conflicto
- [ ] T043 Verificar SC-004: intentar modificar policies.md sin approval, confirmar que queda pending
- [ ] T044 Verificar SC-005: aplicar `008_audit_trail.sql` 2 veces (idempotencia), luego `DROP TABLE IF EXISTS agent_modifications CASCADE`, confirmar 0 residuos y tablas del 2.0 intactas
- [ ] T045 Verificar SC-006: aplicar 5 cambios al mismo archivo, confirmar 4 superseded + 1 applied
- [ ] T046 Verificar SC-007: crear JSONL con fecha >30 dias, ejecutar rotacion, confirmar eliminacion
- [ ] T047 Verificar EC-01..EC-06 con tests dedicados o ejecucion manual documentada

**Independent Test Criteria for Phase 6**: todos los SC pasan; todos los EC verificados; linters y typechecks sin issues nuevos; tests del 2.0 intactos.

---

## Dependencies

- **Phase 1 (Migracion y modelos)** must complete before **Phase 2 (Core AgentModifier)**.
- **Phase 2** must complete before **Phase 3 (CLI)**, **Phase 4 (Observabilidad)** y **Phase 5 (API/Frontend)**.
- **Phase 3, Phase 4 y Phase 5** son independientes entre si tras Phase 2.
- **Phase 6 (Verificacion)** requiere Phases 1-5 completas.
- Dentro de **Phase 2**:
  - T006..T010 (tests) son independientes entre si y se ejecutan antes de T011..T015 (implementaciones).
  - T011..T015 (submodulos) son independientes entre si (archivos distintos).
  - T016 (test AgentModifier) depende de T011..T015 (necesita submodulos).
  - T017 (implementar AgentModifier) depende de T016 (test-before-implementation).
  - T018 (test rollback dedicado) puede correr en paralelo con T016/T017 si se mockean dependencias, pero se recomienda secuencial tras T017.
  - T019 (wirear) depende de T017.
- **Dependencia externa**: spec 009 (migración `006_mvp_foundation.sql` aplicada via MigrationRunner + estructura enterprise/) debe estar completo.
- **Consumidores**: spec 017 (roadmap F5b) consume `AgentModifier` sin redefinirlo.

---

## Parallel Execution Examples

### Phase 1 Parallel Block

- T001 y T002 en paralelo (marker + modelos, archivos distintos).
- T003 secuencial tras T002 (migracion referencia modelos para validacion conceptual).
- T004 secuencial tras T003.

### Phase 2 -- Tests Parallel Block

- Run **T006, T007, T008, T009, T010** en paralelo (tests de submodulos distintos, sin dependencias entre si).

### Phase 2 -- Implementaciones Parallel Block

- Run **T011, T012, T013, T014, T015** en paralelo tras sus tests respectivos (archivos distintos sin dependencias).

### Phases 3, 4, 5 Parallel Block

Tras Phase 2 verde, distribuir:
- **Dev A -- CLI**: T020 -> T021 -> T022 -> T023.
- **Dev B -- Observabilidad**: T024 -> T025 -> T026.
- **Dev C -- API + Frontend**: T027 -> T028 -> T029, luego T030, T031, T032, T033 en paralelo, finalmente T034.

### Phase 6 Parallel Block

- Run **T035, T036, T037, T038, T039** en paralelo (linters/tests independientes).
- Luego **T040..T047** secuencial (verificaciones manuales/SC).

---

## Implementation Strategy

1. **Phase 1 primero**: migracion reversible + modelos. Gate: tabla existe y revierte limpiamente.
2. **Phase 2 como nucleo**: submodulos auxiliares en paralelo, luego AgentModifier como orquestador. Gate: propose_and_apply + rollback funcionales con persistencia dual.
3. **Phases 3, 4, 5 en paralelo**: CLI, metricas y API/frontend son capas de presentacion independientes que consumen el core. Distribuir entre desarrolladores.
4. **Phase 6 como gate final**: nada se considera entregado hasta que SC-001..SC-007 pasen y EC-01..EC-06 esten verificados.
5. **Coexistencia con MVP F5a**: spec 017 MVP (memory consolidation + ingestion sync) NO requiere este spec. Cuando F5b se active, los loops de spec 017 consumiran `AgentModifier` directamente.
6. **Rollback del deploy**: ejecutar `DROP TABLE IF EXISTS agent_modifications CASCADE` elimina la tabla; remover router de `app.py` restaura estado anterior. Cero impacto en el 2.0.
