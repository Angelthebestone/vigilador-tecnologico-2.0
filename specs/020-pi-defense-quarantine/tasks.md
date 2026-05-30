# Tasks: PI Defense y Cuarentena

**Input**: `specs/020-pi-defense-quarantine/spec.md`, `specs/020-pi-defense-quarantine/plan.md`
**Feature**: F5a del MVP — defensa contra prompt injection por regex + dataset Lakera + tool-gating reforzado con cuarentena automatica de inputs sospechosos.

**User Stories del spec**:
- **US1 (P1)**: Operador del Vigilador 3.0 quiere que el sistema intercepte y cuarentene automaticamente contenido externo con patrones de prompt injection, para que un documento malicioso no pueda secuestrar al agente.
  *Unico user story de este spec; cubre los 7 acceptance scenarios y los 19 FRs.*

**Testing strategy**: test-before-implementation por componente. Cada fase produce tests primero y luego implementacion que los hace pasar. SC-001..SC-007 verificados con evidencia en Phase 7.

---

## Phase 1: Validacion y setup

Cero codigo de producto. Solo verificacion de dependencias y entorno.

- [ ] T001 Verificar que `src/vigilancia_multiagente/enterprise/governance/__init__.py` existe (creado por spec 009) en `src/vigilancia_multiagente/enterprise/governance/`
- [ ] T002 [P] Verificar que MigrationRunner aplicó 006_mvp_foundation.sql: confirmar que tabla `schema_migrations` contiene registro de 006 y la metadata DB responde
- [ ] T003 [P] Verificar que `prometheus-client` esta instalado y `/metrics` responde (spec 009 operativo)
- [ ] T004 [P] Verificar que `ToolRegistry.list_tools_for_role` existe y sus tests pasan: `pytest tests/enterprise/tooling/test_tool_registry.py`
- [ ] T005 Verificar disponibilidad del dataset Lakera open-source (fuente: https://github.com/lakeraai/pint-benchmark o equivalente): descargar o confirmar formato esperado (`config/security/lakera-patterns.json`). Validar licencia compatible (A-01). **Plan B**: si licencia incompatible, operar solo con heurísticas regex (FR-002). Documentar resultado en comentario de commit
- [ ] T006 [P] Verificar que tests del 2.0 siguen pasando: `pytest` sin regresiones

**Independent Test Criteria for Phase 1**: MigrationRunner operativo con 006 aplicada (schema_migrations); `/metrics` responde; `ToolRegistry` funcional; dataset Lakera disponible y con licencia compatible; tests del 2.0 al 100%.

---

## Phase 2: Detector PI + DetectionResult

Modulo de deteccion puro sin dependencias de persistencia ni API.

- [ ] T007 [P] [US1] Crear `src/vigilancia_multiagente/enterprise/governance/detection_result.py` con dataclass frozen `DetectionResult`: `is_suspicious: bool`, `patterns_matched: list[str]`, `severity: Literal["LOW", "MEDIUM", "HIGH"]`, `confidence: float`, `source: str`. ~30 LOC. Traza: FR-004
- [ ] T008 [P] [US1] Crear `config/security/lakera-patterns.json` con array de objetos `{"pattern": "<regex>", "category": "<string>", "severity_weight": <int>}` basado en dataset Lakera open-source. **Nota**: requiere crear directorio `config/security/` previamente (no existe aún en el repo). Traza: FR-003
- [ ] T009 [US1] Test `tests/enterprise/governance/test_prompt_injection_detector.py`: corpus de 50 payloads conocidos con 100% deteccion (SC-001); corpus de 200 documentos empresariales tipicos con < 2% falsos positivos (SC-002); latencia < 50 ms para input de 10KB (SC-003); input sin patrones retorna `is_suspicious=false`; archivo Lakera faltante opera solo con regex y emite warning (EC-05); input > 100KB procesado en chunks (EC-02); multiples patrones registrados con severity = max (EC-03). Traza: FR-001, FR-002, FR-004, FR-005
- [ ] T010 [US1] Implementar `src/vigilancia_multiagente/enterprise/governance/prompt_injection_detector.py`: clase `PromptInjectionDetector` con constructor que carga patrones regex hardcoded (FR-002: ingles + espanol) y dataset Lakera desde archivo local (FR-003). Metodo `detect(content: str, source: str) -> DetectionResult` (FR-004). Severidad segun FR-005. Chunks para inputs > 100KB (EC-02). ~200 LOC. Hacer T009 verde. Traza: FR-001..FR-005, SC-001..SC-003

**Independent Test Criteria for Phase 2**: `pytest tests/enterprise/governance/test_prompt_injection_detector.py` verde; 50 payloads detectados al 100%; < 2% falsos positivos sobre 200 docs; latencia < 50 ms p95 para 10KB.

---

## Phase 3: Migracion + Repository

Persistencia de cuarentena en metadata DB.

- [ ] T011 [US1] Crear migración SQL cruda `src/vigilancia_multiagente/infra/db/migrations/010_pi_quarantine.sql`: tabla `pi_quarantine(id UUID PK, tenant_id UUID NOT NULL, source VARCHAR, content_excerpt TEXT, detected_patterns JSONB, severity VARCHAR, quarantined_at TIMESTAMP NOT NULL, approved_at TIMESTAMP NULL, approved_by VARCHAR NULL)`. Indices por `tenant_id` y `quarantined_at DESC`. DDL idempotente (`CREATE TABLE IF NOT EXISTS`). Reversibilidad: `DROP TABLE IF EXISTS pi_quarantine`. ~60 LOC. Traza: FR-009, FR-018, FR-019
- [ ] T012 [US1] Test migración `tests/enterprise/migrations/test_010_pi_quarantine.py`: aplicar `010_pi_quarantine.sql` via MigrationRunner 2 veces consecutivas sin error (idempotencia); tablas existentes del 2.0 y spec 009 intactas tras aplicación. Traza: SC-006
- [ ] T013 [US1] Test repository `tests/enterprise/governance/test_pi_quarantine_repository.py`: insert + query + approve roundtrip; aislamiento por `tenant_id`; `list_pending` retorna solo registros sin `approved_at`; `approve` actualiza `approved_at` y `approved_by`. Traza: FR-009..FR-012
- [ ] T014 [US1] Implementar `src/vigilancia_multiagente/enterprise/governance/pi_quarantine_repository.py`: clase `PIQuarantineRepository` con metodos async `quarantine(tenant_id, source, content_excerpt, detected_patterns, severity) -> UUID`, `list_pending(tenant_id) -> list[QuarantineRecord]`, `approve(id, approved_by) -> None`, `get_by_id(id) -> QuarantineRecord | None`. Reinyección al pipeline (FR-012): exponer callable `on_quarantine_released(content, source)` que los conectores de spec 010 suscribirán cuando existan. ~100 LOC. Hacer T012 y T013 verdes. Traza: FR-009..FR-012, FR-018, FR-019, SC-006

**Independent Test Criteria for Phase 3**: migración idempotente (2 aplicaciones sin error); repository CRUD funcional; tablas previas intactas.

---

## Phase 4: Interceptor + Audit + Metrica

Orquestacion: hook de intercepcion que conecta detector con cuarentena, audit y observabilidad.

- [ ] T015 [US1] Test `tests/enterprise/governance/test_pi_interceptor.py`: input malicioso bloqueado + registro en cuarentena + audit JSONL escrito + metrica incrementada; input limpio pasa sin bloqueo ni escrituras; `content_excerpt` truncado a 500 chars (FR-010); contenido cuarentenado NO accesible por agente (SC-004); metrica refleja conteo real (SC-005). Traza: FR-006..FR-008, FR-010, FR-013..FR-015
- [ ] T016 [US1] Modificar `src/vigilancia_multiagente/enterprise/observability/metrics.py`: anadir counter `vigilador_pi_quarantined_total` con labels `source`, `severity`. Cambio aditivo ~5 LOC. Traza: FR-015
- [ ] T017 [US1] Implementar `src/vigilancia_multiagente/enterprise/governance/pi_interceptor.py`: clase `PIInterceptor` con dependencias inyectadas (`PromptInjectionDetector`, `PIQuarantineRepository`). Metodo `intercept(content: str, source: str, tenant_id: UUID) -> InterceptionResult`. Si `is_suspicious`: persiste en cuarentena, escribe audit JSONL a `~/.vigilador/audit/pi_quarantine_<fecha>.jsonl` (FR-014), incrementa metrica (FR-015), retorna `blocked=True`. Si limpio: retorna `blocked=False, content=content`. ~80 LOC. Hacer T015 verde. Traza: FR-006..FR-008, FR-010, FR-013..FR-015, SC-004, SC-005
- [ ] T017b [US1] Fallback FR-013: verificar que el interceptor emite evento/log estructurado (audit JSONL + métrica) que el frontend consumirá cuando spec 013 esté listo. FR-013 se satisface con este mecanismo hasta integración frontend. Traza: FR-013

**Independent Test Criteria for Phase 4**: `pytest tests/enterprise/governance/test_pi_interceptor.py` verde; audit JSONL generado correctamente; metrica Prometheus incrementada; input malicioso nunca pasa al LLM.

---

## Phase 5: Tool-gating verificación

Verificación de que el gating existente en `_passes_gating()` cumple FR-016/FR-017. NO se modifica `tool_registry.py` (constitución #5).

- [ ] T018 [US1] Test `tests/enterprise/governance/test_tool_gating_credentials.py`: 10 tools (5 con API key configurada, 5 sin key); `list_tools_for_role` retorna solo las 5 con key (SC-007); tool con `requires_auth: false` siempre aparece; cambio de entorno (key anadida) refleja inmediatamente en siguiente query. Traza: FR-016, FR-017
- [ ] T019 [US1] VERIFICAR que `_passes_gating()` en `enterprise/tooling/tool_registry.py` cumple FR-016/FR-017: excluye tools con `requires_auth: true` sin API key configurada; opera como query pura sin side-effects (CQS). Hacer T018 verde sin modificar `tool_registry.py`. Traza: FR-016, FR-017, SC-007

**Independent Test Criteria for Phase 5**: `pytest tests/enterprise/governance/test_tool_gating_credentials.py` verde; 100% de tools sin credencial excluidas; query pura sin side-effects; `tool_registry.py` sin cambios.

---

## Phase 6: Endpoint API cuarentena

Superficie API para consumo frontend (spec 013).

- [ ] T020 [US1] Test `tests/enterprise/api/test_quarantine_endpoints.py`: GET `/api/v2/enterprise/quarantine` lista registros pendientes; GET `/api/v2/enterprise/quarantine/{id}` retorna detalle; POST `/api/v2/enterprise/quarantine/{id}/approve` actualiza `approved_at` y `approved_by`; intento de aprobacion sin autenticacion falla con 401; agente no puede auto-aprobar (FR-011). Traza: FR-011, FR-012, FR-013
- [ ] T021 [US1] Implementar `src/vigilancia_multiagente/api/routes/enterprise_quarantine.py`: endpoints `GET /api/v2/enterprise/quarantine`, `GET /api/v2/enterprise/quarantine/{id}`, `POST /api/v2/enterprise/quarantine/{id}/approve`. Solo usuario humano autenticado puede aprobar (FR-011). Al aprobar: reinyecta contenido al pipeline (FR-012). ~120 LOC. Hacer T020 verde. Traza: FR-011..FR-013
- [ ] T022 [US1] Registrar router en `src/vigilancia_multiagente/api/app.py`. Cambio aditivo ~2 LOC. Traza: FR-013
- [ ] T023 [US1] Wirear `PIInterceptor` y `PIQuarantineRepository` en `src/vigilancia_multiagente/api/dependencies.py`. Cambio aditivo ~10 LOC. Traza: FR-006

**Independent Test Criteria for Phase 6**: `pytest tests/enterprise/api/test_quarantine_endpoints.py` verde; endpoints responden correctamente; aprobacion requiere autenticacion humana.

---

## Phase 7: Integracion E2E + cierre

Verificacion cruzada de todos los SC y cero regresiones.

- [ ] T024 [US1] Test E2E `tests/enterprise/governance/test_pi_e2e.py`: flujo completo input malicioso -> detector -> interceptor -> cuarentena -> NO llega al LLM -> usuario aprueba via endpoint -> reinyeccion al pipeline. Traza: SC-004, FR-008, FR-011, FR-012
- [ ] T025 [US1] Test E2E: 100 documentos limpios indexados -> cero cuarentenas (AS-4). Traza: SC-002
- [ ] T026 [P] Verificar que tests del 2.0 siguen pasando al 100%: `pytest` sin regresiones
- [ ] T027 [P] Verificar `scripts/check-layer-imports.py` sin violaciones nuevas
- [ ] T028 [P] Verificar que MigrationRunner aplica `010_pi_quarantine.sql` idempotentemente sobre el stack completo de migraciones (001..006 + 010). Traza: SC-006
- [ ] T029 Verificar SC-001..SC-007 con evidencia documentada; persistir resultados en comentario de commit o `docs/`

**Independent Test Criteria for Phase 7**: todos los SC-001..SC-007 verificados con evidencia; tests del 2.0 al 100%; cero violaciones de capas; migración idempotente en stack completo.

---

## Dependencies

- **Phase 1 (Validacion)** must complete before **Phase 2 (Detector)**.
- **Phase 2 (Detector)** must complete before **Phase 4 (Interceptor)** — el interceptor depende del detector.
- **Phase 3 (Migracion + Repository)** must complete before **Phase 4 (Interceptor)** — el interceptor depende del repository.
- **Phase 2 y Phase 3** son independientes entre si y pueden ejecutarse en paralelo.
- **Phase 4 (Interceptor)** must complete before **Phase 6 (Endpoint API)** — los endpoints usan el interceptor y repository.
- **Phase 5 (Tool-gating)** es independiente de Phases 3, 4 y 6. Puede ejecutarse en paralelo con Phase 3 o Phase 4. Solo verifica código existente, no modifica archivos.
- **Phases 4, 5 y 6** must complete before **Phase 7 (E2E)**.
- Dentro de cada fase: test antes de implementacion (T009->T010, T012/T013->T014, T015->T017, T018->T019, T020->T021).
- **T016** (metrica) puede ejecutarse en paralelo con T015 (test interceptor) ya que son archivos distintos.
- **T022** y **T023** (app.py, dependencies.py) requieren T021 completado.

## Parallel Execution Examples

### Phase 2 + Phase 3 Parallel Block

Tras Phase 1 verde, distribuir:

- **Dev A — Detector**: T007 -> T008 -> T009 -> T010.
- **Dev B — Migracion/Repository**: T011 -> T012 -> T013 -> T014.

### Phase 4 + Phase 5 Parallel Block

Tras Phases 2 y 3 verdes:

- **Dev A — Interceptor**: T015 -> T016 -> T017 -> T017b.
- **Dev B — Tool-gating verificación**: T018 -> T019.

### Phase 7 Parallel Block

- Run **T026, T027, T028** en paralelo (verificaciones independientes).

---

## Implementation Strategy

1. **Cerrar Phase 1 (Validacion) primero**: confirmar entorno, dependencias de spec 009 operativas y dataset Lakera disponible. Esto da go/no-go al spec 020.
2. **Phases 2 y 3 en paralelo**: el detector (logica pura) y la migracion/repository (persistencia) no tienen dependencia entre si. Distribuir entre desarrolladores.
3. **Phase 4 como punto de convergencia**: el interceptor une detector + repository + audit + metrica. Requiere Phases 2 y 3 completas.
4. **Phase 5 independiente**: el tool-gating es un cambio aditivo aislado en `tool_registry.py`. Puede ejecutarse en cualquier momento tras Phase 1.
5. **Phase 6 tras Phase 4**: los endpoints API consumen el interceptor y repository ya validados.
6. **Phase 7 como gate final**: nada se considera entregado hasta que SC-001..SC-007 esten verificados con evidencia y tests del 2.0 pasen al 100%.
7. **Scope MVP estricto**: PI defense con embeddings, anomaly detector, SSO/SAML, DR y capability tokens son roadmap post-MVP. No se implementan ni se preparan con stubs en este spec.

---

## Format Validation

Todas las tareas T001..T029 siguen el formato requerido:
- Checkbox `- [ ]` al inicio.
- Task ID secuencial (T001..T029).
- Marcador `[P]` solo en tareas paralelizables (diferentes archivos sin dependencias entre si).
- Label `[US1]` en todas las tareas de Phases 2-7 (single user story); sin label en Phase 1 (validacion).
- Descripcion con accion + path concreto del archivo.
- Traza a FR/SC donde aplica.

**Total task count**: 29 tareas.
**Task count per phase**:
- Phase 1 (Validacion): 6
- Phase 2 (Detector): 4
- Phase 3 (Migracion + Repository): 4
- Phase 4 (Interceptor + Audit + Metrica): 3
- Phase 5 (Tool-gating): 2
- Phase 6 (Endpoint API): 4
- Phase 7 (E2E + cierre): 6
