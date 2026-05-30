# Implementation Plan: PI Defense y Cuarentena

**Feature ID**: 020-pi-defense-quarantine
**Created**: 2026-05-29
**Spec**: [spec.md](spec.md)

## Problem

El Vigilador 3.0 indexa contenido externo (correos, PDFs, paginas scrapeadas, documentos de Drive) y lo pasa como contexto al LLM. Sin una capa de defensa previa, un atacante puede inyectar instrucciones maliciosas dentro de ese contenido para secuestrar al agente: exfiltrar datos, ejecutar tools no autorizadas o modificar configuracion sin consentimiento del usuario.

Hoy el repo tiene:

- `enterprise/governance/` con solo `__init__.py` (vacio).
- `enterprise/tooling/tool_registry.py` con `list_tools_for_role` operativo (spec 009) con filtro por credencial faltante ya implementado en `_passes_gating()`.
- Cero detector de prompt injection.
- Cero tabla `pi_quarantine` en la metadata DB.
- Cero mecanismo de intercepcion pre-LLM para inputs externos.

Este plan describe como construir la primera linea de defensa: deteccion por patrones regex + dataset Lakera con cuarentena automatica, mas el refuerzo del tool-gating como segunda barrera.

## Approach

Implementar un modulo `prompt_injection_detector.py` en `enterprise/governance/` que detecte prompt injection mediante heuristicas regex (ingles/espanol) y patrones del dataset Lakera cargados desde archivo local al boot. Crear un hook de intercepcion (`pi_interceptor.py`) desacoplado de los conectores de ingestion que todo pipeline invoca antes de pasar contenido al LLM. Persistir inputs sospechosos en tabla `pi_quarantine` via migración SQL cruda (`010_pi_quarantine.sql`) ejecutada por MigrationRunner. Exponer metrica Prometheus y audit log JSONL. Verificar que el tool-gating existente en `ToolRegistry._passes_gating()` ya cumple FR-016/FR-017 (excluye tools sin credencial). Crear endpoint API para listar cuarentena y aprobar/liberar inputs (solo usuario humano).

**Scope MVP vs Roadmap**: segun `00b-mvp-scope-y-cronograma.md` fase F5a, este plan implementa SOLO PI defense por regex + dataset Lakera + tool-gating reforzado. Quedan explicitamente fuera del MVP (roadmap F5b+/F5d):

- PI defense con embedding comparison (similarity > 0.85).
- Anomaly detector (`anomaly_detector.py`).
- SSO/SAML/OIDC.
- Disaster Recovery automatizado.
- Capability tokens granulares con scope/TTL.

---

## Technical Context

| Area | Decision |
|------|----------|
| Detector PI | Regex heuristicas + dataset Lakera estatico. Sin ML, sin embeddings, sin modelos adicionales (constitucion #2 simplicidad). |
| Interfaz detector | `detect(content: str, source: str) -> DetectionResult`. Objeto de valor inmutable. |
| Hook intercepcion | Middleware invocable desde cualquier conector sin acoplamiento directo. Patron Strategy/DIP. |
| Persistencia cuarentena | Tabla `pi_quarantine` en PostgreSQL via migración SQL cruda `src/vigilancia_multiagente/infra/db/migrations/010_pi_quarantine.sql` ejecutada por MigrationRunner (forward-only). Multi-tenancy con `tenant_id`. |
| Audit | JSONL en `~/.vigilador/audit/pi_quarantine_<fecha>.jsonl`. Misma infraestructura que spec 009. |
| Metrica | `vigilador_pi_quarantined_total{source, severity}` via `prometheus-client` (ya instalado spec 009). |
| Tool-gating | Ya implementado en `ToolRegistry._passes_gating()`. Solo se verifica cumplimiento de FR-016/FR-017. Query pura (CQS). |
| Dataset Lakera | Archivo local `config/security/lakera-patterns.json`. Cargado al boot sin llamadas de red. |
| Aprobacion | Solo usuario humano via endpoint API. Agente no puede auto-aprobar. |
| LOC estimado | Detector ~200 LOC, interceptor ~80 LOC, migracion ~60 LOC, repository ~100 LOC, endpoint ~120 LOC. Total ~560 LOC en 5 archivos (todos <= 200 LOC individual). Tool-gating: 0 LOC (ya implementado). |

## External Constraints

| Constraint | Impact |
|------------|--------|
| Constitucion #2 Simplicidad | Solo regex + dataset estatico. Cero ML, cero embeddings para deteccion en MVP. |
| Constitucion #5 Cambios quirurgicos | Solo se extiende `enterprise/governance/` y observabilidad. `tool_registry.py` NO se modifica (gating ya implementado). Cero cambios al 2.0. |
| C0 #10 <= 400 LOC por archivo | Cada archivo nuevo se mantiene bajo 200 LOC. |
| Spec 009 completado | `ToolRegistry`, `HealthMonitor`, MigrationRunner, `/metrics`, audit JSONL ya operativos. Se extienden, no se reimplementan. |
| Spec 010 (ingestion) | Provee conectores donde se inserta el hook PI. Si no esta completado, el hook se registra como callable y se integra cuando los conectores existan. |
| Spec 013 (frontend) | Provee superficie para alertas de cuarentena. Si no esta completado, la alerta se emite solo via audit log y metrica; el endpoint API queda listo para consumo frontend. |
| Single-tenant MVP | `tenant_id` constante `00000000-0000-0000-0000-000000000001`. |
| Dataset Lakera licencia | A-01: se asume licencia compatible. Validar en Phase 1. |
| Idiomas cubiertos | Solo ingles y espanol en MVP. Otros idiomas pasan sin deteccion (limitacion documentada). |

---

## Files to Create / Modify

### New Files

| File | Purpose |
|------|---------|
| `src/vigilancia_multiagente/enterprise/governance/prompt_injection_detector.py` | Detector PI con heuristicas regex + patrones Lakera. Interfaz `detect()`. ~200 LOC. |
| `src/vigilancia_multiagente/enterprise/governance/pi_interceptor.py` | Hook de intercepcion desacoplado. Invoca detector, deriva a cuarentena si positivo. ~80 LOC. |
| `src/vigilancia_multiagente/enterprise/governance/pi_quarantine_repository.py` | Repository para tabla `pi_quarantine`. CRUD + query por tenant. ~100 LOC. |
| `src/vigilancia_multiagente/enterprise/governance/detection_result.py` | Dataclass `DetectionResult` (valor inmutable). ~30 LOC. |
| `src/vigilancia_multiagente/api/routes/enterprise_quarantine.py` | Endpoints: `GET /api/v2/enterprise/quarantine`, `POST /api/v2/enterprise/quarantine/{id}/approve`. ~120 LOC. |
| `src/vigilancia_multiagente/infra/db/migrations/010_pi_quarantine.sql` | Migración SQL cruda: crea tabla `pi_quarantine` con indices. DDL idempotente. ~60 LOC. |
| `config/security/lakera-patterns.json` | Dataset de patrones Lakera en formato JSON local. |
| `tests/enterprise/governance/test_prompt_injection_detector.py` | Tests unitarios del detector: 50 payloads conocidos + 200 docs limpios. |
| `tests/enterprise/governance/test_pi_interceptor.py` | Tests del hook: bloqueo, cuarentena, bypass de contenido limpio. |
| `tests/enterprise/governance/test_pi_quarantine_repository.py` | Tests del repository: CRUD + aprobacion. |
| `tests/enterprise/governance/test_tool_gating_credentials.py` | Tests del filtro por credencial en `list_tools_for_role`. |
| `tests/enterprise/api/test_quarantine_endpoints.py` | Tests de los endpoints de cuarentena. |
| `tests/enterprise/migrations/test_010_pi_quarantine.py` | Idempotencia (aplicar 2 veces sin error) + verificación de aislamiento de tablas del 2.0. |

### Modified Files

| File | Changes |
|------|---------|
| `src/vigilancia_multiagente/enterprise/observability/metrics.py` | Anadir counter `vigilador_pi_quarantined_total` con labels `source`, `severity`. ~5 LOC. |
| `src/vigilancia_multiagente/api/app.py` | Registrar router `enterprise_quarantine`. ~2 LOC. |
| `src/vigilancia_multiagente/api/dependencies.py` | Wirear `PIInterceptor`, `PIQuarantineRepository`. ~10 LOC. |

---

## Constitution Check (Pre-Design)

- **Gate result**: PASS
- **Constitucion evaluada**: v1.2.0 (`.specify/memory/constitution.md`).
- **Alignment**:
  - **Pensar Antes de Codificar**: 7 assumptions del spec (A-01..A-07) declaradas. Phase 1 valida disponibilidad del dataset Lakera y estado de dependencias antes de implementar.
  - **Simplicidad Obligatoria**: solo regex + dataset estatico. Cero ML, cero embeddings, cero abstracciones especulativas. Cada archivo <= 200 LOC.
  - **Modularidad Primero**: detector (logica pura), interceptor (orquestacion), repository (persistencia), endpoint (API) son modulos separados con responsabilidad unica.
  - **Cambios Quirurgicos y Trazables**: 3 archivos existentes modificados en modo aditivo (counter metrica, registro router, wiring DI). `tool_registry.py` no se modifica (gating ya implementado). Cero borrado, cero renombre, cero refactor lateral.
  - **Entrega Verificable**: 7 success criteria del spec mapeados a tests concretos por fase. Cada fase tiene output verificable.
- **Diseno de Software**: SRP (cada archivo un concern), SoC (detector no conoce persistencia ni API), DIP (interceptor depende de abstraccion del detector, no de implementacion concreta), CQS (tool-gating es query pura; cuarentena es command separado), KISS (regex es la solucion mas simple que funciona para MVP), YAGNI (cero embedding comparison, cero anomaly detector).

---

## Phases

### Phase 1 -- Validacion y setup (1 dia)

1. Verificar que `enterprise/governance/__init__.py` existe (ya creado por spec 009).
2. Verificar que MigrationRunner aplicó 006_mvp_foundation.sql (tabla `schema_migrations` contiene registro de 006) y la metadata DB responde.
3. Verificar disponibilidad del dataset Lakera open-source: descargar o confirmar formato esperado. Validar licencia compatible (A-01).
4. Verificar que `prometheus-client` esta instalado y `/metrics` responde (spec 009).
5. Verificar que `ToolRegistry.list_tools_for_role` existe y sus tests pasan.
6. Documentar resultado de validaciones en comentario de commit.

**Output**: entorno validado, dependencias confirmadas, MigrationRunner operativo con 006 aplicada, cero codigo nuevo.

### Phase 2 -- Detector PI + DetectionResult (2-3 dias)

1. Crear `enterprise/governance/detection_result.py`:
   - Dataclass frozen `DetectionResult` con: `is_suspicious: bool`, `patterns_matched: list[str]`, `severity: Literal["LOW", "MEDIUM", "HIGH"]`, `confidence: float`, `source: str`.
2. Crear `config/security/lakera-patterns.json`:
   - Array de objetos `{"pattern": "<regex>", "category": "<string>", "severity_weight": <int>}`.
   - Incluir patrones del dataset Lakera open-source relevantes.
3. Crear `enterprise/governance/prompt_injection_detector.py`:
   - Clase `PromptInjectionDetector`.
   - Constructor carga patrones regex hardcoded (FR-002: ingles + espanol) y dataset Lakera desde archivo local (FR-003).
   - Si archivo Lakera faltante al boot: warning en log, opera solo con regex (EC-05).
   - Metodo `detect(content: str, source: str) -> DetectionResult` (FR-004).
   - Severidad calculada segun FR-005: HIGH si >= 2 patrones o exfiltracion; MEDIUM si 1 patron de control; LOW si ambiguo.
   - Inputs > 100KB procesados en chunks (EC-02).
   - Multiples patrones: todos registrados, severity = max (EC-03).
4. Tests `tests/enterprise/governance/test_prompt_injection_detector.py`:
   - 50 payloads conocidos: 100% deteccion (SC-001).
   - 200 documentos empresariales tipicos: < 2% falsos positivos (SC-002).
   - Latencia < 50 ms para input de 10KB (SC-003).
   - Input sin patrones: `is_suspicious = false`.
   - Archivo Lakera faltante: funciona solo con regex, emite warning.

**Output**: detector funcional + tests verdes. Traza: FR-001..FR-005, SC-001..SC-003.

### Phase 3 -- Migracion + Repository (1-2 dias)

1. Crear migración SQL cruda `src/vigilancia_multiagente/infra/db/migrations/010_pi_quarantine.sql`:
   - Tabla `pi_quarantine(id UUID PK, tenant_id UUID NOT NULL, source VARCHAR, content_excerpt TEXT, detected_patterns JSONB, severity VARCHAR, quarantined_at TIMESTAMP NOT NULL, approved_at TIMESTAMP NULL, approved_by VARCHAR NULL)`.
   - Indice por `tenant_id`.
   - Indice por `quarantined_at DESC`.
   - DDL idempotente (`CREATE TABLE IF NOT EXISTS`).
   - Reversibilidad: script de DROP idempotente (`DROP TABLE IF EXISTS pi_quarantine`).
2. Verificar migración idempotente: aplicar 2 veces sin error via MigrationRunner (SC-006); verificar aislamiento de tablas del 2.0.
3. Crear `enterprise/governance/pi_quarantine_repository.py`:
   - `PIQuarantineRepository` con metodos:
     - `quarantine(tenant_id, source, content_excerpt, detected_patterns, severity) -> UUID`.
     - `list_pending(tenant_id) -> list[QuarantineRecord]`.
     - `approve(id, approved_by) -> None` (actualiza `approved_at` + `approved_by`).
     - `get_by_id(id) -> QuarantineRecord | None`.
4. Tests `tests/enterprise/governance/test_pi_quarantine_repository.py`:
   - Insert + query + approve roundtrip.
   - Aislamiento por `tenant_id`.
5. Tests `tests/enterprise/migrations/test_010_pi_quarantine.py`:
   - Aplicar migración 2 veces sin error (idempotencia, SC-006).
   - No afecta tablas existentes del 2.0 ni de spec 009 (aislamiento).

**Output**: tabla creada, migración idempotente, repository operativo. Traza: FR-009..FR-012, FR-018, FR-019, SC-006.

### Phase 4 -- Interceptor + Audit + Metrica (2 dias)

1. Crear `enterprise/governance/pi_interceptor.py`:
   - Clase `PIInterceptor` con dependencias inyectadas: `PromptInjectionDetector`, `PIQuarantineRepository`.
   - Metodo `intercept(content: str, source: str, tenant_id: UUID) -> InterceptionResult`:
     - Invoca `detector.detect(content, source)`.
     - Si `is_suspicious`: persiste en cuarentena, escribe audit JSONL, incrementa metrica, retorna `blocked=True`.
     - Si no sospechoso: retorna `blocked=False, content=content`.
   - `content_excerpt` truncado a 500 chars (FR-010).
   - Audit log: escribe a `~/.vigilador/audit/pi_quarantine_<fecha>.jsonl` (FR-014).
   - Metrica: incrementa `vigilador_pi_quarantined_total{source, severity}` (FR-015).
2. Modificar `enterprise/observability/metrics.py`:
   - Anadir `pi_quarantined_total = Counter("vigilador_pi_quarantined_total", "...", ["source", "severity"])`.
3. Tests `tests/enterprise/governance/test_pi_interceptor.py`:
   - Input malicioso: bloqueado, registro en cuarentena, audit escrito, metrica incrementada.
   - Input limpio: pasa sin bloqueo, cero escrituras.
   - Contenido cuarentenado NO accesible por agente (SC-004).
   - Metrica refleja conteo real (SC-005).

**Output**: interceptor funcional, audit JSONL operativo, metrica expuesta. Traza: FR-006..FR-008, FR-013..FR-015, SC-004, SC-005.

### Phase 5 -- Tool-gating verificación (0.5 dia)

1. VERIFICAR que `_passes_gating()` en `enterprise/tooling/tool_registry.py` ya cumple FR-016/FR-017: excluye tools con `requires_auth: true` cuya API key no esté en entorno; opera como query pura sin side-effects (CQS).
2. Tests `tests/enterprise/governance/test_tool_gating_credentials.py`:
   - 10 tools: 5 con key configurada, 5 sin key.
   - `list_tools_for_role` retorna solo las 5 con key (SC-007).
   - Tool con `requires_auth: false` siempre aparece independientemente de keys.
   - Cambio de entorno (key anadida) refleja inmediatamente en siguiente query.

**Output**: tool-gating existente verificado + tests verdes. NO se modifica `tool_registry.py` (constitución #5). Traza: FR-016, FR-017, SC-007.

### Phase 6 -- Endpoint API cuarentena (1 dia)

1. Crear `api/routes/enterprise_quarantine.py`:
   - `GET /api/v2/enterprise/quarantine` -- lista inputs cuarentenados pendientes del tenant.
   - `GET /api/v2/enterprise/quarantine/{id}` -- detalle de un input cuarentenado.
   - `POST /api/v2/enterprise/quarantine/{id}/approve` -- aprueba/libera input. Requiere `approved_by` en body. Solo usuario humano (FR-011).
   - Al aprobar: actualiza registro, reinyecta contenido al pipeline de ingestion (FR-012).
2. Registrar router en `api/app.py`.
3. Wirear dependencias en `api/dependencies.py`.
4. Tests `tests/enterprise/api/test_quarantine_endpoints.py`:
   - Listar cuarentena retorna registros pendientes.
   - Aprobar actualiza `approved_at` y `approved_by`.
   - Intento de aprobacion sin autenticacion falla.

**Output**: API de cuarentena expuesta, lista para consumo frontend. Traza: FR-011, FR-012, FR-013.

### Phase 7 -- Integracion E2E + cierre (1 dia)

1. Test E2E completo: input malicioso → detector → interceptor → cuarentena → NO llega al LLM → usuario aprueba → reinyeccion.
2. Test E2E: 100 documentos limpios → cero cuarentenas (AS-4).
3. Verificar SC-001..SC-007 con evidencia.
4. Verificar que tests del 2.0 siguen pasando al 100%.
5. Verificar `scripts/check-layer-imports.py` sin violaciones nuevas.
6. Verificar que MigrationRunner aplica `010_pi_quarantine.sql` idempotentemente sobre el stack completo de migraciones (001..006 + 010).

**Output**: spec 020 completado, todos los SC verificados.

---

## Rollout Strategy

**Estrategia**: incremental por fase. Cada fase produce artefactos verificables y tests deben pasar antes de avanzar.

- **Backward compatibility**: cero cambios al 2.0. El detector y el interceptor son modulos nuevos en `enterprise/governance/`. No se modifica `tool_registry.py` (el gating existente ya cumple FR-016/FR-017).
- **Feature flags**: cero necesarios. El interceptor se activa al ser invocado desde los conectores de ingestion. Si los conectores (spec 010) no estan completados, el interceptor queda disponible como callable sin efecto hasta integracion.
- **Coexistencia con spec 009**: la migración 010_pi_quarantine.sql se aplica encima de la 006 sin conflicto. El counter Prometheus se anade al modulo de metricas existente.
- **Dependencia de spec 010 (ingestion)**: el hook `PIInterceptor.intercept()` esta disenado para ser invocado desde cualquier conector. Si spec 010 no esta completado, el interceptor se valida via tests unitarios y E2E con inputs simulados. La integracion real con conectores se hace cuando spec 010 este disponible.
- **Dependencia de spec 013 (frontend)**: el endpoint API queda listo. La alerta visual en frontend se implementa cuando spec 013 provea la superficie. Mientras tanto, la alerta se materializa via audit log + metrica Prometheus.
- **Rollback**: `DROP TABLE IF EXISTS pi_quarantine` elimina la tabla sin afectar otras tablas. MigrationRunner es forward-only; el rollback es DDL idempotente manual.

**Scope MVP declarado**: este plan implementa SOLO lo listado. PI defense con embeddings, anomaly detector, SSO/SAML, DR y capability tokens granulares son roadmap post-MVP y no se implementan ni se preparan con stubs.

---

## Success Criteria

- **SC-001**: El detector intercepta el 100% de inputs con al menos uno de los patrones regex definidos (test con corpus de 50 payloads conocidos).
- **SC-002**: Tasa de falsos positivos < 2% sobre corpus de 200 documentos empresariales tipicos.
- **SC-003**: Latencia del detector < 50 ms (p95) para input de 10KB.
- **SC-004**: Un input cuarentenado NUNCA llega al LLM sin aprobacion humana explicita (test E2E de bypass).
- **SC-005**: Metrica `vigilador_pi_quarantined_total` refleja con precision el conteo real (delta = 0 entre metrica y registros en tabla).
- **SC-006**: Migración SQL idempotente: aplicar 2 veces consecutivas sin error; DROP idempotente elimina tabla sin afectar tablas del 2.0.
- **SC-007**: Tool-gating excluye correctamente el 100% de tools sin credencial configurada (test con 10 tools: 5 con key, 5 sin key).

## Constitution Check (Post-Design)

- **Status**: PASS
- **Constitucion evaluada**: v1.2.0 (`.specify/memory/constitution.md`).
- **Justification**:
  - **Pensar Antes de Codificar**: Phase 1 entera dedicada a validar entorno y dependencias antes de escribir codigo. 7 assumptions del spec verificadas explicitamente.
  - **Simplicidad Obligatoria**: solucion minima viable (regex + dataset estatico). Cero ML, cero embeddings, cero abstracciones especulativas. Cada archivo <= 200 LOC. Total ~560 LOC en 5 archivos funcionales.
  - **Modularidad Primero**: 4 modulos con responsabilidad unica (detector, interceptor, repository, endpoint). Detector no conoce persistencia. Interceptor no conoce API. Repository no conoce logica de deteccion.
  - **Cambios Quirurgicos y Trazables**: 3 archivos existentes modificados en modo estrictamente aditivo (~17 LOC total de cambios). `tool_registry.py` NO se modifica (gating ya implementado). Cero borrado, cero renombre, cero refactor lateral. Cada FR traza a acceptance scenario y success criterion del spec.
  - **Entrega Verificable**: 7 SC con metodo de validacion claro. Tests por fase. E2E en Phase 7.
  - **Diseno de Software**: SRP (cada modulo un concern), SoC (capas separadas: logica/persistencia/API), DIP (interceptor depende de abstraccion del detector), CQS (tool-gating query pura, cuarentena command separado), KISS (regex es la solucion mas simple), YAGNI (cero preparacion para features roadmap).
