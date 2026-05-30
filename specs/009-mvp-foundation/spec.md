# Feature Specification: Vigilador 3.0 MVP Foundation

**Feature ID**: 009-mvp-foundation
**Created**: 2026-05-26
**Status**: Draft (specification phase)
**Related plan documents**:
- [plan vigilador 3.0/00-canon-operativo-corregido.md](../../plan%20vigilador%203.0/00-canon-operativo-corregido.md)
- [plan vigilador 3.0/00b-mvp-scope-y-cronograma.md](../../plan%20vigilador%203.0/00b-mvp-scope-y-cronograma.md)
- [plan vigilador 3.0/07-migracion-2.0-a-3.0.md](../../plan%20vigilador%203.0/07-migracion-2.0-a-3.0.md) (fases F0 + F1)

---

## Problem Statement

El producto actual (Vigilador Tecnológico 2.0) ofrece vigilancia tecnológica con 6 agentes de rama, pero está limitado a un solo caso de uso. El usuario quiere evolucionar a un **agente autónomo empresarial multi-propósito (Vigilador 3.0)** que asista al empresario en cualquier área de la empresa.

El plan completo del 3.0 cubre 79 capacidades, 17 dominios, 7 modos y 8 playbooks — un alcance que no puede entregarse en una sola iteración sin riesgo de dispersión. Por eso se acordó (decisión **C1** de esta sesión) reducir el alcance inicial a un **MVP** de 20 capacidades, 4 dominios activos, 3 modos y 3 playbooks.

Antes de implementar capacidades empresariales (modos, skills marketplace, playbooks avanzados, autoaprendizaje), el sistema necesita una **fundación estable** sobre la que construir todo lo demás: el subpaquete `enterprise/` paralelo al 2.0, el adapter del nuevo LLM default (Xiaomimimo `mimo-v2-flash`), el `ToolRegistry` con discovery semántico, persistencia mínima nueva y la primera versión del frontend como consola del producto.

Sin esta fundación, las fases posteriores (F2 ingestion, F3a tools, F4a modos+playbooks, F5a Dreaming básico) no pueden empezar.

**Este spec cubre las fases F0 (Auditoría + setup) y F1 (Foundation) del MVP**. Las siguientes fases (F2-F5a) serán specs separados (010, 011, 012, 013).

---

## Scope Boundaries

### In Scope

- **F0 — Auditoría y setup**:
  - Validar supuestos clave del entorno del usuario (PostgreSQL existente, espacio Hermes copiable, conectividad a Xiaomimimo API, embedding/reranker providers ya configurados, ports del 2.0).
  - Auditoría de licencias de los archivos a copiar de Hermes en F1 (≤30 archivos de cabecera) y de paquetes PyPI nuevos (≤10 paquetes en F1).
  - Crear estructura de carpetas `src/vigilancia_multiagente/enterprise/` (vacía, sin código de producto) más placeholders bajo `config/{modes,playbooks,company,templates,skills,mcp}/`.
  - Setup de migraciones (MigrationRunner + SQL crudo en `006_mvp_foundation.sql`) sobre la metadata DB existente, con DDL idempotente (forward-only; reversibilidad = DROP idempotente).
  - Setup de Prometheus + OpenTelemetry como stubs invocables aunque no exporten métricas todavía.
  - Documento de auditoría (`docs/audit-licenses.md`) con tabla de origen→destino→licencia→atribución por cada archivo copiado y paquete instalado.

- **F1 — Foundation**:
  - **Adapter LLM `XiaomimimoClient`** (`infra/llm/xiaomimimo_client.py`) que soporta:
    - Chat completion vía API OpenAI-compatible (`base_url=https://platform.xiaomimimo.com/v1`).
    - Tool calling estilo OpenAI con schema JSON.
    - Modelo default `mimo-v2-flash`.
    - Manejo de errores con propagación de contexto (sin try/except defensivos).
  - **Selector de provider** en `config/settings.yaml` (`llm.default: xiaomimimo`) que el código resuelve a través de un port `LlmClient` ya existente o nuevo, manteniendo `MiniMaxClient` del 2.0 como adapter opcional activable.
  - **Contrato `ToolWrapper` unificado** (`enterprise/tooling/tool_wrapper.py`): protocolo común para tools internas y MCPs externos, con `name`, `domain`, `is_external_mcp`, `requires_auth`, `healthcheck()`, `execute(tool_name, args)`.
  - **`ToolRegistry` con discovery semántico** (`enterprise/tooling/tool_registry.py`):
    - Tres niveles de detalle: lista mínima (id + descripción corta + dominios + permisos + costo + estado), ficha resumida (schema inputs/outputs + ejemplos cortos), contenido completo (docs largas).
    - Búsqueda por embeddings sobre descripciones/tags/uso histórico/modo activo (los embeddings usan el provider ya seleccionable del 2.0; no implementa nuevos embeddings en este spec).
    - Filtrado por Mode activo (en este spec hay placeholder; los modos reales llegan en spec 011).
    - Solo LEE de `tool_health`; mutaciones del estado de tools/MCPs son responsabilidad de `health_monitor.py` (CQS).
  - **`HealthMonitor`** (`enterprise/observability/health_monitor.py`): proceso que cada 30 s pinguea tools registradas vía `healthcheck()` y actualiza la tabla `tool_health(name, status, last_check, fail_count, last_error)`.
  - **Persistencia base**:
    - Migración SQL cruda (`006_mvp_foundation.sql`) ejecutada por el MigrationRunner que crea: `tool_health`, `oauth_credentials`, `subagents`, `pending_approvals`. Todas con `tenant_id UUID NOT NULL` desde día 1 (multi-tenancy en schema, single-tenant en runtime).
    - La tabla `agent_modifications` (audit trail D4) **NO** entra en este spec; se difiere a F5b (spec posterior).
  - **Auth básico**:
    - `enterprise/auth/oauth_manager.py` con Fernet-encrypted tokens en `~/.vigilador/credentials/`.
    - Refresh automático placeholder (la lógica completa de scopes restrictivos se materializa en spec 010 al integrar Google Workspace MCP).
  - **Tool-gating**: el `ToolRegistry` aplica gating cuando falta API key declarada por la tool, sin necesidad de modos todavía.
  - **Frontend de fundación**:
    - Pantalla de login (auth básica password + sesión).
    - Pantalla de onboarding paso 1 — datos de empresa (nombre, sector, `company_geo`: país/departamento/municipio/timezone).
    - Pantalla de onboarding paso 2 — selección de provider LLM (Xiaomimimo default + form para API key + test de conectividad).
    - Pantalla mínima de listado de tools/MCPs con estado UP/DOWN/UNCONFIGURED (alimentada por `tool_health`).
    - Resto de superficies frontend (chat, modos, workstreams visor, indexación, artefactos, optimización, admin) viven en specs posteriores.
  - Tests unitarios y E2E para los componentes nuevos (XiaomimimoClient, ToolRegistry, HealthMonitor, OAuthManager, migración SQL 006, las 4 pantallas frontend).

### Out of Scope

- **Cualquier ingesta de documentos** (Google Workspace MCP integration, TurboVecIndex, embeddings de chunks) → spec 010 (F2).
- **MCP `google-workspace-mcp` y `MCPProcessSupervisor`** → spec 010 (F2-F3a).
- **Las 4 tools Tier 1 nuevas** (`file_system`, `template_render`, `docx_generate`, `pdf_generate`) → spec 011 (F3a).
- **Modos `default`, `Vigilancia Tech`, `CEO`** y sus YAMLs → spec 012 (F4a).
- **Playbooks `technology-watch`, `deep-research`, `general`** y `PlaybookRunner` → spec 012 (F4a).
- **`ComplexityClassifier`, `SubagentRegistry`, `ModeResolver`** → spec 012 (F4a).
- **Frontend chat, visor de workstreams, configuración avanzada de tools/MCPs** → spec 013 (F4a frontend).
- **Dreaming, PI defense, audit trail SQL, 5 loops de autoaprendizaje** → specs F5a+ (post-MVP-foundation).
- **Goal-pursuit, app-development, artifact-development, company-optimization** → roadmap completo (post-MVP).
- **Capability tokens, anomaly detector, SSO/SAML, DR, compliance avanzado** → roadmap completo.
- **Sub-tools `*_local.py`** → roadmap completo (post-MVP).
- **Marketplaces externos** (K-Dense, agency-agents, Claude local) → roadmap completo.
- **Cambios al 2.0**: cero. La API `/api/v2/research/*` y los 6 agentes de rama no se tocan.

---

## Assumptions

- **A-01**: La metadata DB existente del 2.0 permite ejecutar migraciones SQL crudas vía MigrationRunner sin afectar tablas del 2.0 (se opera con DDL idempotente `IF NOT EXISTS` / `IF EXISTS`).
- **A-02**: El operador tiene credenciales válidas para Xiaomimimo (API key emitida por `platform.xiaomimimo.com`) y conectividad de red hacia ese endpoint.
- **A-03**: Los providers de embeddings y reranker del 2.0 (`GeminiEmbeddingGateway`, `SemanticReranker`/Cohere) están funcionales con sus API keys ya configuradas; este spec NO requiere instalar embeddings locales.
- **A-04**: El sistema target inicial corre en Windows 11 con Python 3.11+; el frontend corre en navegador moderno (Chrome/Edge ≥ 120).
- **A-05**: El proyecto trabaja directamente sobre `main` por regla del `CLAUDE.md`. No se crean feature branches automáticas por hooks.
- **A-06**: El usuario es **single-tenant** en MVP: todas las queries usan el mismo `tenant_id` hardcoded; la multi-tenancy operativa se activa en una versión posterior sin migración adicional.
- **A-07**: Frontend usa el stack existente (React 19 + Vite + TypeScript + Zustand) extendido bajo `frontend/src/enterprise/`. No se introducen nuevos frameworks UI.
- **A-08**: La API key de Xiaomimimo se carga vía variable de entorno `VT_XIAOMIMIMO_API_KEY` (mismo patrón `VT_*` del 2.0).
- **A-09**: La estructura de carpetas `src/vigilancia_multiagente/enterprise/` se crea **vacía** en F0; los módulos solo aparecen cuando F1 los implementa. Cero archivos placeholder con `pass` o stubs ficticios — el código se introduce solo cuando hay funcionalidad real.
- **A-10**: La auditoría de licencias se hace antes de copiar cada archivo de Hermes y antes de instalar cada paquete PyPI nuevo. Si un archivo o paquete no es MIT/Apache-2.0 compatible, se excluye y se documenta la alternativa.

---

## User Scenarios & Testing

### Primary User Story

Como **operador del Vigilador 3.0** (admin que instala el sistema en una empresa), quiero **arrancar el sistema por primera vez y completar un onboarding mínimo** que conecte el LLM, registre mi empresa con su geografía y muestre el estado del catálogo de tools, **para validar que la fundación del 3.0 está operativa** antes de comenzar a indexar documentos o configurar modos.

### Acceptance Scenarios

1. **Given** una instalación limpia con Python 3.11+ y la metadata DB existente del 2.0 corriendo, **When** ejecuto el setup del Vigilador 3.0 y aplico la migración inicial, **Then** las tablas nuevas (`tool_health`, `oauth_credentials`, `subagents`, `pending_approvals`) existen con `tenant_id UUID NOT NULL` y las tablas del 2.0 no se modifican.

2. **Given** el sistema arrancado y mi `VT_XIAOMIMIMO_API_KEY` configurada, **When** abro el frontend e ingreso a la pantalla de onboarding paso 2 y pulso "Probar conectividad", **Then** el sistema realiza una llamada de chat completion mínima a `mimo-v2-flash` y muestra "Conectividad OK" con el modelo respondido + latencia en ms.

3. **Given** el onboarding paso 1 abierto, **When** ingreso nombre de empresa, sector, país, departamento, municipio y timezone, **Then** los datos se persisten y la siguiente sesión los carga como `company_geo` frozen snapshot.

4. **Given** el sistema con un par de tools registradas en el `ToolRegistry`, **When** consulto el frontend de listado de tools/MCPs, **Then** veo cada tool con su nombre, dominio, estado UP/DOWN/UNCONFIGURED, último check y badge de "API key faltante" cuando aplica.

5. **Given** una tool registrada cuya API key falta en el entorno, **When** un agente (cualquier consumidor del `ToolRegistry`) pide el listado de tools disponibles para un rol, **Then** esa tool **no aparece** en el listado (tool-gating funcional).

6. **Given** el `HealthMonitor` corriendo, **When** una tool registrada falla 3 veces seguidas en 60 s, **Then** la tabla `tool_health` refleja status DOWN, `fail_count = 3` y el listado del `ToolRegistry` excluye la tool hasta el cooldown.

7. **Given** la migración 006_mvp_foundation.sql aplicada por el MigrationRunner, **When** ejecuto el script de DROP idempotente de las tablas enterprise, **Then** las 5 tablas nuevas se eliminan y la metadata DB queda en el estado pre-spec-009 sin afectar las tablas del 2.0.

8. **Given** el frontend de onboarding completo, **When** un nuevo admin de empresa atraviesa los pasos 1 y 2, **Then** el tiempo total mediano de onboarding es ≤ 5 minutos.

### Edge Cases

- **EC-01**: API key de Xiaomimimo inválida o vencida → el botón "Probar conectividad" muestra mensaje claro identificando el error (401/403) y enlace a `platform.xiaomimimo.com` para regenerar.
- **EC-02**: La metadata DB no responde durante migración → la migración falla atómicamente sin dejar tablas a medias; el log indica el paso exacto donde falló.
- **EC-03**: `~/.vigilador/credentials/` no es accesible (permisos) → el `OAuthManager` falla con error explícito al primer write y el sistema marca el sub-sistema como "credentials_unavailable" en el frontend.
- **EC-04**: Una tool intenta registrarse con `name` duplicado → el `ToolRegistry` rechaza el segundo registro con error y log estructurado.
- **EC-05**: El `HealthMonitor` no puede contactar a una tool externa por timeout → la tool queda en status `DOWN`, `last_error` = "timeout" y se reintenta en el próximo ciclo de 30 s.
- **EC-06**: El usuario completa solo el paso 1 del onboarding y cierra el navegador → al volver, el frontend carga los datos parciales persistidos y permite continuar desde el paso 2 sin re-ingresar.
- **EC-07**: Provider LLM secundario (MiniMax) activado pero sin API key → el `ToolRegistry` lo lista como UNCONFIGURED; sin impacto sobre el funcionamiento con Xiaomimimo activo.

---

## Functional Requirements

### Auditoría y setup (F0)

- **FR-001**: El sistema MUST validar la conectividad y versión de la metadata DB existente antes de aplicar cualquier migración nueva.
- **FR-002**: El sistema MUST generar `docs/audit-licenses.md` con una fila por cada archivo copiado y por cada paquete PyPI instalado, listando: origen, destino, licencia, atribución y versión.
- **FR-003**: El sistema MUST crear las carpetas `src/vigilancia_multiagente/enterprise/{orchestration,modes,skills_marketplace,intelligence,triggers,auth,governance,memory,observability,ingestion,tooling,dreaming,mcp}/` vacías + `config/{modes,playbooks,company,templates,skills,mcp}/` vacías. Cero archivos placeholder con stubs ficticios.
- **FR-004**: El sistema MUST crear la migración `006_mvp_foundation.sql` ejecutable por el MigrationRunner existente, con DDL idempotente (IF NOT EXISTS / IF EXISTS) que permita reaplicación sin error.

### Adapter LLM Xiaomimimo (F1)

- **FR-005**: El sistema MUST proveer un adapter `XiaomimimoClient` que invoque chat completion contra el endpoint OpenAI-compatible de Xiaomimimo usando `mimo-v2-flash` como modelo default.
- **FR-006**: El sistema MUST soportar tool calling vía schema JSON en `XiaomimimoClient`, retornando la lista de tool_calls del LLM al caller para que el orquestador las despache.
- **FR-007**: El sistema MUST cargar la API key desde la variable de entorno `VT_XIAOMIMIMO_API_KEY` sin permitir hardcodearla en código.
- **FR-008**: El sistema MUST permitir cambiar el LLM activo editando `config/settings.yaml > llm.default`; el cambio se toma al próximo arranque del proceso (no requiere recompilación).
- **FR-009**: El sistema MUST conservar el `MiniMaxClient` existente del 2.0 sin modificaciones y ofrecerlo como adapter opcional activable.
- **FR-010**: El adapter `XiaomimimoClient` MUST propagar errores HTTP con su código y cuerpo de respuesta, sin try/except defensivos que oculten causas.

### ToolRegistry con discovery semántico (F1)

- **FR-011**: El sistema MUST proveer un protocolo `ToolWrapper` común que cualquier tool (interna o MCP externo) debe implementar con: `name`, `domain`, `is_external_mcp`, `requires_auth`, `healthcheck()`, `execute(tool_name, args)`.
- **FR-012**: El `ToolRegistry` MUST exponer 3 niveles de detalle para sus tools: lista mínima (≤ 80 caracteres por tool), ficha resumida (schema + ejemplos), contenido completo (docs largas).
- **FR-013**: El `ToolRegistry.discover(role, intent)` MUST devolver candidatos ordenados por similitud semántica entre el `intent` del agente y descripciones/tags de las tools.
- **FR-014**: El `ToolRegistry.list_tools_for_role` MUST ser una **query pura** (solo lee de `tool_health`); cualquier mutación de estado vive en `HealthMonitor`.
- **FR-015**: El `ToolRegistry` MUST aplicar tool-gating por: ausencia de API key declarada, status DOWN reportado por `HealthMonitor`, y exclusión declarada por el caller (placeholder para Mode-filter que llegará en spec 012).
- **FR-016**: El `ToolRegistry` MUST rechazar el registro de una tool cuyo `name` ya existe, propagando error con log estructurado.

### HealthMonitor (F1)

- **FR-017**: El sistema MUST ejecutar `HealthMonitor` como tarea recurrente cada 30 s que invoca `healthcheck()` en cada tool registrada y actualiza la tabla `tool_health`.
- **FR-018**: El `HealthMonitor` MUST aplicar circuit breaker: tras 3 fallos en 60 s, marcar status DOWN y mantenerlo así por al menos 5 min antes de reintentar.
- **FR-019**: El `HealthMonitor` MUST escribir un log estructurado JSONL en `~/.vigilador/audit/healthcheck.log` con cada ciclo.

### Persistencia base (F1)

- **FR-020**: La migración inicial MUST crear las tablas `tool_health`, `oauth_credentials`, `subagents`, `pending_approvals` con columna `tenant_id UUID NOT NULL` en cada una.
- **FR-021**: La migración MUST ser reversible mediante script de DROP idempotente (`DROP TABLE IF EXISTS`) que elimine las 5 tablas enterprise dejando la metadata DB en el estado pre-spec-009. El MigrationRunner es forward-only; la reversibilidad se expresa como DDL de limpieza, no como downgrade.
- **FR-022**: Las tablas nuevas MUST tener índices que respeten patrones de consulta esperados (al menos índice por `tenant_id` en cada tabla y por `name` en `tool_health`).

### OAuth básico (F1)

- **FR-023**: El sistema MUST encriptar tokens OAuth con Fernet antes de escribir a `~/.vigilador/credentials/`.
- **FR-024**: El sistema MUST refrescar automáticamente tokens próximos a expirar (< 7 días) cuando se invocan; el refresh fallido se registra como warning y se sigue intentando en próxima invocación.

### Frontend de fundación (F1)

- **FR-025**: El frontend MUST exponer una pantalla de login con autenticación por usuario+contraseña local (single-tenant MVP).
- **FR-026**: El frontend MUST exponer pantalla de onboarding paso 1 (datos de empresa: nombre, sector, país, departamento, municipio, timezone) que persiste como `company_geo`.
- **FR-027**: El frontend MUST exponer pantalla de onboarding paso 2 (selección de provider LLM, captura de API key, botón "Probar conectividad") que ejecuta una llamada real al adapter activo.
- **FR-028**: El frontend MUST exponer pantalla de listado de tools/MCPs alimentada por `tool_health`, con columnas: nombre, dominio, estado UP/DOWN/UNCONFIGURED, último check, último error si aplica.
- **FR-029**: El frontend MUST permitir retomar onboarding parcial: si el usuario cierra sesión a mitad de paso 1 o paso 2, al volver retoma desde el último paso completado.

### Observabilidad mínima (F1)

- **FR-030**: El sistema MUST exponer endpoint `/metrics` con Prometheus stubs (counters básicos para `llm_calls_total`, `tool_invocations_total`, `tool_health_status`) — sin necesidad de dashboard final todavía.
- **FR-031**: El sistema MUST emitir spans OpenTelemetry para: arranque del proceso, llamada LLM, healthcheck de tool. Sin exportador remoto obligatorio (consola basta).

### Constitución y constraints (transversal)

- **FR-032**: El sistema MUST mantener cero breaking changes a la API `/api/v2/research/*` y a los 6 agentes de rama del 2.0; los tests del 2.0 MUST seguir pasando al 100% tras este spec.
- **FR-033**: Toda nueva carpeta o archivo bajo `src/vigilancia_multiagente/enterprise/` MUST respetar la separación de capas verificada por `scripts/check-layer-imports.py`.
- **FR-034**: Cada archivo nuevo MUST ser ≤ 400 LOC siempre que sea posible (regla C0 #10 — modularizar); excepciones requieren justificación documentada.

---

## Key Entities

- **Tool registration record (`tool_health`)**: snapshot del estado operacional de una tool registrada. Atributos: `name` (PK), `tenant_id`, `status` (UP/DOWN/UNCONFIGURED), `last_check`, `fail_count`, `last_error`, `domain`, `requires_key`. Vive en metadata DB.
- **OAuth credential (`oauth_credentials`)**: tokens encriptados para integraciones externas. Atributos: `id`, `tenant_id`, `provider`, `token_encrypted`, `refresh_token_encrypted`, `expires_at`, `scopes`. Vive en metadata DB; cuerpos encriptados en `~/.vigilador/credentials/`.
- **Subagent placeholder (`subagents`)**: tabla preparada para registros futuros del `SubagentRegistry` (spec 012). En este spec se crea vacía como anticipación de schema.
- **Pending approval placeholder (`pending_approvals`)**: tabla preparada para approvals residuales (specs F5b+). En este spec se crea vacía.
- **Company profile (`company_geo`)**: contexto geográfico/empresarial inicial. Atributos: `name`, `sector`, `country`, `department`, `municipality`, `timezone`. Vive en config persistido por el frontend onboarding (puede vivir en `config/company/identity.md` + tabla `company_profile`, decisión técnica en `/speckit-plan`).
- **LLM provider config**: registro declarativo del provider activo y opcionales. Atributos: `default_provider`, `adapters_enabled[]`. Vive en `config/settings.yaml`.

---

## Success Criteria

- **SC-001**: Un operador nuevo completa el onboarding (pasos 1 + 2) en ≤ 5 min mediana con Xiaomimimo configurado y conectividad validada.
- **SC-002**: Tras instalar y aplicar la migración inicial, los tests existentes del 2.0 siguen pasando al 100% (cero regresiones).
- **SC-003**: La migración 006 es idempotente: aplicarla 5 veces consecutivas en una metadata DB de prueba no produce errores ni residuos, y el script de DROP limpia las tablas enterprise sin afectar al 2.0.
- **SC-004**: El `ToolRegistry` lista en ≤ 200 ms el set de tools registradas para un rol arbitrario, incluso con 200 tools registradas (estrés sintético).
- **SC-005**: El `HealthMonitor` detecta una tool caída y la excluye del listado del `ToolRegistry` en ≤ 90 s desde el primer fallo (3 fallos × 30 s ciclo).
- **SC-006**: Una llamada a `mimo-v2-flash` con prompt de 200 tokens responde en ≤ 3 s mediana (sujeto a SLA de Xiaomimimo, validar en F0).
- **SC-007**: El frontend de onboarding completo está accesible y funcional en navegadores Chrome/Edge actuales, sin errores de consola.
- **SC-008**: La auditoría de licencias documenta el 100% de los archivos copiados y paquetes PyPI nuevos antes de cerrar F0.
- **SC-009**: Cero archivos del subpaquete `enterprise/` quedan con stubs vacíos (`pass`, `...`, `TODO`) al cierre de F1 — todo lo escrito debe tener funcionalidad implementada o no estar.
- **SC-010**: La tool-gating responde correctamente al 100% de los escenarios de prueba: tool sin API key oculta, tool DOWN oculta, tool UNCONFIGURED visible solo para admin.
- **SC-011**: `scripts/check-layer-imports.py` pasa sin nuevas violaciones de capas tras incorporar el subpaquete `enterprise/` (FR-033).

---

## Traceability Matrix

Cada FR se ancla a un acceptance scenario (AS) y/o success criterion (SC), y a la fase del plan que lo materializa. Permite verificar cobertura sin huérfanos.

| FR | Acceptance scenario | Success criterion | Fase plan |
|----|---------------------|-------------------|-----------|
| FR-001 | AS-1 | SC-002 | Phase 1 (F0) |
| FR-002 | — | SC-008 | Phase 1 (F0) |
| FR-003 | — | SC-009 | Phase 1 (F0) |
| FR-004 | AS-1, AS-7 | SC-003 | Phase 1 (F0) |
| FR-005 | AS-2 | SC-006 | Phase 2 (F1.1) |
| FR-006 | AS-2 | SC-006 | Phase 2 (F1.1) |
| FR-007 | AS-2 | — | Phase 2 (F1.1) |
| FR-008 | — | — | Phase 2 (F1.1) |
| FR-009 | EC-07 | SC-002 | Phase 2 (F1.1) |
| FR-010 | EC-01 | — | Phase 2 (F1.1) |
| FR-011 | AS-4 | SC-010 | Phase 3 (F1.2) |
| FR-012 | AS-4 | SC-004 | Phase 3 (F1.2) |
| FR-013 | — | SC-004 | Phase 3 (F1.2) |
| FR-014 | AS-4 | — | Phase 3 (F1.2) |
| FR-015 | AS-5, EC-07 | SC-010 | Phase 3 (F1.2) |
| FR-016 | EC-04 | — | Phase 3 (F1.2) |
| FR-017 | AS-6 | SC-005 | Phase 4 (F1.3) |
| FR-018 | AS-6, EC-05 | SC-005 | Phase 4 (F1.3) |
| FR-019 | — | — | Phase 4 (F1.3) |
| FR-020 | AS-1 | SC-003 | Phase 4 (F1.3) |
| FR-021 | AS-7 | SC-003 | Phase 4 (F1.3) |
| FR-022 | — | SC-004 | Phase 4 (F1.3) |
| FR-023 | EC-03 | — | Phase 5 (F1.4) |
| FR-024 | — | — | Phase 5 (F1.4) |
| FR-025 | — | SC-007 | Phase 7 (F1.6) |
| FR-026 | AS-3 | SC-001, SC-007 | Phase 7 (F1.6) |
| FR-027 | AS-2 | SC-001, SC-007 | Phase 7 (F1.6) |
| FR-028 | AS-4 | SC-007, SC-010 | Phase 7 (F1.6) |
| FR-029 | EC-06 | SC-001 | Phase 7 (F1.6) |
| FR-030 | — | — | Phase 5 (F1.4) |
| FR-031 | — | — | Phase 5 (F1.4) |
| FR-032 | — | SC-002 | Phase 8 (F1.7) |
| FR-033 | — | SC-011 | Phase 8 (F1.7) |
| FR-034 | — | SC-009 | Transversal (todas las fases) |

**Cobertura**: 34/34 FR mapeados a fase. Los FR sin AS ni SC directo (FR-008, FR-019, FR-024, FR-030, FR-031) se validan vía tests unitarios de su fase, no vía criterio de aceptación de negocio.

---

## Delivery Constraints

- **Constitución v1.2.0 — Cambios quirúrgicos (#5)**: el 2.0 no se toca. Cualquier renombre de `vigilancia_multiagente` se rechaza.
- **Constitución v1.2.0 — Simplicidad obligatoria (#2)**: este spec NO introduce abstracciones especulativas. Cada componente listado tiene una razón concreta documentada en el plan v3.0.
- **Constitución v1.2.0 — Modularidad primero (#3)**: cada componente bajo `enterprise/` cumple SRP y un único concern por archivo. Regla C0 #10: ≤ 300-400 LOC por archivo.
- **Constitución v1.2.0 — Manejo de errores estricto (#4)**: cero try/except defensivos. Errores propagan con contexto. Circuit breakers solo en boundaries (`HealthMonitor`).
- **C0 #4** (canon): TurboVecIndex se diseña como índice vectorial único del 3.0, pero NO se implementa todavía en este spec — solo se documenta que el port `VectorIndex` será su contrato. La materialización es spec 010 (F2).
- **C0 #6** (canon): el adapter LLM debe estar desacoplado del SDK concreto. `XiaomimimoClient` usa el SDK OpenAI con `base_url` custom; el resto del runtime nunca importa `openai` directamente.
- **C1.1** (MVP scope): Xiaomimimo es el default; MiniMax permanece como adapter opcional.
- **C1.6** (MVP scope): solo 4 pantallas frontend en este spec; el chat, visor workstreams y configuración avanzada van en spec 013.
- **CLAUDE.md** (regla del proyecto): trabajar directamente sobre `main`; cero feature branches automáticas.
- **Atribución obligatoria**: cada archivo copiado de Hermes lleva header `# Adapted from Hermes Agent — original: tools/<filename>.py — License: <MIT|Apache-2.0>`.

---

## Dependencies on previous specs

- **spec 002-008** (todo el 2.0): el spec 009 los respeta. No depende de cambios a ninguno; depende de que sigan corriendo.

## Specs descendientes que dependen de este

- **spec 010 — MVP F2 ingestion**: depende de `XiaomimimoClient`, `ToolRegistry`, `HealthMonitor` y migración 006 aplicada por MigrationRunner.
- **spec 011 — MVP F3a tools**: depende del contrato `ToolWrapper`.
- **spec 012 — MVP F4a modos+playbooks**: depende de `ToolRegistry` y `subagents`.
- **spec 013 — MVP F4a frontend chat+workstreams**: depende de las 4 pantallas frontend de F1.
