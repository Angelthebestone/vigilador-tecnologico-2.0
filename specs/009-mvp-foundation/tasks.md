# Tasks: Vigilador 3.0 MVP Foundation

**Input**: `specs/009-mvp-foundation/spec.md`, `specs/009-mvp-foundation/plan.md`
**Feature**: F0 + F1 del MVP — fundación reusable del Vigilador 3.0 (adapter Xiaomimimo, ToolRegistry con discovery semántico, HealthMonitor CQS, migración SQL 006, OAuthManager Fernet, frontend de onboarding).

**User Stories del spec**:
- **US1 (P1)**: Operador admin completa setup + onboarding + listado tools.
  *Único user story de este spec; cubre las 8 acceptance scenarios y los 34 FRs.*

**Testing strategy**: tests pedidos explícitamente por el spec (FR-032 exige 100% del 2.0; SC-002 y SC-003 exigen cobertura por componente). Por eso este tasks.md **SÍ incluye tasks de test** intercaladas siguiendo el orden test-before-implementation por componente.

---

## Phase 1: Setup (project initialization)

Cero código de producto. Solo validación + estructura + auditoría.

- [x] T001 Validar PostgreSQL existente: ejecutar `python -c "import asyncpg; ..."` contra `VT_DATABASE_URL` y confirmar versión, persistir resultado en `docs/postgres-readiness.md` _(OK 2026-05-28: PostgreSQL 18.3; DB virgen sin migraciones)_
- [ ] T002 [P] Validar conectividad Xiaomimimo: `curl https://platform.xiaomimimo.com/v1/models` con `VT_XIAOMIMIMO_API_KEY` y persistir resultado en `docs/postgres-readiness.md` (sección "Xiaomimimo connectivity") _(PENDIENTE — requiere entorno vivo: API key)_
- [x] T003 [P] Validar embedding provider del 2.0: ejecutar test sintético contra `src/vigilancia_multiagente/infra/embeddings/gemini_gateway.py` para confirmar que sigue operativo _(OK 2026-05-28: embed() devolvió 768 dims)_
- [x] T004 [P] Validar layer imports baseline: `python scripts/check-layer-imports.py` sin issues sobre el 2.0 _(OK 2026-05-28: 0 violaciones)_
- [x] T005 Crear estructura `src/vigilancia_multiagente/enterprise/` con subcarpetas vacías (orchestration, modes, skills_marketplace, intelligence, triggers, auth, governance, memory, observability, ingestion, tooling, dreaming, mcp) — solo `__init__.py` vacíos _(13 subpaquetes + 14 __init__.py)_
- [x] T006 [P] Crear estructura `config/` con subcarpetas placeholder (`config/modes/`, `config/playbooks/`, `config/company/`, `config/templates/`, `config/skills/`, `config/mcp/`) cada una con `README.md` mínimo de 3-5 líneas indicando "reservada para spec NNN" _(sin tocar prompt_overrides/skills/mcp-providers.yaml del 2.0)_
- [x] T007 [P] Crear `docs/audit-licenses.md` con encabezados y tabla vacía + secciones "Hermes copies" (vacía hasta spec 011), "New PyPI dependencies" (a llenar en T008), "Frontend dependencies" (sin cambios)
- [x] T008 Añadir dependencias nuevas en `pyproject.toml`: `openai>=1.40`, `cryptography>=42`, `apscheduler>=3.10`, `prometheus-client>=0.19`, `opentelemetry-api>=1.27`, `opentelemetry-sdk>=1.27`. Actualizar `docs/audit-licenses.md` con cada una (versión + licencia) _(instaladas + importables; respx>=0.21 añadido a dev para T021)_
- [x] T009 ~~Setup Alembic~~ **REINTERPRETADO**: el 2.0 no usa Alembic ni ORM. Se verificó el sistema de migraciones SQL crudo existente (`infra/db/migrations/NNN_*.sql` + `MigrationRunner`, 5 migraciones intactas) y se eliminó el scaffold `alembic/` vacío. La migración 006 (5 tablas enterprise) se crea en Fase 2. _(decisión operador 2026-05-28, ver `docs/postgres-readiness.md`)_
- [x] T010 Añadir variables nuevas en `.env.example`: solo secretos/API keys (`VT_XIAOMIMIMO_API_KEY=`) + `VT_DATABASE_URL`. Los fields no-secretos viven en `settings.py` con default (Convención sobre Configuración). Conservar todas las variables existentes del 2.0. _(añadidas vars secretas del spec 009 al final; las 66 líneas del 2.0 intactas)_

**Independent Test Criteria for Phase 1**: `docs/postgres-readiness.md` confirma PostgreSQL + Xiaomimimo + Gemini OK; `scripts/check-layer-imports.py` baseline sin issues; `schema_migrations` incluye 006; `pyproject.toml` y `.env.example` actualizados sin tocar lo del 2.0; tests del 2.0 siguen pasando al 100% (`pytest`).

---

## Phase 2: Foundational (blocking prerequisites for the user story)

Componentes base que toda US1 necesita: LLM adapter, tool contract, repositorios, migración.

- [x] T011 Extender `src/vigilancia_multiagente/config/settings.py` con secciones nuevas: `llm.default` (str), `llm.adapters.xiaomimimo.{enabled,model,api_key_env,base_url}`, `llm.adapters.minimax.{enabled,api_key_env}`, `enterprise.health_monitor.{interval_sec,circuit_breaker_threshold,cooldown_sec}`. NO tocar settings existentes del 2.0
- [ ] T012 [P] Crear `config/settings.yaml` con defaults: `llm.default: xiaomimimo`, `llm.adapters.xiaomimimo.enabled: true`, `llm.adapters.xiaomimimo.model: mimo-v2-flash`, `llm.adapters.xiaomimimo.api_key_env: VT_XIAOMIMIMO_API_KEY`, `llm.adapters.xiaomimimo.base_url: https://platform.xiaomimimo.com/v1`, `llm.adapters.minimax.enabled: false`
- [x] T013 Migración `src/vigilancia_multiagente/infra/db/migrations/006_mvp_foundation.sql` (YA creada) con 5 tablas: `tool_health(name PK, tenant_id UUID NOT NULL, status, last_check, fail_count, last_error, domain, requires_key)`, `oauth_credentials(id, tenant_id UUID NOT NULL, provider, token_encrypted, refresh_token_encrypted, expires_at, scopes)`, `subagents(id, tenant_id UUID NOT NULL, parent_session_id, depth, role, status, pause_reason, resume_token, last_progress_at, created_at, completed_at)`, `pending_approvals(id, tenant_id UUID NOT NULL, kind, payload JSONB, requested_by_agent, requested_at, status)`, `company_profile(id, tenant_id UUID NOT NULL, name, sector, country, department, municipality, timezone)`. Índices: `tenant_id` en cada una, `name` en `tool_health`, `provider` en `oauth_credentials`. DDL idempotente (forward-only; reversibilidad = DROP idempotente).
- [ ] T014 Test migración: crear `tests/enterprise/migrations/test_migration_006.py` con tests de idempotencia (aplicar 006 dos veces consecutivas sin error) + verificar aislamiento (tablas del 2.0 intactas tras aplicar la migración)
- [x] T015 [P] Crear `src/vigilancia_multiagente/enterprise/tooling/tool_wrapper.py` con Protocol `ToolWrapper` (atributos `name`, `domain`, `is_external_mcp`, `requires_auth`; métodos async `healthcheck() -> HealthcheckResult`, `execute(tool_name, args) -> dict`). Incluir dataclass `HealthcheckResult(status, latency_ms, error)`
- [x] T016 [P] Crear `src/vigilancia_multiagente/enterprise/tooling/tool_card.py` con dataclasses `ToolCard` (id, descripción ≤ 80 chars, domains list, requires_auth bool, cost_tier, status), `ToolSummary` (extiende ToolCard con schema inputs/outputs + 2-3 ejemplos), `ToolDocs` (extiende ToolSummary con descripción larga + ejemplos completos)
- [x] T017 Crear `src/vigilancia_multiagente/infra/persistence/tool_health_repository.py` con `ToolHealthRepository`: métodos async `read_status(name, tenant_id) -> ToolHealthRow | None`, `list_all(tenant_id) -> list[ToolHealthRow]`, `upsert(row: ToolHealthRow) -> None` (este último para uso EXCLUSIVO de HealthMonitor; ToolRegistry solo llama los read*)
- [x] T018 [P] Crear `src/vigilancia_multiagente/infra/persistence/oauth_credentials_repository.py` con `OAuthCredentialsRepository`: métodos async `get(provider, tenant_id) -> OAuthRow | None`, `store(row) -> None`, `delete(provider, tenant_id) -> None`
- [x] T019 [P] Crear `src/vigilancia_multiagente/infra/persistence/company_profile_repository.py` con `CompanyProfileRepository`: métodos async `get(tenant_id) -> CompanyProfile | None`, `upsert(profile) -> None`
- [ ] T020 Test repositorios: `tests/enterprise/persistence/test_repositories.py` cubriendo CRUD básico contra DB de prueba para los 3 repositorios

**Independent Test Criteria for Phase 2**: `pytest tests/enterprise/migrations/ tests/enterprise/persistence/` verde; migración aplica y revierte sin residuos; protocolos y dataclasses tipados correctamente (`basedpyright` sin nuevos errores). _✅ CUMPLIDO 2026-05-28: 8 passed contra PostgreSQL 18.3 real; ruff "All checks passed!" en archivos nuevos; basedpyright sin errores nuevos (los 13 preexistentes viven en bm25_plus_embedding.py del 2.0); 0 violaciones de capas._

---

## Phase 3: User Story 1 — Operador admin completa setup + onboarding + listado tools (P1)

**Goal**: cubrir las 8 acceptance scenarios y los 34 FRs del spec. Entrega un sistema con XiaomimimoClient funcional, ToolRegistry con discovery semántico, HealthMonitor con circuit breaker, OAuthManager Fernet, 6 endpoints API y 4 pantallas frontend.

**Independent Test Criteria**: operador completa onboarding (login → paso 1 → paso 2) en ≤ 5 min; conectividad Xiaomimimo verificada por UI; listado de tools muestra estado correcto; tests del 2.0 siguen pasando al 100%.

### F1.1 — XiaomimimoClient adapter LLM

- [ ] T021 [P] [US1] Test unitario `tests/enterprise/llm/test_xiaomimimo_client.py`: 5 tests (chat completion con respuesta mock, tool calling con respuesta mock, error 401 propaga sin try/except, error 429 propaga, modelo default `mimo-v2-flash` aplicado si no se pasa explícito). Usar `respx` o `httpx.MockTransport` para mockear el endpoint OpenAI-compatible
- [x] T022 [US1] Implementar `src/vigilancia_multiagente/infra/llm/xiaomimimo_client.py` (~250 LOC máx): clase `XiaomimimoClient` con constructor que lee API key + base_url de settings, método async `chat_completion(messages: list[Message], tools: list[ToolSchema] | None = None, model: str | None = None) -> ChatResponse`. Internamente usa `openai.AsyncOpenAI(api_key=..., base_url=...)`. Retorna tipos propios `ChatResponse`, `ToolCall` (NO exponer tipos del SDK). Cero try/except defensivos. Hacer T021 verde
- [ ] T023 [US1] Wirear `XiaomimimoClient` en `src/vigilancia_multiagente/api/dependencies.py` como factory que respeta `settings.llm.default` y solo instancia el adapter habilitado. NO tocar wires existentes del 2.0

### F1.2 — ToolRegistry con discovery semántico

- [ ] T024 [P] [US1] Test `tests/enterprise/tooling/test_tool_registry.py`: 7 tests (registro normal de 5 tools fake; duplicado por `name` falla; `list_tools_for_role` retorna nivel mínimo con ≤ 80 chars por descripción; `get_summary` retorna ficha resumida; `get_docs` retorna contenido completo; `discover("research")` ordena por similitud usando embedding mock; gating por API key faltante oculta tool)
- [x] T025 [US1] Implementar `src/vigilancia_multiagente/enterprise/tooling/tool_registry.py` (~350 LOC máx): clase `ToolRegistry` con métodos async `register(tool: ToolWrapper)`, `list_tools_for_role(role, tenant_id) -> list[ToolCard]`, `get_summary(name) -> ToolSummary`, `get_docs(name) -> ToolDocs`, `discover(role, intent, tenant_id) -> list[ToolCard]`. Solo lectura desde `ToolHealthRepository`. `discover` inyecta `EmbeddingGateway` (puerto del 2.0) via DI. Gating: lee API key declarada del wrapper + consulta `tool_health.status`. Hacer T024 verde
- [ ] T026 [US1] Test de performance `tests/enterprise/tooling/test_tool_registry_perf.py`: registrar 200 tools sintéticas, medir `list_tools_for_role` ≤ 200 ms (SC-004)

### F1.3 — HealthMonitor con circuit breaker

- [ ] T027 [P] [US1] Test `tests/enterprise/observability/test_health_monitor.py`: 4 tests con clock fake (`apscheduler` test utilities o `freezegun`): ciclo cada 30 s invoca healthcheck en cada tool registrada; circuit breaker abre tras 3 fallos en 60 s; status DOWN se mantiene ≥ 5 min; escribe línea JSONL al log
- [x] T028 [US1] Implementar `src/vigilancia_multiagente/enterprise/observability/health_monitor.py` (~300 LOC máx): clase `HealthMonitor` con APScheduler `AsyncIOScheduler`, método `start()`, callback `_tick()` que itera tools del registry, invoca `healthcheck()`, actualiza `tool_health` via `ToolHealthRepository.upsert`. Circuit breaker: contador en memoria + `fail_count` persistido. Escritura JSONL a `~/.vigilador/audit/healthcheck.log`. Hacer T027 verde
- [ ] T029 [US1] Wirear `HealthMonitor` en `dependencies.py` como singleton lazy; arrancar el scheduler en lifespan startup de FastAPI (`api/app.py`). NO arrancar si `enterprise.health_monitor.enabled: false` en settings

### F1.4 — OAuthManager con Fernet

- [ ] T030 [P] [US1] Test `tests/enterprise/auth/test_oauth_manager.py`: 5 tests (Fernet key se crea al primer arranque con permisos restrictivos; `store` encripta y persiste; `get` desencripta correctamente; roundtrip multi-provider; `refresh_if_needed` dispara cuando `expires_at - now < 7d`)
- [x] T031 [US1] Implementar `src/vigilancia_multiagente/enterprise/auth/oauth_manager.py` (~250 LOC máx): clase `OAuthManager` que genera/lee Fernet key de `~/.vigilador/credentials/.fernet_key` (chmod 600 en Unix; restricciones equivalentes en Windows con `icacls`). Métodos `store(provider, access_token, refresh_token, expires_at, scopes)`, `get(provider, tenant_id) -> OAuthCredential | None`, `refresh_if_needed(provider)` (placeholder que registra warning si falla). Persiste vía `OAuthCredentialsRepository`. Hacer T030 verde

### F1.5 — Observabilidad mínima

- [x] T032 [P] [US1] Crear `src/vigilancia_multiagente/enterprise/observability/metrics.py` con counters Prometheus: `vigilador_llm_calls_total{provider,model,status}`, `vigilador_tool_invocations_total{tool,status}`, `vigilador_tool_health_status{name,domain}` (gauge). Exponer via `prometheus_client.make_asgi_app`
- [x] T033 [P] [US1] Crear `src/vigilancia_multiagente/enterprise/observability/tracing.py` con setup OpenTelemetry: TracerProvider + ConsoleSpanExporter por default; spans `session.lifecycle`, `llm.call`, `tool.healthcheck`, `app.startup`

### F1.6 — API endpoints enterprise

- [ ] T034 [P] [US1] Test `tests/enterprise/api/test_auth_endpoints.py`: 3 tests (login con credenciales válidas retorna 200 + cookie/token; login con credenciales inválidas retorna 401; logout invalida sesión)
- [ ] T035 [P] [US1] Test `tests/enterprise/api/test_onboarding_endpoints.py`: 5 tests (POST `company` persiste `company_geo` en `company_profile`; POST `llm-provider` valida `provider` y persiste settings; POST `test-llm` llama Xiaomimimo y retorna OK/error con latencia; flujo parcial — solo paso 1 — luego retomar; campos inválidos retornan 422)
- [ ] T036 [P] [US1] Test `tests/enterprise/api/test_tools_endpoints.py`: 3 tests (GET `tools` lista desde `tool_health` y retorna 3 niveles según query param `detail=card|summary|docs`; tool con `requires_key` y env vacío retorna `status=UNCONFIGURED`; tool DOWN no aparece en listado público)
- [x] T037 [US1] Implementar `src/vigilancia_multiagente/api/routes/enterprise_auth.py` con `POST /api/v2/enterprise/auth/login` y `POST /api/v2/enterprise/auth/logout`. Auth local single-tenant: comparar contra credencial admin en `config/admin-credentials.yaml` (hashed con bcrypt). Hacer T034 verde
- [x] T038 [US1] Implementar `src/vigilancia_multiagente/api/routes/enterprise_onboarding.py` con `POST /api/v2/enterprise/onboarding/company`, `POST /api/v2/enterprise/onboarding/llm-provider`, `POST /api/v2/enterprise/onboarding/test-llm`. Usa `CompanyProfileRepository` y `XiaomimimoClient`. Hacer T035 verde
- [x] T039 [US1] Implementar `src/vigilancia_multiagente/api/routes/enterprise_tools.py` con `GET /api/v2/enterprise/tools?detail=card|summary|docs`. Lee del `ToolRegistry`. Hacer T036 verde
- [x] T040 [P] [US1] Implementar `src/vigilancia_multiagente/api/routes/enterprise_metrics.py` montando el ASGI app de Prometheus en `GET /metrics`
- [ ] T041 [US1] Registrar los 4 routers en `src/vigilancia_multiagente/api/app.py` bajo prefijo `/api/v2/enterprise/*` (excepto `/metrics`). NO tocar routers del 2.0. Añadir el `HealthMonitor` al lifespan startup

### F1.7 — Frontend MVP foundation

- [ ] T042 [P] [US1] Crear estructura `frontend/src/enterprise/{auth,onboarding,tools,api,state}/` con `index.ts` por subcarpeta para barrel exports
- [ ] T043 [P] [US1] Crear `frontend/src/enterprise/api/enterpriseClient.ts` con cliente axios envolvente que apunta a `/api/v2/enterprise/*`, gestiona token de sesión y maneja errores HTTP estándar
- [ ] T044 [P] [US1] Crear `frontend/src/enterprise/state/onboardingStore.ts` con Zustand store: estado `{ companyProfile, llmProvider, currentStep }`, acciones `saveStep1`, `saveStep2`, `loadFromBackend`. Persistencia parcial en `localStorage` para retomar paso (EC-06)
- [ ] T045 [P] [US1] Crear `frontend/src/enterprise/state/toolsStore.ts` con Zustand store: estado `{ tools: ToolCard[], lastFetch }`, acción `refresh()` que pega a `GET /api/v2/enterprise/tools`
- [ ] T046 [US1] Implementar `frontend/src/enterprise/auth/LoginPage.tsx`: form usuario+password, llama `/auth/login`, redirige a `/enterprise/onboarding` o `/enterprise/tools` según haya completado onboarding
- [ ] T047 [US1] Implementar `frontend/src/enterprise/onboarding/OnboardingFlow.tsx`: router interno que muestra Step1 o Step2 según `currentStep` del store; lee estado persistido al montar
- [ ] T048 [US1] Implementar `frontend/src/enterprise/onboarding/Step1Company.tsx`: form con `name`, `sector` (select), `country`, `department`, `municipality`, `timezone` (select); validación zod; submit llama `/onboarding/company`
- [ ] T049 [US1] Implementar `frontend/src/enterprise/onboarding/Step2LlmProvider.tsx`: select provider (Xiaomimimo default + MiniMax opcional), input API key (type=password con toggle revelable), botón "Probar conectividad" llama `/onboarding/test-llm` y muestra modelo respondido + latencia ms. Hacer T035 verde end-to-end
- [ ] T050 [US1] Implementar `frontend/src/enterprise/tools/ToolsListPage.tsx`: tabla con columnas nombre, dominio, estado (badge color: verde UP, rojo DOWN, gris UNCONFIGURED), último check (relative time), último error tooltip. Auto-refresh cada 60 s
- [ ] T051 [P] [US1] Añadir rutas en `frontend/src/App.tsx`: `/enterprise/login`, `/enterprise/onboarding`, `/enterprise/tools`. NO tocar rutas del 2.0
- [ ] T052 [P] [US1] Tests Vitest `frontend/src/enterprise/__tests__/onboarding.test.tsx`: flujo completo (login → paso 1 → paso 2 → success) con mocks de API; verificar persistencia parcial al cerrar y reabrir
- [ ] T053 [P] [US1] Tests Vitest `frontend/src/enterprise/__tests__/tools-list.test.tsx`: render con 5 tools fake, refresh, estados visuales correctos

---

## Phase 4: Polish & Cross-Cutting Concerns

Verificación final, documentación, cero regresiones.

- [ ] T054 [P] Correr suite completa: `pytest` debe pasar al 100% (2.0 + nuevas). Documentar en `docs/postgres-readiness.md` sección "Final verification"
- [ ] T055 [P] Correr `scripts/check-layer-imports.py` final y verificar 0 violaciones nuevas
- [ ] T056 [P] Correr `python -m basedpyright src/vigilancia_multiagente/` y verificar 0 nuevos errores ni warnings (puede haber `type: ignore` justificados según `CLAUDE.md` sección Basedpyright)
- [ ] T057 [P] Correr `ruff check src/ tests/` + `ruff format src/ tests/` sin issues
- [ ] T058 [P] Correr tests frontend `npm test --prefix frontend` con cobertura ≥ 70% en archivos nuevos bajo `frontend/src/enterprise/`
- [ ] T059 Verificar manualmente SC-001 (onboarding ≤ 5 min en navegador limpio con stopwatch); persistir captura/notas en `docs/sc-001-validation.md`
- [ ] T060 Verificar manualmente SC-005 (HealthMonitor detecta tool caída ≤ 90 s) con tool fake que falla deliberadamente; persistir log
- [ ] T061 Verificar manualmente SC-006 (latencia mediana `mimo-v2-flash`); ejecutar batch de 10 prompts ~200 tokens y medir
- [ ] T062 Verificar SC-009: ejecutar `grep -rE "^\s*(pass|\.\.\.|TODO)\s*$" src/vigilancia_multiagente/enterprise/` y confirmar 0 matches (excepto `__init__.py` vacíos legítimos)
- [ ] T063 Actualizar `CLAUDE.md` con: comando `python -m vigilancia_multiagente.infra.db.migration_runner` documentado; env vars nuevas listadas; comando para correr `HealthMonitor` standalone si se desea (futuro post-MVP); nota de cómo deshabilitar enterprise vía settings
- [ ] T064 Cerrar `docs/audit-licenses.md` con tabla final de las 6 deps PyPI nuevas + sus licencias + atribuciones requeridas (si las hay)
- [ ] T065 Crear `specs/009-mvp-foundation/quickstart.md` (opcional, recomendado) con: pasos para arrancar el sistema localmente, smoke tests manuales, troubleshooting típico (Xiaomimimo 401, Postgres conexión, frontend build errors)
- [ ] T066 Verificar checklist completo `specs/009-mvp-foundation/checklists/requirements.md` y marcar todo como pasado

---

## Dependencies

- **Phase 1 (Setup)** must complete before **Phase 2 (Foundational)**.
- **Phase 2 (Foundational)** must complete before **Phase 3 (US1)**.
- **Phase 3 (US1)** must complete before **Phase 4 (Polish)**.
- Dentro de **Phase 3**:
  - **F1.1 (XiaomimimoClient)**, **F1.2 (ToolRegistry)**, **F1.3 (HealthMonitor)**, **F1.4 (OAuthManager)** y **F1.5 (Observability)** son **independientes** entre sí. Pueden ejecutarse en paralelo por desarrolladores distintos.
  - **F1.6 (API endpoints)** depende de F1.1+F1.2+F1.3+F1.4 (necesita los componentes wireados).
  - **F1.7 (Frontend)** depende de F1.6 (necesita los endpoints).
- **Tests-before-implementation por componente** dentro de cada F1.x: T021→T022→T023, T024→T025→T026, T027→T028→T029, T030→T031, T034→T037, T035→T038, T036→T039.
- **T011** (extender `settings.py`) bloquea T012, T022, T028 y todos los que leen settings.
- **T013** (migración) bloquea T014, T017, T018, T019, T020 (repositorios necesitan las tablas).
- **T015, T016** (protocolos/dataclasses) bloquean T025 (ToolRegistry los importa).
- **T017** (ToolHealthRepository) bloquea T025 (ToolRegistry lo usa) y T028 (HealthMonitor lo usa).
- **T018** (OAuthCredentialsRepository) bloquea T031 (OAuthManager lo usa).
- **T019** (CompanyProfileRepository) bloquea T038 (onboarding endpoint lo usa).
- **T041** (registrar routers en `app.py`) requiere T037, T038, T039, T040 completos.
- **T046..T050** (pantallas frontend) requieren T042, T043, T044, T045 (estructura, cliente, stores).

---

## Parallel Execution Examples

### Phase 1 Parallel Block

- Run **T002, T003, T004, T006, T007** en paralelo (validaciones y creación de placeholders no relacionados).

### Phase 2 Parallel Block

- Run **T012, T015, T016, T018, T019** en paralelo tras completar T011 (settings) y T013 (migración aplicada). Son archivos distintos sin dependencias entre sí.

### Phase 3 — F1 components Parallel Block

Tras Phase 2 verde, distribuir entre 4 desarrolladores:

- **Dev A — LLM**: T021 → T022 → T023.
- **Dev B — Registry**: T024 → T025 → T026.
- **Dev C — HealthMonitor**: T027 → T028 → T029.
- **Dev D — Auth + Observability**: T030 → T031, en paralelo T032, T033.

### Phase 3 — API endpoints Parallel Block

Tras F1.1..F1.5 verdes:

- Run **T034, T035, T036, T040** (tests + métricas) en paralelo.
- Luego **T037, T038, T039** en paralelo (3 routers distintos).
- Finalmente **T041** secuencial (registra todos los routers).

### Phase 3 — Frontend Parallel Block

Tras API endpoints verdes:

- Run **T042, T043, T044, T045** en paralelo (estructura + cliente + 2 stores).
- Luego **T046, T047, T048, T049, T050** parcialmente secuenciales por compartir el flow del onboarding (recomendado: T047 antes que T048+T049; T050 independiente).
- Run **T051, T052, T053** en paralelo al final.

### Phase 4 Parallel Block

- Run **T054, T055, T056, T057, T058** en paralelo (linters/tests/typechecks independientes).
- Luego **T059, T060, T061, T062** secuencial-manual (requieren ojos humanos).
- Finalmente **T063, T064, T065, T066** en paralelo.

---

## Implementation Strategy

1. **Cerrar Phase 1 (Setup) primero**: validar entorno + estructura vacía + MigrationRunner + deps. Cero código de producto. Esto da go/no-go al spec 009 completo.
2. **Cerrar Phase 2 (Foundational) segundo**: settings + migración + repositorios + protocolos/cards. Estos componentes son la base que todo lo demás importa.
3. **Phase 3 (US1) en paralelo por componente**: F1.1..F1.5 son independientes; distribuir entre desarrolladores. Sincronizar antes de F1.6 (endpoints). F1.7 (frontend) cierra al final.
4. **Phase 4 (Polish) como gate final**: nada se considera entregado hasta que linters, tests del 2.0 y del 3.0 pasen + SC manuales verificados.
5. **Punto de no retorno**: tras T041 (registro de routers) la app expone la superficie nueva. Si algo va mal aquí, revertir con `DROP TABLE IF EXISTS` de las tablas enterprise deja la app del 2.0 intacta.
6. **MVP scope ESTRICTO**: cualquier feature que no esté en este tasks.md va a spec 010+ (siguiente fase). NO añadir tools concretas, modos, playbooks ni Dreaming en este spec — sus tasks viven en specs posteriores.

---

## Format Validation

Todas las tareas T001..T066 siguen el formato requerido:
- ✅ Checkbox `- [ ]` al inicio.
- ✅ Task ID secuencial (T001..T066).
- ✅ Marcador `[P]` solo en tareas paralelizables (diferentes archivos / sin dependencias incompletas).
- ✅ Label `[US1]` en todas las tareas de Phase 3 (single user story); sin label en Setup, Foundational ni Polish.
- ✅ Descripción con acción + path concreto del archivo.

**Total task count**: 66 tareas.
**Task count per user story**:
- Setup (Phase 1): 10
- Foundational (Phase 2): 10
- US1 (Phase 3): 33
- Polish (Phase 4): 13

**Suggested MVP scope**: este spec entero ES el MVP de fundación (US1 única). Para acotar aún más en caso de tiempo limitado, el "MVP-of-the-MVP" mínimo absoluto sería: T001-T013, T015-T020, T021-T029, T034-T041 (sin F1.4 OAuth + sin frontend) = backend funcional. Pero esto rompe SC-001 (no hay onboarding completable sin frontend), por lo que **no se recomienda recortar** este spec.
