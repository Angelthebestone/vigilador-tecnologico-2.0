# Implementation Plan: Vigilador 3.0 MVP Foundation

**Feature ID**: 009-mvp-foundation
**Created**: 2026-05-26
**Spec**: [spec.md](spec.md)

## Problem

El plan v3.0 acordó (decisión C1) un alcance MVP reducido sobre el set de planes amplio del 3.0. Antes de implementar capacidades empresariales (modos, skills, playbooks avanzados, autoaprendizaje), el sistema necesita una fundación reusable sobre el 2.0. Hoy el repo tiene:

- 2.0 funcionando (`application/`, `domain/`, `infra/`) con la API `/api/v2/research/*`, 6 agentes de rama, 15 MCPs ya registrados y workstreams de evaluación operativos.
- Cero adapter para Xiaomimimo `mimo-v2-flash` (LLM default del MVP por decisión C1.1).
- Cero `ToolRegistry` con discovery semántico ni contrato unificado `ToolWrapper`.
- Cero `HealthMonitor` ni tabla `tool_health`.
- Cero frontend de fundación (login + onboarding + listado tools).
- Cero estructura `enterprise/` o `config/{modes,playbooks,company,templates,skills,mcp}/`.

Este plan describe cómo construir esa fundación en dos fases secuenciales (F0 + F1) sin tocar el 2.0.

## Approach

Crear un subpaquete paralelo `src/vigilancia_multiagente/enterprise/` (vacío en F0, poblado en F1) que respete los ports del 2.0. Implementar `XiaomimimoClient` como adapter LLM usando el SDK OpenAI con `base_url` custom (desacoplado por C0 #6). Construir `ToolRegistry` con 3 niveles de detalle (lista mínima → ficha resumida → contenido completo) y discovery semántico que reuse `GeminiEmbeddingGateway` existente. Levantar `HealthMonitor` como proceso separado (CQS #81) que actualiza `tool_health`. Migrar 4 tablas nuevas con `tenant_id UUID NOT NULL` vía MigrationRunner + SQL crudo en `006_mvp_foundation.sql` (DDL idempotente). Habilitar `OAuthManager` con Fernet sobre `~/.vigilador/credentials/`. Implementar 4 pantallas frontend (login + onboarding paso 1 + paso 2 + listado tools) bajo `frontend/src/enterprise/` sin tocar las vistas del 2.0. Cero cambios al 2.0.

---

## Technical Context

| Area | Decision |
|------|----------|
| Lenguaje runtime | Python 3.11+ (mismo que 2.0) |
| LLM default | Xiaomimimo `mimo-v2-flash` vía SDK OpenAI con `base_url=https://platform.xiaomimimo.com/v1`. MiniMax queda como adapter opcional activable. |
| LLM adapter pattern | C0 #6: el runtime no importa SDK concreto. El nuevo cliente vive en `src/vigilancia_multiagente/infra/llm/xiaomimimo_client.py`. |
| Embeddings | Reusar `GeminiEmbeddingGateway` existente del 2.0 para discovery semántico del `ToolRegistry`. Sin nuevos providers. |
| Persistencia metadata | PostgreSQL existente del 2.0. 5 tablas nuevas vía MigrationRunner + SQL crudo (`006_mvp_foundation.sql`), multi-tenancy en schema desde día 1. |
| Vector index | Sin cambios. TurboVecIndex es target del spec 010 (F2), no se implementa aquí. |
| Tool contract | Protocolo `ToolWrapper` unificado (`enterprise/tooling/tool_wrapper.py`) con `name`, `domain`, `is_external_mcp`, `requires_auth`, `healthcheck()`, `execute()`. |
| Tool registry | `enterprise/tooling/tool_registry.py` con 3 niveles + discovery semántico + filtro por Mode placeholder. CQS: solo LEE de `tool_health`. |
| Health monitor | `enterprise/observability/health_monitor.py` como tarea cada 30 s. Circuit breaker: 3 fallos en 60 s → DOWN por 5 min. |
| Audit log | `~/.vigilador/audit/healthcheck.log` (JSONL). |
| OAuth | `enterprise/auth/oauth_manager.py` con `cryptography.fernet`. Tokens en `~/.vigilador/credentials/<provider>.enc`. |
| Observabilidad | Prometheus stubs en `/metrics` + OpenTelemetry spans con exportador consola. |
| Frontend stack | React 19 + Vite + TypeScript + Zustand (mismo que 2.0). Carpeta nueva `frontend/src/enterprise/`. |
| Frontend pantallas en F1 | login + onboarding paso 1 (`company_geo`) + paso 2 (provider LLM) + listado tools/MCPs. |
| Config | `config/settings.yaml` con `llm.default: xiaomimimo`. API keys vía env (`VT_XIAOMIMIMO_API_KEY`). |
| Migrations | MigrationRunner existente del 2.0 + SQL crudo en `src/vigilancia_multiagente/infra/db/migrations/006_mvp_foundation.sql` (ya creada). Forward-only; reversibilidad = DROP idempotente. |
| Layer enforcement | `scripts/check-layer-imports.py` debe seguir pasando sin nuevas violaciones. |
| File size guidance | ≤ 400 LOC por archivo nuevo (C0 #10), salvo justificación. |

## External Constraints

| Constraint | Impact |
|------------|--------|
| Cero breaking changes al 2.0 (constitución #5) | API `/api/v2/research/*`, 6 agentes y workstreams del 2.0 no se modifican. Tests del 2.0 deben seguir pasando al 100%. |
| Trabajar siempre en `main` (`CLAUDE.md`) | Cero feature branches automáticas. Hook `before_specify` se omite por regla del proyecto. |
| `VT_MINIMAX_API_KEY` no configurada hoy | MiniMax adapter no se valida en F0; se conserva como opcional. Validación se hace cuando se active. |
| Constitución #2 Simplicidad | Cero abstracciones especulativas. Tablas `subagents` y `pending_approvals` se crean vacías como anticipación de schema porque las exige multi-tenancy desde día 1. |
| C0 #4 TurboVecIndex único | Se documenta el contrato pero NO se implementa en este spec. El port `VectorIndex` queda intacto. |
| C0 #6 Adapter por proveedor | `XiaomimimoClient` no expone tipos del SDK OpenAI a callers; expone interfaces propias. |
| C0 #10 Modularización | Archivos copiados de Hermes (no aplica directamente en F1, llegan en F3a) deben fragmentarse antes de entrar al core. |
| C1.1 Xiaomimimo default | Default del config viene preconfigurado. MiniMax requiere flip explícito. |
| C1.6 Frontend MVP mínimo | Solo las 4 pantallas listadas. Chat, visor workstreams, configuración avanzada quedan para spec 013. |

---

## Files to Create / Modify

### New Files

| File | Purpose |
|------|---------|
| `src/vigilancia_multiagente/infra/llm/xiaomimimo_client.py` | Adapter LLM default MVP. Chat completion + tool calling vía SDK OpenAI con `base_url` custom. |
| `src/vigilancia_multiagente/enterprise/__init__.py` | Marker del subpaquete `enterprise/` (única excepción a la regla "no stubs": archivo `__init__.py` vacío es estructural, no un stub funcional). |
| `src/vigilancia_multiagente/enterprise/tooling/__init__.py` | Marker. |
| `src/vigilancia_multiagente/enterprise/tooling/tool_wrapper.py` | Protocolo `ToolWrapper` (Protocol class) + tipos comunes. |
| `src/vigilancia_multiagente/enterprise/tooling/tool_registry.py` | `ToolRegistry` con 3 niveles + discovery semántico + filtro por gating. Solo lee `tool_health`. |
| `src/vigilancia_multiagente/enterprise/tooling/tool_card.py` | Modelos `ToolCard` (lista mínima), `ToolSummary` (ficha resumida), `ToolDocs` (contenido completo). |
| `src/vigilancia_multiagente/enterprise/observability/__init__.py` | Marker. |
| `src/vigilancia_multiagente/enterprise/observability/health_monitor.py` | Proceso cada 30 s. Pinguea tools registradas y actualiza `tool_health`. |
| `src/vigilancia_multiagente/enterprise/observability/metrics.py` | Prometheus stubs (`llm_calls_total`, `tool_invocations_total`, `tool_health_status`). |
| `src/vigilancia_multiagente/enterprise/observability/tracing.py` | OpenTelemetry spans con exportador consola. |
| `src/vigilancia_multiagente/enterprise/auth/__init__.py` | Marker. |
| `src/vigilancia_multiagente/enterprise/auth/oauth_manager.py` | OAuth con Fernet + refresh básico. |
| `src/vigilancia_multiagente/infra/persistence/tool_health_repository.py` | Repository de la tabla `tool_health` (port + adapter). |
| `src/vigilancia_multiagente/infra/persistence/oauth_credentials_repository.py` | Repository de `oauth_credentials`. |
| `src/vigilancia_multiagente/infra/persistence/company_profile_repository.py` | Repository de `company_profile` (para `company_geo` del onboarding). |
| `src/vigilancia_multiagente/infra/db/migrations/006_mvp_foundation.sql` | Migración SQL cruda (ya creada): crea `tool_health`, `oauth_credentials`, `subagents`, `pending_approvals`, `company_profile`. DDL idempotente. |
| `config/settings.yaml` (nuevo) | `llm.default: xiaomimimo`, `llm.adapters.xiaomimimo.{enabled,model,api_key_env,base_url}`, `llm.adapters.minimax.{enabled,api_key_env}`. |
| `docs/audit-licenses.md` | Auditoría licencias F0 (vacío en F0 sin tools copiadas; primera entrada será spec 011 cuando se traigan archivos de Hermes). |
| `docs/postgres-readiness.md` | Documento de validación de la metadata DB en F0. |
| `frontend/src/enterprise/auth/LoginPage.tsx` | Pantalla login local. |
| `frontend/src/enterprise/onboarding/OnboardingFlow.tsx` | Wrapper de pasos del onboarding (router interno). |
| `frontend/src/enterprise/onboarding/Step1Company.tsx` | Paso 1: empresa + `company_geo`. |
| `frontend/src/enterprise/onboarding/Step2LlmProvider.tsx` | Paso 2: provider LLM + API key + test conectividad. |
| `frontend/src/enterprise/tools/ToolsListPage.tsx` | Listado tools/MCPs con estado UP/DOWN/UNCONFIGURED. |
| `frontend/src/enterprise/api/enterpriseClient.ts` | Cliente HTTP para los endpoints nuevos (`/api/v2/enterprise/*`). |
| `frontend/src/enterprise/state/onboardingStore.ts` | Store Zustand para el estado del onboarding (persistencia parcial). |
| `frontend/src/enterprise/state/toolsStore.ts` | Store Zustand para listado de tools. |
| `src/vigilancia_multiagente/api/routes/enterprise_onboarding.py` | Endpoints `POST /api/v2/enterprise/onboarding/company` y `POST /api/v2/enterprise/onboarding/llm-provider`. |
| `src/vigilancia_multiagente/api/routes/enterprise_tools.py` | Endpoint `GET /api/v2/enterprise/tools` que lee `tool_health`. |
| `src/vigilancia_multiagente/api/routes/enterprise_auth.py` | Endpoints `POST /api/v2/enterprise/auth/login` y `POST /api/v2/enterprise/auth/logout`. |
| `src/vigilancia_multiagente/api/routes/enterprise_metrics.py` | Endpoint `/metrics` Prometheus. |
| `tests/enterprise/llm/test_xiaomimimo_client.py` | Test unitarios + un test e2e contra mock server. |
| `tests/enterprise/tooling/test_tool_registry.py` | Discovery, 3 niveles, gating, no-duplicate. |
| `tests/enterprise/observability/test_health_monitor.py` | Circuit breaker, ciclo cada 30 s (con clock fake). |
| `tests/enterprise/auth/test_oauth_manager.py` | Encrypt/decrypt + refresh. |
| `tests/enterprise/migrations/test_migration_006.py` | Idempotencia (aplicar 006 dos veces sin error) + aislamiento con tablas del 2.0. |
| `tests/enterprise/api/test_onboarding_endpoints.py` | Endpoints onboarding + auth + tools list. |
| `frontend/src/enterprise/__tests__/onboarding.test.tsx` | Tests Vitest del flujo onboarding. |
| `frontend/src/enterprise/__tests__/tools-list.test.tsx` | Tests Vitest del listado tools. |

### Modified Files

| File | Changes |
|------|---------|
| `src/vigilancia_multiagente/api/app.py` | Registrar los nuevos routers `enterprise_auth`, `enterprise_onboarding`, `enterprise_tools`, `enterprise_metrics`. Cero cambios a routers existentes. |
| `src/vigilancia_multiagente/api/dependencies.py` | Wirear `XiaomimimoClient` opcional, `ToolRegistry`, `HealthMonitor` (como singleton lazy), `OAuthManager`, repositorios nuevos. No tocar wirings del 2.0. |
| `src/vigilancia_multiagente/config/settings.py` | Añadir secciones `llm.default`, `llm.adapters.*`, `enterprise.health_monitor.*`. Mantener todos los settings del 2.0 sin cambios. |
| `.env.example` | Añadir `VT_XIAOMIMIMO_API_KEY=` (único secreto nuevo). `VT_MINIMAX_API_KEY=` ya existe, conservar. Los demás fields no-secretos viven en `settings.py` con default. |
| `pyproject.toml` | Añadir deps: `openai>=1.40`, `cryptography>=42`, `apscheduler>=3.10`, `prometheus-client>=0.19`, `opentelemetry-api>=1.27`, `opentelemetry-sdk>=1.27`. Sin upgradar versiones del 2.0. |
| `frontend/package.json` | Sin deps nuevas en MVP foundation (React + Vite + Zustand + axios ya están). Solo asegurar versiones compatibles. |
| `frontend/src/App.tsx` | Añadir rutas `/login`, `/onboarding`, `/tools` bajo prefijo `/enterprise/*` sin tocar rutas del 2.0. |
| `CLAUDE.md` | Documentar `VT_XIAOMIMIMO_API_KEY` y comando para correr migración vía MigrationRunner (`python -m vigilancia_multiagente.infra.db.migration_runner`). |

---

## Constitution Check (Pre-Design)

- **Gate result**: PASS
- **Constitución evaluada**: v1.2.0 (`.specify/memory/constitution.md`).
- **Alignment**:
  - **Pensar Antes de Codificar**: 10 assumptions explícitas (A-01..A-10) en el spec. F0 dedica fase a validar conectividad DB, Xiaomimimo, embedding providers, layer imports y disponibilidad de Hermes ANTES de escribir código nuevo.
  - **Simplicidad Obligatoria**: cero abstracciones especulativas. `subagents` y `pending_approvals` se crean vacías porque las exige multi-tenancy en schema desde día 1 — no son sobreingeniería, son la mínima migración necesaria. Cero tabla `agent_modifications` todavía (D4 difiere a F5b).
  - **Modularidad Primero**: cada archivo nuevo tiene un único concern. `ToolRegistry` (query pura) y `HealthMonitor` (mutaciones) están separados explícitamente (fix CQS #81). `XiaomimimoClient` no expone tipos del SDK OpenAI al runtime.
  - **Cambios Quirurgicos y Trazables**: cero modificaciones al 2.0 más allá de los 3 archivos listados (`app.py` solo añade routers, `dependencies.py` solo añade wires, `settings.py` solo añade secciones). Tests del 2.0 deben seguir pasando al 100%.
  - **Entrega Verificable**: cada FR mapea a uno o más acceptance scenarios + success criteria. SC-002 exige tests del 2.0 al 100%. SC-003 exige migración 006 idempotente + DROP limpio.
- **Diseno de Software**: SRP (cada archivo nuevo un concern), SoC (capas API → enterprise → infra preservadas), DIP (Repository pattern para `tool_health`, `oauth_credentials`, `company_profile`), OCP (router enterprise extiende `app.py` sin tocarlo), CQS (`ToolRegistry` lee / `HealthMonitor` escribe), DRY (reusa `GeminiEmbeddingGateway` del 2.0 para discovery semántico), KISS (cero cosas no listadas en el spec).

---

## Phases

### Phase 1 — F0 Auditoría + setup (3-4 días)

1. **Validar entorno**: correr scripts de verificación que comprueben:
   - PostgreSQL responde, versión ≥ a la que usa el 2.0.
   - `VT_XIAOMIMIMO_API_KEY` set en `.env` y endpoint responde (curl).
   - `VT_EMBEDDING_API_KEY` o equivalente para embeddings del 2.0 ya configurado.
   - Estructura `documentation/hermes agent/hermes-agent/tools/` accesible (para tools de F3a futura).
   - `scripts/check-layer-imports.py` pasa sin issues sobre el 2.0 puro (baseline).
   - Estado del MigrationRunner en el repo: verificar que `infra/db/migrations/` contiene las 5 migraciones del 2.0 y que el runner las detecta correctamente. Registrar el resultado en `docs/postgres-readiness.md`.
2. **Auditoría licencias inicial**: crear `docs/audit-licenses.md` con encabezados y filas placeholder (sin contenidos todavía, las entradas reales se llenan en F3a cuando se traigan archivos de Hermes). Las 6 librerías nuevas PyPI (`openai`, `cryptography`, `apscheduler`, `prometheus-client`, `opentelemetry-*`) se documentan con versión + licencia (MIT/Apache-2.0).
3. **Crear estructura `enterprise/` vacía**: solo `__init__.py` en cada subcarpeta del listado (orchestration, modes, skills_marketplace, intelligence, triggers, auth, governance, memory, observability, ingestion, tooling, dreaming, mcp). Cero módulos funcionales.
4. **Crear estructura `config/` placeholders**: `config/{modes,playbooks,company,templates,skills,mcp}/` cada una con un `.gitkeep` o `README.md` mínimo (≤ 5 líneas) que indique "carpeta reservada para spec X".
5. **Verificar MigrationRunner**: confirmar que el MigrationRunner existente detecta y aplica `006_mvp_foundation.sql` sin conflictos con las 5 migraciones previas del 2.0. Verificar idempotencia (aplicar 2 veces sin error).

**Output**: estructura de carpetas creada, `docs/audit-licenses.md` esqueleto, `docs/postgres-readiness.md` con resultados de validación, MigrationRunner verificado, cero código de producto todavía. Tests del 2.0 siguen pasando al 100%.

### Phase 2 — F1.1 Adapter LLM + Settings (2-3 días)

1. Añadir deps a `pyproject.toml` (openai, cryptography, apscheduler, prometheus-client, opentelemetry-*).
2. Extender `config/settings.py` con secciones `llm.default`, `llm.adapters.{xiaomimimo,minimax}`.
3. Crear `infra/llm/xiaomimimo_client.py` (~250 LOC máx):
   - Clase `XiaomimimoClient` con `chat_completion(messages, tools=None, model=None) -> ChatResponse`.
   - Constructor lee API key y `base_url` de settings.
   - Usa `openai.AsyncOpenAI` internamente pero retorna tipos propios (`ChatResponse`, `ToolCall`).
   - Sin try/except defensivos; HTTPError propaga con status + body.
4. Crear `config/settings.yaml` con default `llm.default: xiaomimimo`, ambos adapters definidos.
5. Tests unitarios `tests/enterprise/llm/test_xiaomimimo_client.py`:
   - Test de chat completion con respuesta mockeada.
   - Test de tool calling con respuesta mockeada.
   - Test de error 401 → propaga exception sin swallow.
   - Test de selección por `llm.default`.

**Output**: `XiaomimimoClient` funcional + tests verdes + settings extendidos.

### Phase 3 — F1.2 ToolRegistry + ToolWrapper (3-4 días)

1. Crear `enterprise/tooling/tool_wrapper.py`:
   - Protocol `ToolWrapper`.
   - Dataclasses `ToolMetadata`, `HealthcheckResult`.
2. Crear `enterprise/tooling/tool_card.py`:
   - Modelos `ToolCard` (id, descripción ≤ 80 chars, dominios, permisos, costo, estado).
   - `ToolSummary` (schema inputs/outputs, ejemplos cortos).
   - `ToolDocs` (descripción larga + ejemplos completos).
3. Crear `enterprise/tooling/tool_registry.py` (~350 LOC máx):
   - `ToolRegistry` con `register(tool: ToolWrapper)`, `list_tools_for_role(role) -> list[ToolCard]`, `get_summary(name) -> ToolSummary`, `get_docs(name) -> ToolDocs`, `discover(role, intent) -> list[ToolCard]`.
   - `discover()` usa `GeminiEmbeddingGateway` para similitud semántica intent vs descripciones.
   - Solo LEE de `tool_health` table via `ToolHealthRepository`.
   - Aplica gating: API key faltante, status DOWN, exclusión declarada.
   - Rechaza registro duplicado por `name`.
4. Crear `infra/persistence/tool_health_repository.py` (~150 LOC):
   - `ToolHealthRepository.read_status(name) -> ToolHealthRow`.
   - `ToolHealthRepository.list_all(tenant_id) -> list[ToolHealthRow]`.
   - Solo lectura desde el lado del Registry; las escrituras viven en HealthMonitor.
5. Tests `tests/enterprise/tooling/test_tool_registry.py`:
   - Registro normal de 5 tools.
   - Duplicado falla con error.
   - `list_tools_for_role` retorna 3 niveles correctos.
   - `discover("research")` ordena por similitud (con embeddings mockeados).
   - Gating: tool sin API key oculta.
   - Performance: 200 tools registradas, list ≤ 200 ms.

**Output**: `ToolRegistry` operativo + tests verdes. Sin tools reales registradas todavía (esa es responsabilidad de spec 011).

### Phase 4 — F1.3 HealthMonitor + migración SQL (2-3 días)

1. La migración `src/vigilancia_multiagente/infra/db/migrations/006_mvp_foundation.sql` (ya creada) contiene:
   - `tool_health(name PK, tenant_id, status, last_check, fail_count, last_error, domain, requires_key)`.
   - `oauth_credentials(id, tenant_id, provider, token_encrypted, refresh_token_encrypted, expires_at, scopes)`.
   - `subagents(id, tenant_id, parent_session_id, depth, role, status, ...)` (vacía pero con schema completo).
   - `pending_approvals(id, tenant_id, kind, payload, requested_by_agent, requested_at, status)` (vacía).
   - `company_profile(id, tenant_id, name, sector, country, department, municipality, timezone)`.
   - Índices: `tenant_id` en cada una, `name` en `tool_health`, `provider` en `oauth_credentials`.
   - DDL idempotente (`CREATE TABLE IF NOT EXISTS`). Reversibilidad vía script de DROP (`DROP TABLE IF EXISTS`).
2. Verificar idempotencia: aplicar la migración 006 dos veces consecutivas sin error + verificar aislamiento (tablas del 2.0 intactas).
3. Crear `enterprise/observability/health_monitor.py` (~300 LOC):
   - `HealthMonitor` con APScheduler cada 30 s.
   - Por cada tool registrada en el `ToolRegistry`, invoca `tool.healthcheck()`.
   - Actualiza `tool_health` vía repository (escritura).
   - Circuit breaker: 3 fallos en 60 s → `status = DOWN`, no reintentar por 5 min.
   - Escribe a `~/.vigilador/audit/healthcheck.log` (JSONL).
4. Tests:
   - `tests/enterprise/migrations/test_migration_006.py`: idempotencia + aislamiento del 2.0.
   - `tests/enterprise/observability/test_health_monitor.py`: circuit breaker con clock fake.

**Output**: migración aplicada y revertible + `HealthMonitor` corriendo + tests verdes.

### Phase 5 — F1.4 OAuthManager + observability stubs (1-2 días)

1. Crear `enterprise/auth/oauth_manager.py` (~250 LOC):
   - Fernet key generada al primer arranque, persistida en `~/.vigilador/credentials/.fernet_key` con permisos restrictivos.
   - `OAuthManager.store(provider, access_token, refresh_token, expires_at, scopes)` → encripta y persiste.
   - `OAuthManager.get(provider, tenant_id)` → desencripta y retorna.
   - `OAuthManager.refresh_if_needed(provider)` → trigger refresh si `expires_at - now < 7d`.
2. Crear `enterprise/observability/metrics.py` con counters Prometheus.
3. Crear `enterprise/observability/tracing.py` con setup OpenTelemetry consola.
4. Tests `tests/enterprise/auth/test_oauth_manager.py`: encrypt/decrypt roundtrip + refresh logic.

**Output**: OAuth + observabilidad listos + tests verdes.

### Phase 6 — F1.5 API endpoints (2 días)

1. Crear los 4 routers nuevos bajo `api/routes/enterprise_*.py`:
   - `enterprise_auth.py`: `POST /api/v2/enterprise/auth/login`, `POST /api/v2/enterprise/auth/logout`.
   - `enterprise_onboarding.py`: `POST /api/v2/enterprise/onboarding/company`, `POST /api/v2/enterprise/onboarding/llm-provider`, `POST /api/v2/enterprise/onboarding/test-llm`.
   - `enterprise_tools.py`: `GET /api/v2/enterprise/tools`.
   - `enterprise_metrics.py`: `GET /metrics`.
2. Registrar routers en `api/app.py` sin tocar los routers del 2.0.
3. Wirear dependencies en `api/dependencies.py` (factory de XiaomimimoClient, ToolRegistry, HealthMonitor singleton, OAuthManager, repositorios).
4. Tests `tests/enterprise/api/test_onboarding_endpoints.py` cubriendo los 6 endpoints + auth flow.

**Output**: API enterprise expuesta + tests verdes.

### Phase 7 — F1.6 Frontend MVP foundation (3-4 días)

1. Crear estructura `frontend/src/enterprise/{auth,onboarding,tools,api,state}/`.
2. `LoginPage.tsx`: form usuario+password, post a `/api/v2/enterprise/auth/login`, persiste sesión en cookie/localStorage.
3. `OnboardingFlow.tsx`: router interno que decide qué paso mostrar según estado persistido.
4. `Step1Company.tsx`: form con campos del `company_geo`, validación, post.
5. `Step2LlmProvider.tsx`: selector provider, input API key (revelable on focus), botón "Probar conectividad" que llama `/api/v2/enterprise/onboarding/test-llm`.
6. `ToolsListPage.tsx`: tabla con columnas nombre, dominio, estado, último check, badges.
7. Tests Vitest para flujo de onboarding completo + listado tools.
8. Añadir rutas en `App.tsx` bajo `/enterprise/*`.

**Output**: 4 pantallas frontend operativas + tests verdes + onboarding completable en ≤ 5 min.

### Phase 8 — F1.7 Cierre + verificación (1-2 días)

1. Correr toda la batería `pytest` y verificar 0 regresiones en el 2.0.
2. Correr `scripts/check-layer-imports.py` sin violaciones.
3. Verificar SC-001..SC-010 del spec uno por uno con evidencia.
4. Actualizar `CLAUDE.md` con: comando de migration, env vars nuevos, comando para correr `HealthMonitor` standalone.
5. Cerrar `docs/audit-licenses.md` con todas las deps PyPI nuevas listadas.

**Output**: spec 009 completado, listo para spec 010 (F2 ingestion).

---

## Rollout Strategy

**Estrategia**: incremental por fase. Cada fase produce un artefacto verificable y los tests deben pasar antes de moverse a la siguiente.

- **Backward compatibility**: el 2.0 sigue corriendo sin cambios visibles. Frontend del 2.0 sigue accesible en sus rutas originales; nuevas rutas viven bajo `/enterprise/*`.
- **Feature flags**: cero necesarios en este spec. La existencia del subpaquete `enterprise/` no afecta al 2.0.
- **Coexistencia con 2.0**: los nuevos endpoints son aditivos. `XiaomimimoClient` se invoca solo desde código bajo `enterprise/`; el 2.0 sigue usando su LLM original.
- **Deploy**: una vez todas las fases verdes, deploy en main. Cero rollback complicado: si algo falla, el DROP de las tablas enterprise (`DROP TABLE IF EXISTS tool_health, oauth_credentials, subagents, pending_approvals, company_profile`) deja el 2.0 intacto.

---

## Success Criteria

- **SC-001**: Onboarding (login + paso 1 + paso 2) completable en ≤ 5 min mediana en navegador limpio.
- **SC-002**: `pytest` corre verde al 100% sobre todas las suites: 2.0 (sin regresiones) + nuevas suites de spec 009.
- **SC-003**: Migración 006 es idempotente: aplicarla 5 veces consecutivas sin errores ni residuos en base de datos de prueba; script de DROP limpia tablas enterprise sin afectar al 2.0.
- **SC-004**: `ToolRegistry.list_tools_for_role` ≤ 200 ms con 200 tools registradas sintéticamente.
- **SC-005**: `HealthMonitor` detecta tool caída y excluye del listado en ≤ 90 s desde primer fallo.
- **SC-006**: Llamada `mimo-v2-flash` con prompt 200 tokens responde ≤ 3 s mediana (con la cuenta del usuario en `platform.xiaomimimo.com`).
- **SC-007**: Las 4 pantallas frontend renderizan sin errores de consola en Chrome/Edge actuales.
- **SC-008**: `docs/audit-licenses.md` lista 100% de las deps PyPI nuevas (6) con licencia + versión.
- **SC-009**: Cero archivos bajo `enterprise/` con `pass`/`...`/`TODO` al cierre de F1 (regla anti-stubs).
- **SC-010**: Tool-gating cubre los 3 escenarios: sin API key, status DOWN, exclusión por caller.
- **SC-011**: `scripts/check-layer-imports.py` pasa sin nuevas violaciones.

## Constitution Check (Post-Design)

- **Status**: PASS
- **Constitución evaluada**: v1.2.0 (`.specify/memory/constitution.md`).
- **Justification**:
  - **Pensar Antes de Codificar**: F0 entera dedicada a validar entorno antes de F1. Cero código nuevo escrito antes de cerrar F0.
  - **Simplicidad Obligatoria**: 11 archivos `__init__.py` + ~18 archivos funcionales nuevos + 1 migración + 7 archivos frontend. Cada uno con razón documentada. Cero abstracciones especulativas.
  - **Modularidad Primero**: 13 carpetas en `enterprise/` cada una con un concern. `ToolRegistry`/`HealthMonitor` separados explícitamente.
  - **Cambios Quirurgicos y Trazables**: 7 archivos del 2.0 modificados (todos en modo aditivo: register router, add wire, add settings, add deps). Cero borrado o renombre.
  - **Entrega Verificable**: 11 success criteria + 8 acceptance scenarios del spec + tests por fase. Cada SC tiene método de validación claro.
  - **Diseño de Software** (SRP, SoC, DIP, OCP, CQS, DRY, KISS): aplicados en cada archivo (ver Constitution Check Pre-Design para detalle).

---

## Código deprecated (preservado por trazabilidad — constitución #5)

Este spec **NO elimina nada** del 2.0. La categoría "deprecated" significa: código que pierde su rol de **default** en la jerarquía del 3.0 pero permanece operativo como adapter opcional o ruta legacy. Se documenta para auditoría y para que `/speckit-implement` no lo borre por error.

### Deprecated soft: pierde rol de "default" pero queda activo

| Componente | Ubicación | Estado en 2.0 | Estado tras spec 009 | Acción este spec |
|---|---|---|---|---|
| `MiniMaxClient` | `src/vigilancia_multiagente/infra/llm/minimax_client.py` | LLM principal del 2.0 | **Adapter opcional** (no es default del 3.0; sigue siendo el LLM del 2.0) | Cero edits. Se conserva intacto. Wiring en `dependencies.py` solo instancia el adapter si `llm.adapters.minimax.enabled: true` en settings |
| Settings `minimax_*` | `src/vigilancia_multiagente/config/settings.py:11-13` (`minimax_api_key`, `minimax_model`, `minimax_base_url`) | Fields obligatorios para el 2.0 | Conservados; el 3.0 los referencia desde el nuevo bloque `llm.adapters.minimax` | Cero edits a los fields existentes. Se añaden los nuevos `llm.*` en T011 sin tocar los viejos |
| Variable `VT_MINIMAX_API_KEY` | `.env.example` | Variable principal del 2.0 | Conservada; ahora apunta al **adapter opcional** del 3.0 | Cero edits. El usuario sigue pudiéndola configurar para activar MiniMax en el 3.0 |
| Variable `VT_MINIMAX_MODEL` (default `MiniMax-M2.7`) | `.env.example` | Default del 2.0 | Conservada. Si MiniMax queda activado en el 3.0, sigue siendo el modelo de ese adapter | Cero edits |
| Variable `VT_MINIMAX_BASE_URL` (`https://api.minimax.io`) | `.env.example` | Default del 2.0 | Conservada | Cero edits |
| Endpoints `/api/v2/research/*` | `src/vigilancia_multiagente/api/routes/research_*.py` | API principal del 2.0 | **Sigue activa al 100%**. El 3.0 no la modifica ni la propone reemplazar | Cero edits |
| 6 agentes de rama (`AvancesAgent`, `ComercialAgent`, `RiesgoAgent`, `PiNormativaAgent`, `CompetitivoAgent`, `OportunidadesAgent`) | `src/vigilancia_multiagente/application/agents/*_agent.py` | Núcleo del 2.0 | Conservados. Spec 012 los envolverá en playbook `technology-watch` sin tocarlos | Cero edits |
| `BranchCoordinator` | `src/vigilancia_multiagente/application/execution/branch_coordinator.py` | Núcleo de paralelización del 2.0 | Conservado. Spec 012 lo invocará desde playbook | Cero edits |
| `application/pipeline/*` y workstreams `evaluation/ws_a..ws_e/` | `src/vigilancia_multiagente/application/...` | Pipeline operativo del 2.0 | Conservados al 100% — son activos del sistema (C0 #3) | Cero edits |
| `infra/embeddings/gemini_gateway.py` | `src/vigilancia_multiagente/infra/embeddings/` | Embedding provider del 2.0 | **Conservado y reusado**. El `ToolRegistry.discover()` lo inyecta como provider por defecto | Cero edits — se referencia desde DI |
| `infra/reranking/semantic_reranker.py` (si existe) | `src/vigilancia_multiagente/infra/reranking/` | Reranker del 2.0 (Cohere por API + fallback embeddings) | Conservado. Se preserva para specs posteriores cuando se haga RAG real | Cero edits |
| `infra/mcp/mcp-providers.json` y los 15 MCPs registrados | `src/vigilancia_multiagente/infra/mcp/` | MCPs activos del 2.0 | Conservados al 100%. Se mantienen registrados; el spec 010 los integrará al `ToolRegistry` del 3.0 | Cero edits |
| Frontend 2.0 (`frontend/src/{chat,analysis,agents,graph,history}/`) | `frontend/src/` | UI del 2.0 | Conservada al 100%. Las nuevas pantallas viven en `frontend/src/enterprise/` (namespace aislado) | Cero edits a las carpetas del 2.0 |

### NO existe deprecated hard en este spec

Cero archivos del 2.0 marcados para eliminación, renombre o modificación destructiva. La constitución #5 ("Cambios Quirúrgicos y Trazables") se cumple estrictamente: solo cambios aditivos a `app.py`, `dependencies.py`, `settings.py`, `.env.example`, `pyproject.toml`, `CLAUDE.md` y `frontend/src/App.tsx`.

### Reformulación de defaults (no es deprecated pero se documenta)

| Default 2.0 | Default 3.0 MVP | Motivo |
|---|---|---|
| LLM principal: MiniMax M-2.7 | LLM principal: Xiaomimimo `mimo-v2-flash` | Decisión C1.1 sesión refinamiento MVP |
| Settings `minimax_*` obligatorios | Settings `llm.adapters.{xiaomimimo,minimax}` ambos opcionales, default activo según `llm.default` | Adapter pattern C0 #6 |
| Variable de entorno principal: `VT_MINIMAX_API_KEY` | Variable principal: `VT_XIAOMIMIMO_API_KEY` | C1.1 |

---

## Código copiado / reusado

Este spec **NO copia archivos completos de Hermes** — la cosecha de Hermes empieza en spec 011 (F3a tools) con `file_tools.py` y dependencias. En este spec 009 los reusos son: (a) librerías PyPI estándar, (b) patrones del 2.0 que se replican en `enterprise/` sin copiar línea, (c) cero archivos copiados textualmente.

### Librerías PyPI nuevas (instaladas vía `pyproject.toml`)

| Paquete | Versión mínima | Licencia | Uso en spec 009 | Atribución requerida |
|---|---|---|---|---|
| `openai` | `>=1.40` | Apache-2.0 | SDK base del `XiaomimimoClient` (con `base_url` custom; OpenAI-compatible API) | No (Apache-2.0 sin obligación de header per-file) |
| `cryptography` | `>=42` | Apache-2.0 / BSD-3-Clause | Fernet symmetric encryption en `OAuthManager` | No |
| `apscheduler` | `>=3.10` | MIT | Scheduler cada 30 s del `HealthMonitor` | No (MIT sin header per-file) |
| `prometheus-client` | `>=0.19` | Apache-2.0 | Counters/gauges en `enterprise/observability/metrics.py` | No |
| `opentelemetry-api` | `>=1.27` | Apache-2.0 | Tracing API | No |
| `opentelemetry-sdk` | `>=1.27` | Apache-2.0 | TracerProvider + ConsoleSpanExporter | No |

**Auditoría obligatoria**: registrar cada paquete arriba en `docs/audit-licenses.md` como parte de T008 con: nombre, versión mínima, licencia, URL PyPI, fecha de revisión.

**Política**: solo se aceptan MIT, Apache-2.0, BSD-2/3-Clause. Cualquier paquete con GPL, AGPL, SSPL o licencia copyleft se excluye y se documenta la alternativa.

### Frontend: cero deps nuevas

`frontend/package.json` no añade librerías nuevas en spec 009. Se reusan las existentes del 2.0:
- `react@^19`, `react-dom@^19`
- `vite` + `@vitejs/plugin-react`
- `typescript`
- `zustand` (state management)
- `axios` (HTTP client)
- `vitest` + `@testing-library/react` (testing)
- `zod` (validación de forms en `Step1Company.tsx` y `Step2LlmProvider.tsx`) — verificar que ya esté instalado; si no, añadir en T042

### Archivos copiados textualmente de Hermes

**Cero en este spec**. La extracción Hermes empieza en spec 011 cuando se traiga `file_tools.py`, `file_operations.py`, `file_state.py`, `file_safety.py` y `redact.py`. Cada uno llevará en su cabecera el atributo:

```python
# Adapted from Hermes Agent — original: tools/<filename>.py
# Source repo: <upstream URL>
# License: <MIT|Apache-2.0>
# Atribución requerida por <license>.
```

`docs/audit-licenses.md` tendrá una fila por archivo copiado **en su propio spec** (spec 011), no en spec 009.

### Patrones del 2.0 reusados (referencia, no copia)

Estos componentes del 2.0 inspiran la estructura de los nuevos sin copiar código línea-a-línea:

| Patrón del 2.0 | Componente nuevo en spec 009 | Tipo de reuso |
|---|---|---|
| Repository pattern existente en `infra/persistence/` | `tool_health_repository.py`, `oauth_credentials_repository.py`, `company_profile_repository.py` | Mismo pattern (async + ports), nueva tabla |
| Pydantic BaseSettings con prefix `VT_` en `config/settings.py` | Extensión de la misma clase `Settings` con nuevos fields agrupados (sin nueva clase) | Mismo pattern |
| Inyección de dependencias en `api/dependencies.py` | Nuevas factories para `XiaomimimoClient`, `ToolRegistry`, `HealthMonitor`, `OAuthManager` | Mismo pattern |
| Estructura de routers FastAPI bajo `api/routes/*.py` | `enterprise_auth.py`, `enterprise_onboarding.py`, `enterprise_tools.py`, `enterprise_metrics.py` | Mismo pattern, prefix `/api/v2/enterprise/*` |
| Test fixtures con `MemorySessionRepository` y `FakeDatabase` (ver `tests/conftest.py`) | Tests nuevos usan los mismos fakes para no requerir PG en CI | Reuso directo |
| Frontend stack React+Vite+Zustand+axios | `frontend/src/enterprise/{auth,onboarding,tools}/` | Mismo stack, nueva carpeta |
| `scripts/check-layer-imports.py` ya valida capas del 2.0 | Se extiende cobertura para incluir `enterprise/` sin modificar el script | Mismo script, nuevo target |

---

## Variables de entorno y settings declaradas en este spec

### Variables nuevas en `.env.example`

Añadir al final del archivo (preservar todo lo existente del 2.0). **Política**: `.env.example` contiene SOLO secretos/API keys + `VT_DATABASE_URL`. Los fields no-secretos viven en `settings.py` con default (Convención sobre Configuración).

```bash
# Vigilador 3.0 — Xiaomimimo LLM (default del MVP, spec 009)
# Obtener API key en https://platform.xiaomimimo.com
VT_XIAOMIMIMO_API_KEY=
```

### Variables existentes que **no se modifican** (preservadas del 2.0)

`.env.example` conserva todas estas líneas intactas:

- `VT_APP_ENV`, `VT_APP_HOST`, `VT_APP_PORT`
- `VT_MINIMAX_API_KEY`, `VT_MINIMAX_MODEL`, `VT_MINIMAX_BASE_URL`, `VT_MINIMAX_API_HOST`, `VT_MINIMAX_IMAGE_API_KEY`
- `VT_EMBEDDING_API_KEY`, `VT_EMBEDDING_MODEL`, `VT_EMBEDDING_DIMENSIONS`, `VT_EMBEDDING_BATCH_SIZE`
- `VT_DATABASE_URL`
- `VT_MCP_DEFAULT_TIMEOUT_MS`, `VT_MCP_DEFAULT_RETRY_LIMIT`
- `VT_TAVILY_API_KEY`, `VT_EXA_API_KEY`, `VT_JINA_API_KEY`, `VT_BRAVE_API_KEY`, `VT_FIRECRAWL_API_KEY`, `VT_SERPER_API_KEY`
- `VT_COHERE_API_KEY` (reranker — sigue siendo opcional)
- `VT_OPENALEX_EMAIL`, `VT_OPENALEX_API_KEY`
- `VT_PLAYWRIGHT_HEADLESS`, `VT_MARKITDOWN_TIMEOUT`, `VT_SANDBOX_TIMEOUT`, `VT_SANDBOX_MAX_OUTPUT_SIZE`

### Fields nuevos en `src/vigilancia_multiagente/config/settings.py`

Añadir a la clase `Settings` existente (NO crear nueva clase, NO tocar fields existentes):

```python
# Bloque añadido por spec 009 — Vigilador 3.0 MVP Foundation
# Todos los fields nuevos cumplen el prefix VT_ ya configurado en SettingsConfigDict.

# === Xiaomimimo LLM (default MVP) ===
xiaomimimo_api_key: SecretStr | None = None
xiaomimimo_model: str = "mimo-v2-flash"
xiaomimimo_base_url: str = "https://platform.xiaomimimo.com/v1"

# === LLM router (selecciona adapter activo) ===
llm_default: str = "xiaomimimo"  # xiaomimimo | minimax
llm_adapter_xiaomimimo_enabled: bool = True
llm_adapter_minimax_enabled: bool = False

# === HealthMonitor (CQS) ===
health_monitor_enabled: bool = True
health_monitor_interval_sec: int = 30
health_monitor_cb_threshold: int = 3
health_monitor_cb_window_sec: int = 60
health_monitor_cooldown_sec: int = 300

# === OAuth + credentials ===
credentials_dir: str | None = None  # Resolución por defecto en código (~/.vigilador/credentials/)

# === Multi-tenancy schema-only (single-tenant runtime en MVP) ===
default_tenant_id: str = "00000000-0000-0000-0000-000000000001"

# === Observability ===
otel_exporter_endpoint: str | None = None
prometheus_metrics_path: str = "/metrics"

# === Admin local single-tenant MVP ===
admin_username: str = "admin"
```

**Notas de implementación de los settings**:

- `xiaomimimo_api_key` se valida lazy: solo es requerido si `llm_default == "xiaomimimo"`. Si está vacío, el wiring en `dependencies.py` levanta error explícito al arrancar.
- `minimax_api_key` (ya existente del 2.0) se valida lazy: solo es requerido si `llm_adapter_minimax_enabled == True`.
- `credentials_dir` se resuelve en `OAuthManager.__init__` con `pathlib.Path.home() / ".vigilador" / "credentials"` si está vacío. Se crea con permisos restrictivos (`mode=0o700` en Unix; equivalente con `icacls` en Windows).
- `default_tenant_id` se usa como `tenant_id` en todas las queries del MVP single-tenant. Las queries lo aceptan como parámetro, no hardcoded en SQL.
- `llm_default` acepta cualquier string; el wiring en `dependencies.py` valida en runtime que sea un adapter conocido.
- No se requieren imports adicionales de `typing` ni `uuid` en `settings.py`; los campos usan tipos primitivos (`str`, `bool`, `int`).

### Archivo `config/settings.yaml` (nuevo, NO confundir con `settings.py`)

Este archivo declarativo se crea en T012 para permitir override por entorno sin tocar código:

```yaml
# config/settings.yaml — overrides operacionales del Vigilador 3.0 MVP
# Las variables VT_* del .env tienen precedencia sobre este archivo.
# Este YAML sirve para entornos donde el operador edita config sin reiniciar el shell.

llm:
  default: xiaomimimo
  adapters:
    xiaomimimo:
      enabled: true
      model: mimo-v2-flash
      api_key_env: VT_XIAOMIMIMO_API_KEY
      base_url: https://platform.xiaomimimo.com/v1
    minimax:
      enabled: false
      model: MiniMax-M2.7
      api_key_env: VT_MINIMAX_API_KEY
      base_url: https://api.minimax.io

enterprise:
  health_monitor:
    enabled: true
    interval_sec: 30
    circuit_breaker:
      threshold: 3
      window_sec: 60
      cooldown_sec: 300
  multi_tenancy:
    default_tenant_id: "00000000-0000-0000-0000-000000000001"
    enforced: false  # MVP single-tenant; se activa en v3.1

observability:
  prometheus:
    metrics_path: /metrics
  otel:
    exporter: console  # console | otlp_http | otlp_grpc
    endpoint: ""       # solo aplica si exporter != console
```

**Precedencia de configuración** (de mayor a menor prioridad):
1. Variables de entorno `VT_*` cargadas de `.env`.
2. `config/settings.yaml` valores override.
3. Defaults declarados en `Settings` class de `settings.py`.

### Archivo `config/admin-credentials.yaml` (gitignored, generado en primer arranque)

Persiste el password hash del admin local. Excluido de git (`*.yaml` permitido para los demás configs, pero este path específico se añade a `.gitignore`):

```yaml
# config/admin-credentials.yaml — single-tenant MVP, NO commitear
# Se crea en primer arranque; password se pide por CLI y se persiste con bcrypt.
admin:
  username: admin
  password_hash: "$2b$12$..."  # bcrypt hash
  created_at: "2026-05-26T00:00:00Z"
```

### `.gitignore` adiciones

Añadir al `.gitignore` existente:

```
# Vigilador 3.0 MVP — credenciales locales (single-tenant)
/config/admin-credentials.yaml

# Vigilador 3.0 — datos runtime usuario (Fernet keys, audit logs, credentials encriptadas)
# Estos viven en el HOME del usuario por default; si VT_CREDENTIALS_DIR apunta
# al repo (modo desarrollo), también deben excluirse.
/.vigilador/
```

### Resumen: matriz completa de variables introducidas por spec 009

| Variable | Tipo | Default | Requerida si... | Validación |
|---|---|---|---|---|
| `VT_XIAOMIMIMO_API_KEY` | SecretStr | `None` | `VT_LLM_DEFAULT=xiaomimimo` o `VT_LLM_ADAPTER_XIAOMIMIMO_ENABLED=true` | Test conectividad en T002, T021 |
| `VT_XIAOMIMIMO_MODEL` | str | `mimo-v2-flash` | No | Validado por el endpoint Xiaomimimo |
| `VT_XIAOMIMIMO_BASE_URL` | str | `https://platform.xiaomimimo.com/v1` | No | — |
| `VT_LLM_DEFAULT` | str | `xiaomimimo` | No | Runtime validation en wiring |
| `VT_LLM_ADAPTER_XIAOMIMIMO_ENABLED` | bool | `true` | No | — |
| `VT_LLM_ADAPTER_MINIMAX_ENABLED` | bool | `false` | No | — |
| `VT_HEALTH_MONITOR_ENABLED` | bool | `true` | No | — |
| `VT_HEALTH_MONITOR_INTERVAL_SEC` | int | `30` | No | `> 0` |
| `VT_HEALTH_MONITOR_CB_THRESHOLD` | int | `3` | No | `>= 1` |
| `VT_HEALTH_MONITOR_CB_WINDOW_SEC` | int | `60` | No | `> 0` |
| `VT_HEALTH_MONITOR_COOLDOWN_SEC` | int | `300` | No | `> 0` |
| `VT_CREDENTIALS_DIR` | str | `None` (resuelve a `~/.vigilador/credentials/`) | No | Path escribible |
| `VT_DEFAULT_TENANT_ID` | str | `00000000-0000-0000-0000-000000000001` | No | UUID válido (validación runtime) |
| `VT_OTEL_EXPORTER_ENDPOINT` | str | `""` | No | URL válida si no vacío |
| `VT_PROMETHEUS_METRICS_PATH` | str | `/metrics` | No | Path con `/` al inicio |
| `VT_ADMIN_USERNAME` | str | `admin` | No | Min 3 chars |

**Total**: 16 settings nuevos en `settings.py` (con defaults), de los cuales solo `VT_XIAOMIMIMO_API_KEY` va en `.env.example` (es secreto). Los demás viven exclusivamente en `settings.py` con default (Convención sobre Configuración) y se sobreescriben opcionalmente vía variable de entorno `VT_*`.

---

## Tareas de tasks.md que materializan estos bloques

- **Deprecated audit**: cubierto implícitamente por T032 (cero edits a `MiniMaxClient`) y T011 (settings nuevos sin tocar viejos). El check de "tests del 2.0 al 100%" (T054) garantiza que el código deprecated soft sigue funcionando.
- **Código copiado**: T008 (auditar deps PyPI nuevas), T064 (cerrar `docs/audit-licenses.md`). Cero archivos copiados de Hermes en este spec — empieza en spec 011.
- **Variables de entorno**: T010 (añadir secretos a `.env.example`), T011 (extender `settings.py` con defaults no-secretos), T012 (crear `config/settings.yaml`), T037-T038 (endpoints que las consumen), T063 (documentar en `CLAUDE.md`).
