# Feature Specification: Integracion Runtime MVP — Tools Native-First, Extraccion a src/ y Cableado de Orquestacion

**Feature ID**: 021-mvp-integration-extraction
**Created**: 2026-05-29
**Status**: Draft (specification phase)
**Related plan documents**:
- [plan vigilador 3.0/00-canon-operativo-corregido.md](../../plan%20vigilador%203.0/00-canon-operativo-corregido.md) (decisiones C0)
- [plan vigilador 3.0/00b-mvp-scope-y-cronograma.md](../../plan%20vigilador%203.0/00b-mvp-scope-y-cronograma.md) (scope MVP C1, SSOT de alcance)
- [plan vigilador 3.0/01-vision-y-arquitectura.md](../../plan%20vigilador%203.0/01-vision-y-arquitectura.md) (jerarquia, estructura, stack)
- [plan vigilador 3.0/03-playbooks-y-orquestacion.md](../../plan%20vigilador%203.0/03-playbooks-y-orquestacion.md) (PlaybookRunner, ComplexityClassifier)
- [plan vigilador 3.0/04-skills-y-capacidades.md](../../plan%20vigilador%203.0/04-skills-y-capacidades.md) (marketplaces K-Dense + agency-agents)
- [plan vigilador 3.0/05-autoaprendizaje-y-autonomia.md](../../plan%20vigilador%203.0/05-autoaprendizaje-y-autonomia.md) (Dreaming basico)
- [plan vigilador 3.0/06-catalogo-tools-y-extraccion.md](../../plan%20vigilador%203.0/06-catalogo-tools-y-extraccion.md) (extraccion Hermes/OpenClaw, MCPProcessSupervisor, computer use)
- [plan vigilador 3.0/07-migracion-2.0-a-3.0.md](../../plan%20vigilador%203.0/07-migracion-2.0-a-3.0.md) (fases F1/F2/F3a/F4a/F5a)
- [plan vigilador 3.0/08-gobernanza-seguridad-y-operaciones.md](../../plan%20vigilador%203.0/08-gobernanza-seguridad-y-operaciones.md) (tool-gating, auth, PI defense)

---

## Problem Statement

La auditoria de implementacion contra el plan v3.0 revelo que el codigo **invirtio la prioridad del plan**: se construyeron subsistemas de roadmap (goal-pursuit, app-development, artifact-development, 26 archivos de Dreaming con 10 fases + 7 loops, modos CFO/Legal/Marketing/B2B/Ops) como modulos superficiales sin cablear, mientras el **backbone del MVP (F1-F5a) quedo ausente o desconectado**. Verificado en codigo:

1. **MCPs no llegan a tools**: hay 3 servidores MCP clonados en `.mcp-servers/` (arxiv, brave-search, google-scholar) + 15 providers en `infra/mcp/mcp-providers.json`, pero `ToolRegistry.register()` solo acepta objetos `ToolWrapper` y **no existe ningun puente MCP→`ToolWrapper`**. Los agentes no pueden invocar ningun MCP como tool.
2. **No hay `MCPProcessSupervisor`**: `enterprise/mcp/` esta vacio; nada conecta los 16 proveedores (ni como tool nativa ni como MCP) al runtime.
3. **TurboVecIndex ausente**: 0 referencias en `src/` y `config/`. No existe el indice vectorial unico del 3.0.
4. **Pipeline de ingestion ausente**: `enterprise/ingestion/` y `enterprise/memory/` contienen solo `__init__.py`.
5. **Orquestacion sin cablear**: no existen `PlaybookRunner` ni `ComplexityClassifier`; `technology-watch.yaml` es un YAML que **no invoca** el `BranchCoordinator` del 2.0. `ModeResolver` existe pero no esta conectado al flujo de request.
6. **Governance F1 de Hermes ausente**: faltan `file_safety`, `redact`, `path_security`, `url_safety`, `website_policy`.
7. **Skills equivocadas**: el `SkillLoader` carga skills del proyecto (`curated`/`learned`) y `.claude/skills` local, pero **no** los marketplaces externos que el plan exige (`K-Dense-AI/scientific-agent-skills`, `msitarzewski/agency-agents`).
8. **Hermes/OpenClaw sin extraer**: ambos repos estan clonados en `documentation/` pero su codigo (computer use, tools nuevas, safety) no se ha modularizado e importado a `src/`.
9. **Computer use ausente**: el catalogo declara la capability `computer_use` (navigate/screenshot/click/fill) pero `enterprise/tooling/builtin/desktop/` no existe.
10. **Auth de usuario sin sentido para esta version**: hay ~30 referencias de auth en `api/` y el plan contemplaba SSO/SAML/login; el usuario decide eliminar la autenticacion de usuario (manteniendo solo OAuth de servicio para conectores de ingestion).

Esta spec cierra esos gaps y aplica las correcciones explicitas del usuario, **respetando el alcance MVP F0-F5a** y dejando el resto del catalogo como roadmap documentado (no implementado).

---

## Scope Boundaries

### In Scope

- **Estrategia native-first de tools**: cada proveedor se internaliza como **tool nativa Python** por defecto — `WRAP-SDK` (wrapper sobre el SDK/REST del proveedor) o `CLONE-UPSTREAM` (clonar el repo del MCP **Python** con logica propia y refactorizarlo a `src/`). `MCP-EXTERNO` (proceso STDIO) queda **solo como fallback** para MCPs en TS/Go sin SDK Python. Razon: depurar/mantener codigo in-process es mas simple que un proceso MCP externo.
- **Abstraccion universal de Tool**: TODOS los proveedores se exponen como `Tool` (`ToolWrapper`) en el `ToolRegistry`, sin importar el backend (nativo `is_external_mcp=False` o MCP externo `is_external_mcp=True`). El resto del sistema y los agentes **solo ven Tools** — habilita conectar/intercambiar multiples proveedores y soportar proveedores que **no ofrecen MCP**.
- **Audit de estrategia por MCP**: script que clona/inspecciona cada repo, detecta lenguaje + SDK Python/REST + LOC y asigna estrategia (WRAP-SDK / CLONE-UPSTREAM / MCP-EXTERNO) en el catalogo SSOT.
- **Puente MCP→ToolWrapper (fallback)**: para los proveedores que permanezcan como MCP externo, un adaptador los envuelve como `ToolWrapper` (`is_external_mcp=True`) y los registra en el `ToolRegistry`.
- **`MCPProcessSupervisor`**: gestion de los procesos MCP que queden como fallback (backoff exponencial, healthcheck, status); en el caso ideal puede gestionar 0 si todo se internaliza.
- **Cliente MCP** (`enterprise/tooling/mcp_client.py`): portado/modularizado desde Hermes `tools/mcp_tool.py` (STDIO + HTTP + SSE).
- **TurboVec nativo in-process** (correccion 021-D1, revertida): adapter `TurboVecIndex` (`infra/persistence/turbovec_index.py`) que implementa el port `domain/ports/vector_index.py` usando el paquete PyPI **`turbovec`** (Rust con bindings Python sobre TurboQuant). Es el indice vectorial unico del 3.0; coherente con la estrategia native-first (021-D5). Sin servidor MCP, sin pgvector backup.
- **Pipeline de ingestion F2**: `enterprise/ingestion/{orchestrator,chunking,dedup,acl_resolver}.py` + connectors (Google Drive primero, luego OneDrive/local_fs/Outlook/Gmail). Reusa `GeminiEmbeddingGateway` y `SemanticReranker` del 2.0.
- **`enterprise/memory/frozen_snapshot.py`**: portado desde Hermes `tools/memory_tool.py` (home → `~/.vigilador/memories/`).
- **Cableado de orquestacion F4a**: `ComplexityClassifier` + `PlaybookRunner` + conexion de `ModeResolver`/`ModeContext` al flujo de request, de modo que el playbook `technology-watch` **realmente envuelve** el `BranchCoordinator` del 2.0 (6 ramas) via `plugins/technology-watch/`.
- **3 modos MVP** (`default`, `vigilancia-tech`, `CEO`) y **3 playbooks MVP** (`technology-watch`, `deep-research`, `general`) operativos.
- **Governance F1 (COPY-HERMES)**: `enterprise/governance/{file_safety,redact,path_security,url_safety,website_policy}.py` + `enterprise/governance/approvals/{approval,interrupt,slash_confirm}.py`.
- **Extraccion Hermes→src/**: modularizacion (≤400 LOC/modulo, atribucion) de los archivos Hermes del MVP listados en doc 06 §1.1/§5.
- **OpenClaw como referencia**: patrones de hard-blocks + vision routing para computer use; **no se copia codigo** (SDKs Python equivalentes existen).
- **Tools Tier 1 nuevas (documents)**: `template_render`, `docx_generate`, `pdf_generate` (la 4a, `file_system`, ya esta portada). Registradas via `ToolWrapper`.
- **Computer use Windows 11**: `enterprise/tooling/builtin/desktop/computer_use/` con backend `pyautogui` + `pygetwindow` + `mss`; capabilities navigate/screenshot/click/fill/type; gate de aprobacion antes de acciones destructivas.
- **Skills marketplaces clonados en src/**: clonar `K-Dense-AI/scientific-agent-skills` y `msitarzewski/agency-agents` dentro de `src/` + adapters `k_dense_adapter.py` y `agency_agents_adapter.py` + registro en `SkillRegistry`.
- **Eliminacion de skills `.claude` local**: remover `external:claude-local` como fuente del `SkillLoader` en runtime (supersede spec 015).
- **Eliminacion de auth de usuario**: remover SSO/SAML/OIDC, `token_auth`, `device_token`, login/sesiones de usuario y las referencias de auth en `api/`. **Conservar** `enterprise/auth/oauth_manager.py` (OAuth de servicio para conectores de ingestion).
- **Dreaming basico F5a**: `enterprise/dreaming/{scheduler,phases,reporter}.py` ejecutando **solo** `memory_consolidation` + `ingestion_sync`.
- **Governance MVP**: tool-gating (sin API key → no listada), politica no-delete, PI defense regex + Lakera, audit trail JSONL.
- **Frontend MVP (GAP-1)**: 4 superficies en `frontend/src/enterprise/` (sin login — auth de usuario eliminada por D4): onboarding, chat con seleccion de modo + visor de workstreams 2.0, estado de tools/MCPs, datos empresariales (conectores + progreso de indexacion).
- **Onboarding wizard (GAP-2)**: empresa + `company_geo` + seleccion de providers + conexion Google Workspace/Drive + primera ingestion, con endpoints `api/v2/enterprise/onboarding/*` sin auth de usuario.
- **Seleccion de providers (GAP-3)**: embeddings y reranker seleccionables (settings + UI), default Gemini/Cohere.
- **SubagentRegistry (GAP-4)**: spawn/track basico para `PlaybookRunner` (pause/resume/approval = roadmap).
- **CommandSkill (GAP-5)**: modelo de comando parametrizable en `SkillLoader` para skills de marketplace que declaren comandos (con sandbox/aprobacion).

### Out of Scope

- **Catalogo SSOT, regla <5000 LOC, contrato `ToolWrapper` y discovery semantico**: definidos por **spec 018** — 021 los **reusa y cita**, no los redefine.
- **`ToolRegistry`/`HealthMonitor`/tabla `tool_health` base + adapter LLM Xiaomimimo**: definidos por **spec 009** — 021 los reusa.
- **TurboVec via MCP**: descartado por revision de D1 (2026-05-29). Se usa nativo in-process via paquete PyPI `turbovec`, coherente con native-first (D5). Persistencia local en `~/.vigilador/turbovec/<tenant>.tq`.
- **Dreaming fases 2-4 y 6-10**, los **5-7 loops de autoaprendizaje**, `agent_modifier`, tabla SQL `agent_modifications`, `anomaly_detector`: roadmap F5b. El codigo sobre-construido de estas fases se marca roadmap, no MVP.
- **Playbooks** `decision-debate`, `market-research`, `compliance-audit`, `goal-pursuit`, `app-development`, `artifact-development`, `company-optimization`: roadmap F4b.
- **Modos** `CFO`, `Consultor Legal`, `Marketing`, `Vendedor B2B`, `Operaciones PYME`: roadmap F4c.
- **Tier 3 traducidos (TS→Python)** y **sub-tools `*_local.py`**: roadmap F3b.
- **Dominios** design/engineering/media/analytics (tools nuevas): roadmap F3b.
- **Capability tokens, PI defense por embeddings, SSO, DR/backup, Presidio**: roadmap F5b/F5d.
- **Frontend post-MVP** (artefactos, optimizacion, admin/Dreaming viewer, audit/rollback UI): roadmap F5c. Las 4 superficies MVP SI estan en scope (ver FR-046..050).
- **Canales** Telegram/WhatsApp: roadmap (MVP usa Web/SSE).

---

## Assumptions

- **A-01**: Las fuentes de extraccion ya estan clonadas: `documentation/hermes agent/hermes-agent/` y `documentation/openclaw/openclaw/`. Los MCPs ya clonados viven en `.mcp-servers/` (arxiv, brave-search, google-scholar); el resto de los 15 del 2.0 estan declarados en `infra/mcp/mcp-providers.json`. El conteo de lineas real (regla de spec 018) se valida en fase de plan/tasks.
- **A-02**: El contrato `ToolWrapper` (`name`, `domain`, `is_external_mcp`, `requires_auth`, `healthcheck() -> HealthStatus`, `execute(tool_name, args) -> ToolResult`) y `ToolRegistry` con discovery semantico ya existen por specs 009/018. Esta spec los **consume**, no los redefine.
- **A-03 (correccion usuario, decision 021-D1 revisada)**: TurboVec se consume **nativo in-process** via el paquete PyPI `turbovec` (Rust con bindings Python sobre TurboQuant). El adapter `TurboVecIndex` implementa el port `VectorIndex` (`add`, `query`, `persist`, `rebuild`) llamando directo a la libreria. Persistencia local en `~/.vigilador/turbovec/<tenant>.tq`. Coherente con native-first (D5).
- **A-04 (correccion usuario, decision 021-D2)**: Los repos de skills se clonan **dentro de `src/`**, en `src/vigilancia_multiagente/enterprise/skills_marketplace/_vendor/{k_dense,agency_agents}/`, con atribucion y licencia registradas. No se usan rutas `~/.vigilador/marketplaces/` ni `.claude/` para skills de marketplace.
- **A-05 (correccion usuario, decision 021-D3)**: La fuente `external:claude-local` se **elimina** del `SkillLoader` en runtime. El runtime no depende de `.claude/skills`. Esto supersede la parte claude-local de spec 015.
- **A-06 (correccion usuario, decision 021-D4)**: La **autenticacion de usuario** (login, sesiones, SSO/SAML/OIDC, API tokens de usuario, device tokens) se **elimina**. El OAuth de servicio (`oauth_manager.py`) se **conserva** porque los conectores de ingestion (Drive/Gmail/Outlook) lo requieren. No hay quotas por usuario (decision #29 obsoleta por C0).
- **A-07**: El LLM default del MVP es Xiaomimimo `mimo-v2-flash` (decision C1.1, spec 009). Las llamadas del `ComplexityClassifier` y del `ModeResolver` (fallback LLM) usan el adapter LLM seleccionado por config, no un SDK acoplado.
- **A-08**: Embeddings via `GeminiEmbeddingGateway` y reranking via `SemanticReranker` del 2.0 se preservan y se reusan en ingestion (decision #41 reformulada por C0).
- **A-09**: La extraccion de Hermes sigue C0/§1.1 del doc 06: cada archivo se divide en cliente/schema/normalizador/politica/cache/wrapper, ≤400 LOC por modulo, con header de atribucion y tests por modulo.
- **A-10**: El `MCPProcessSupervisor` arranca los procesos MCP que queden como **fallback**; los que sean TS/Node requieren Node como proceso externo (no en runtime del harness). En native-first este conjunto tiende a 0; la clasificacion la fija el audit (F0/F1).
- **A-11**: La constitucion v1.2.0 aplica: SRP, KISS/YAGNI, errores explicitos (sin try/except defensivos), DIP, CQS, modulos ≤400 LOC.

---

## User Scenarios & Testing

### Primary User Story

Como **ingeniero del Vigilador 3.0** que opera el MVP, quiero que **los proveedores se expongan como tools (nativas o MCP fallback) invocables, que TurboVec funcione nativo in-process, que la ingestion empresarial indexe documentos, y que un Modo seleccione un Playbook que realmente ejecute el flujo del 2.0**, para que el MVP sea operativo end-to-end (no solo modulos sueltos), respetando el alcance F0-F5a del plan.

### Secondary User Stories

- Como **agente autonomo**, quiero **descubrir y ejecutar capabilities respaldadas por MCPs externos** (busqueda, web, research, Google Workspace) a traves del `ToolRegistry`, sin saber si son in-process o procesos externos.
- Como **operador del sistema**, quiero que **los repos de skills externos (K-Dense, agency-agents) esten clonados en `src/` y registrados**, y que **el runtime no dependa de `.claude/`**, para tener un catalogo de skills versionado y trazable.
- Como **administrador**, quiero **iniciar el sistema sin pantalla de login** (auth de usuario eliminada) y que el OAuth de servicio siga permitiendo conectar Google Drive para ingestion.

### Acceptance Scenarios

1. **Given** los 16 proveedores clasificados por el audit, **When** el harness arranca, **Then** los 16 quedan registrados como `Tool` en el `ToolRegistry` (nativos `is_external_mcp=False`; los que queden como fallback arrancan como proceso via `MCPProcessSupervisor.start_all()` y quedan UP con `is_external_mcp=True`).
2. **Given** un proveedor que quede como **MCP fallback**, **When** un agente invoca `execute()` sobre su `Tool`, **Then** la llamada se delega via JSON-RPC `tools/call` al proceso MCP y retorna `ToolResult` sin logica de dominio in-process; para un proveedor **nativo** (WRAP-SDK/CLONE-UPSTREAM), `execute()` llama al SDK/REST in-process. El agente no distingue el backend.
3. **Given** un MCP que falla 3 veces en 60s, **When** el circuit breaker se dispara, **Then** el MCP se marca DOWN por 5 min y el `ToolRegistry` lo excluye del listing (tool-gating), sin tumbar el harness.
4. **Given** un MCP que falla en el arranque, **When** el supervisor reintenta, **Then** aplica backoff exponencial (1→2→4→8→16→32s, max 5 intentos) y tras 5 fallos lo marca `STUCK` y alerta, sin reintentar hasta intervencion manual.
5. **Given** el adapter `TurboVecIndex` cargado, **When** la ingestion llama `add(chunks)` y luego `query(embedding)`, **Then** la libreria nativa `turbovec` calcula y retorna resultados con citations sin proceso externo; `TurboVecIndex` implementa el port `VectorIndex`.
6. **Given** un conector Google Drive autenticado por `oauth_manager`, **When** corre la ingestion de 100 documentos, **Then** el pipeline ejecuta discovery → ACL → extract → normalize → chunk → dedup → embed (Gemini) → TurboVec → metadata, y una query semantica devuelve resultados con citas.
7. **Given** el modo `vigilancia-tech` activo, **When** el usuario envia una consulta, **Then** `ModeResolver` resuelve el modo, `ComplexityClassifier` clasifica la tarea, `PlaybookRunner` carga `technology-watch.yaml` y **ejecuta el `BranchCoordinator` del 2.0 con sus 6 ramas** sin regresiones (los tests del 2.0 siguen verdes).
8. **Given** el modo `default`, **When** el usuario hace una consulta simple, **Then** `PlaybookRunner` ejecuta el playbook `general` con 1 agente generalista y tool discovery progresivo.
9. **Given** los repos K-Dense y agency-agents clonados en `src/.../_vendor/`, **When** el `SkillLoader` carga al arranque, **Then** registra skills con `source: external:k-dense` y `external:agency-agents`, y **no** intenta cargar `external:claude-local`.
10. **Given** el sistema arrancado, **When** un cliente accede a cualquier endpoint, **Then** **no** se solicita login/token de usuario (auth de usuario eliminada), pero el flujo OAuth de servicio para conectar Drive sigue disponible.
11. **Given** la capability `computer_use` en Windows 11, **When** un agente solicita `screenshot` y luego `click`, **Then** el backend usa `mss`/`pyautogui`/`pygetwindow`; **When** solicita una accion destructiva (p.ej. cerrar app sin guardar), **Then** se exige aprobacion antes de ejecutar.
12. **Given** Dreaming basico configurado, **When** corre el cron 3 AM, **Then** ejecuta **solo** `memory_consolidation` + `ingestion_sync` y registra completitud; ninguna otra fase ni loop se ejecuta.

### Edge Cases

- **EC-01**: Un MCP de `.mcp-servers/` no esta en `config/mcp/external.yaml` → el supervisor no lo arranca; queda fuera del registry con nota en log (la declaracion en `external.yaml` es la fuente de verdad de que MCPs se levantan).
- **EC-02**: El paquete `turbovec` no esta instalado o falla la inicializacion del indice → `TurboVecIndex.healthcheck()` reporta DOWN con error explicito; la busqueda semantica se deshabilita (no fallback silencioso) y la ingestion encola pendientes hasta que se resuelva (plan de rollback F2).
- **EC-03**: Un connector OAuth pierde el token → la ingestion de esa fuente se detiene con error accionable; las demas fuentes continuan; el refresh de token se reintenta en Dreaming.
- **EC-04**: El playbook `technology-watch` se invoca desde un modo cuyo allowlist no lo incluye → `PlaybookRunner` rechaza con error explicito de incompatibilidad de modo.
- **EC-05**: Un skill de marketplace declara `required_capabilities` que no existen en el `ToolRegistry` → el `SkillLoader` lo marca `unavailable` y no lo expone, sin abortar la carga del resto.
- **EC-06**: Una tool declara una capability `delete_*` → la politica no-delete la excluye del registry al boot, salvo whitelist (`forget_user`).
- **EC-07**: La extraccion de un archivo Hermes supera 400 LOC tras modularizar → debe dividirse en mas modulos; un solo modulo >400 LOC sin justificacion documentada falla la verificacion.
- **EC-08**: `computer_use` se solicita en un entorno headless/sin display → el backend retorna error explicito de "no display disponible", no excepcion no controlada.
- **EC-09**: Existe codigo de roadmap ya construido (goal_pursuit, app_development, artifacts, 26 archivos dreaming) → 021 NO lo borra; lo marca/documenta como roadmap (no-MVP) y se asegura de que no se presente como capacidad MVP activa.

---

## Functional Requirements

### Grupo 1 — Estrategia de tools, abstraccion universal y puente MCP (gaps 1, 2)

- **FR-053**: Cada proveedor MUST construirse por estrategia **native-first**: (a) `WRAP-SDK` por defecto — tool nativa Python sobre el SDK o REST del proveedor; (b) `CLONE-UPSTREAM` — clonar el repo del MCP **Python** con logica propia y refactorizarlo a `src/.../tooling/builtin/<domain>/` (≤400 LOC/modulo, atribucion); (c) `MCP-EXTERNO` (proceso STDIO) **solo como fallback** para MCPs en TS/Go sin SDK Python.
  - *Traza*: doc 06 #11 (COPY-HERMES/WRAP-SDK/CLONE-UPSTREAM/MCP-EXTERNO); decision #50 (cero Node en runtime); spec 018 regla <5000 LOC.
- **FR-054**: TODOS los proveedores MUST exponerse como `Tool` (`ToolWrapper`) en el `ToolRegistry`, sin importar el backend: nativo (`is_external_mcp=False`) o MCP externo (`is_external_mcp=True`). `ToolRegistry`, Skills y agentes MUST operar unicamente sobre la abstraccion `Tool`; el detalle de conexion (SDK nativo vs proceso MCP) queda oculto. Habilita conectar/intercambiar multiples proveedores y soportar proveedores **sin MCP**.
  - *Traza*: spec 018 FR-012 (ToolWrapper); correccion usuario 021-D5.
- **FR-055**: El sistema MUST proveer un audit de estrategia por MCP (`scripts/audit_mcp_strategy.py`) que, por proveedor, clone/inspeccione el repo, detecte lenguaje principal + SDK Python/REST + LOC, y asigne `strategy`/`runtime` en `config/tools/catalog.yaml` (regla <5000 LOC de spec 018), fijando `loc_validated`.
  - *Traza*: spec 018 FR-005/006/007; doc 06 §4/§5.
- **FR-001**: Para los proveedores que permanezcan como **MCP externo (fallback)**, el sistema MUST proveer un adaptador `McpToolWrapper` (`enterprise/tooling/mcp_tool_wrapper.py`) que los envuelva como `ToolWrapper` con `is_external_mcp=True`, `healthcheck()` = `initialize`+`tools/list`, y `execute(tool_name, args)` que delegue por JSON-RPC `tools/call` sin logica de dominio in-process.
  - *Traza*: doc 06 §8.6 "Observabilidad uniforme", §8.2 "Tier 2 — MCPs via STDIO"; spec 018 FR-012/FR-013.
- **FR-002**: El sistema MUST registrar en el `ToolRegistry` (al arranque) cada proveedor como tool: las **nativas** (WRAP-SDK/CLONE-UPSTREAM) directamente, y las que queden como **MCP externo** via `McpToolWrapper` por cada entrada de `config/mcp/external.yaml`, tomando metadata (id, domain, capabilities, requires_key, env_var) del catalogo SSOT de spec 018.
  - *Traza*: spec 018 FR-015; doc 06 §0.
- **FR-003**: El sistema MUST proveer un cliente MCP `enterprise/tooling/mcp_client.py` (portado/modularizado desde Hermes `tools/mcp_tool.py`) que soporte transporte STDIO y HTTP/SSE, con header de atribucion.
  - *Traza*: doc 06 §1.1 `tools/mcp_tool.py`; C0 §10.
- **FR-004**: El sistema MUST proveer `MCPProcessSupervisor` (`enterprise/mcp/process_supervisor.py`, objetivo ~150 LOC) con `start_all()`, `restart(name)`, `get_status(name)` y `stop_all()`.
  - *Traza*: doc 06 §10.2; decision #64.
- **FR-005**: `MCPProcessSupervisor` MUST aplicar backoff exponencial (1, 2, 4, 8, 16, 32s) con maximo 5 reintentos; tras 5 fallos consecutivos MUST marcar el MCP como `STUCK`, emitir alerta y dejar de reintentar hasta intervencion manual.
  - *Traza*: doc 06 §10.3 "Backoff & Health".
- **FR-006**: `MCPProcessSupervisor` MUST ejecutar healthcheck por MCP cada `healthcheck_interval_sec` (default 60s) y exponer estado para tool-gating; un MCP DOWN MUST excluirse del listing del `ToolRegistry`.
  - *Traza*: doc 06 §10; decision #61 (circuit breaker), #81 (CQS).
- **FR-007**: El sistema MUST declarar en `config/mcp/external.yaml` **solo los proveedores que el audit (FR-055) deje como MCP externo (fallback)** — campos `name`, `command`, `args`, `env` (`${VAR}`), `healthcheck_interval_sec`, `restart_policy`, `log_file`; logs en `~/.vigilador/mcp-logs/<name>.jsonl`. En la estimacion native-first este conjunto tiende a 0 (los 16 proveedores pasan a tool nativa).
  - *Traza*: doc 00b "Inventario MVP Tier 2"; doc 06 §10.3.
- **FR-008**: El circuit breaker MUST disparar tras 3 fallos en 60s, marcar el MCP DOWN por 5 min y permitir auto-recuperacion; las metricas Prometheus `vigilador_mcp_process_status{name}`, `_restarts_total{name}`, `_uptime_seconds{name}` MUST exponerse.
  - *Traza*: doc 06 §10.6; decision #61.

### Grupo 2 — TurboVec nativo in-process (gap 3, correccion 021-D1 revisada)

- **FR-009**: El sistema MUST instalar y consumir el paquete PyPI **`turbovec`** in-process (Rust con bindings Python sobre TurboQuant); MUST NO declararse como MCP ni gestionarse por `MCPProcessSupervisor`.
  - *Traza*: revision de 021-D1 (2026-05-29) por consistencia con native-first (021-D5); doc 00 #4 (TurboVec indice unico).
- **FR-010**: El sistema MUST proveer un adaptador `TurboVecIndex` (`infra/persistence/turbovec_index.py`) que implemente el port `domain/ports/vector_index.py` (`add`, `query`, `persist`, `rebuild`) llamando directo a la libreria `turbovec`, sin doble stack pgvector. Persistencia local en `~/.vigilador/turbovec/<tenant>.tq`.
  - *Traza*: doc 00 #4; doc 01 "Vector index"; spec 009 stack.
- **FR-011**: `TurboVecIndex` MUST ser el indice vectorial unico consumido por la ingestion y por el discovery semantico; si el paquete no carga o el indice no inicializa, `healthcheck()` MUST reportarlo y la busqueda semantica MUST fallar con error explicito (sin fallback silencioso).
  - *Traza*: doc 07 F2 "rollback"; constitucion #4 (errores explicitos).

### Grupo 3 — Ingestion empresarial + memoria (gaps 4, 5)

- **FR-012**: El sistema MUST proveer `enterprise/ingestion/orchestrator.py` que ejecute el pipeline: discovery → resolucion ACL → extraccion → normalizacion → chunking → dedup → embeddings → TurboVec → metadata relacional → busqueda con citas.
  - *Traza*: doc 00 "Indexacion empresarial"; doc 07 F2.
- **FR-013**: El sistema MUST proveer `enterprise/ingestion/{chunking,dedup,acl_resolver}.py` y connectors en `enterprise/ingestion/connectors/`, implementando primero `google_drive.py`; `onedrive`, `local_fs`, `outlook`, `gmail` quedan declarados con el mismo port `IngestionConnector`.
  - *Traza*: doc 07 F2 tareas 1-2; doc 01 estructura `enterprise/ingestion/`.
- **FR-014**: La ingestion MUST reusar `GeminiEmbeddingGateway` (embeddings) y `SemanticReranker` (reranking) del 2.0 via sus ports, sin reemplazarlos.
  - *Traza*: doc 00 tabla stack; decision #41 reformulada.
- **FR-015**: El sistema MUST proveer `enterprise/memory/frozen_snapshot.py` (portado desde Hermes `tools/memory_tool.py`), con el home redirigido a `~/.vigilador/memories/` y header de atribucion.
  - *Traza*: doc 06 §1.1 `tools/memory_tool.py`; doc 01 `enterprise/memory/`.
- **FR-016**: Los connectors MUST obtener credenciales desde `oauth_manager` con scopes sin permisos de borrado (Drive `drive.readonly`/`drive.file`); ningun connector MUST solicitar scopes de delete.
  - *Traza*: doc 08 "no delete" en OAuth; decision #45.

### Grupo 4 — Cableado de orquestacion: Mode/Complexity/Playbook (gap 6)

- **FR-017**: El sistema MUST proveer `ComplexityClassifier` (`enterprise/orchestration/complexity_classifier.py`) que con 1 llamada LLM clasifique la tarea como `SIMPLE | MODERADA | COMPLEJA` y registre la razon (POLA).
  - *Traza*: doc 03 §ComplexityClassifier.
- **FR-018**: El sistema MUST proveer `PlaybookRunner` (`enterprise/orchestration/playbook_runner.py`) que cargue `config/playbooks/<id>.yaml`, valide `mode_compatible` contra el modo activo (rechazo explicito si incompatible), instancie los agents y ejecute el `flow` (`sequential` y `rounds` en MVP; `dag`/`hierarchical` roadmap).
  - *Traza*: doc 03 §Concepto, §Schema YAML; doc 07 F4a.
- **FR-019**: El `ModeResolver` (`enterprise/modes/mode_resolver.py`) MUST conectarse al flujo de request y resolver el modo en 5 pasos: explicito `/mode <id>` → autodetect por canal → heuristica por turno → fallback LLM → `default`. La resolucion MUST producir un `ModeContext` frozen (`enterprise/modes/mode_context.py`) inyectado en los prompts de la sesion.
  - *Traza*: doc 02 §Activacion, §Composicion (regla 5).
- **FR-020**: El `ModeLoader` (`enterprise/modes/mode_loader.py`) MUST validar en boot que los skills/playbooks/tools referenciados por cada modo existen; un modo invalido MUST excluirse del listing `/mode` con error logueado.
  - *Traza*: doc 02 §Validacion del schema.
- **FR-021**: El sistema MUST proveer 3 modos MVP en `config/modes/`: `default.yaml`, `vigilancia-tech.yaml`, `CEO.yaml`, con los campos `id`, `display_name`, `soul_overlay`, `company_subset`, `company_geo {country, department, municipality, timezone, regulatory_sources_policy}`, `skills`, `playbooks {default, allowed}`, `tools {domains, excluded}`, `mode_settings {intensity}`.
  - *Traza*: doc 00b "Modos MVP"; doc 02 §Catalogo + §company_geo (C0 #5).
- **FR-022**: El sistema MUST proveer 3 playbooks MVP en `config/playbooks/`: `technology-watch.yaml`, `deep-research.yaml`, `general.yaml`.
  - *Traza*: doc 00b "Playbooks MVP"; doc 03 §Catalogo.
- **FR-023**: El playbook `technology-watch` MUST envolver el `BranchCoordinator` del 2.0 (6 ramas) via `plugins/technology-watch/`, sin reimplementar la logica; los tests del 2.0 MUST seguir verdes.
  - *Traza*: doc 00 "El playbook technology-watch debe ser una envoltura"; doc 07 §A; doc 01 diagrama.
- **FR-024**: El playbook `general` MUST ejecutar 1 agente generalista con tool discovery progresivo; el playbook `deep-research` MUST ejecutar el patron Clarify→Plan→Approve→Execute→Fuse→Report.
  - *Traza*: doc 03 §Catalogo (filas general, deep-research); doc 00b.

### Grupo 5 — Extraccion Hermes/OpenClaw + tools nuevas + computer use (gaps 7, 9, 10, 11)

- **FR-025**: El sistema MUST extraer e importar a `src/` los archivos Hermes del MVP modularizados (≤400 LOC/modulo) en: governance `enterprise/governance/{file_safety,redact,path_security,url_safety,website_policy}.py`; approvals `enterprise/governance/approvals/{approval,interrupt,slash_confirm}.py`; tooling base `enterprise/tooling/{lazy_deps,schema_sanitizer,output_limits}.py`.
  - *Traza*: doc 06 §1.1, §5 Sprint A/B; doc 07 F1 tarea 1/4.
- **FR-026**: Cada archivo importado desde Hermes MUST incluir el header de atribucion: `# Adapted from Hermes Agent — Original file: <path> — License: <MIT|Apache-2.0>`, y cada modulo MUST tener tests unitarios.
  - *Traza*: doc 06 §7 "Licencias", C0 §10; constitucion #3.
- **FR-027**: OpenClaw MUST usarse solo como **referencia** (hard-blocks + vision routing para computer use; patrones de memoria); 021 MUST NOT copiar codigo de OpenClaw (existen SDKs Python equivalentes).
  - *Traza*: doc 06 §2 "OpenClaw — codigo copiable".
- **FR-028**: El sistema MUST implementar las 3 tools Tier 1 nuevas de `documents` (la 4a, `file_system`, ya esta portada): `template_render` (Jinja2/docxtpl), `docx_generate` (python-docx), `pdf_generate` (WeasyPrint) en `enterprise/tooling/builtin/documents/`, cada una implementando `ToolWrapper` y registrada en el `ToolRegistry`.
  - *Traza*: doc 00b "Tier 1 MVP 4 tools"; doc 06 §C1; spec 018 FR-019/020/021.
- **FR-029**: El sistema MUST implementar computer use en `enterprise/tooling/builtin/desktop/computer_use/` portando `schema.py` y `tool.py` de Hermes y reescribiendo el backend para Windows 11 con `pyautogui` + `pygetwindow` + `mss`; capabilities `navigate`, `screenshot`, `click`, `fill`, `type`.
  - *Traza*: doc 06 §1.1 computer_use, §5 Sprint G; doc 01 "Computer use", decision #12/#15.
- **FR-030**: Computer use MUST exigir un gate de aprobacion antes de acciones destructivas (cerrar sin guardar, instalar, cambiar settings del sistema) y MUST retornar error explicito si no hay display disponible.
  - *Traza*: doc 06 §2 (hard-blocks de OpenClaw); EC-08; constitucion #4.

### Grupo 6 — Skills marketplaces en src/ + eliminar claude-local (gap 8, correcciones 021-D2/D3)

- **FR-031**: El sistema MUST clonar `K-Dense-AI/scientific-agent-skills` y `msitarzewski/agency-agents` dentro de `src/vigilancia_multiagente/enterprise/skills_marketplace/_vendor/{k_dense,agency_agents}/`, registrando repo URL, licencia y hash de contenido.
  - *Traza*: doc 04 §Marketplaces externos; doc 01 stack "Skills marketplaces externos"; correccion 021-D2.
- **FR-032**: El sistema MUST proveer `k_dense_adapter.py` y `agency_agents_adapter.py` (`enterprise/skills_marketplace/`) que normalicen los skills clonados al schema unificado `SKILL.md` y produzcan `SkillCard`s con `source: external:k-dense` / `external:agency-agents`.
  - *Traza*: doc 04 §Adapters, §Schema unificado.
- **FR-033**: El `SkillLoader` MUST cargar fuentes en prioridad `curated > learned > external` y MUST NOT incluir `external:claude-local` como fuente de runtime; el runtime MUST NOT depender de `.claude/skills`.
  - *Traza*: doc 04 §Concepto; correccion usuario 021-D3 (supersede spec 015 claude-local).
- **FR-034**: El `SkillRegistry` MUST exponer descubrimiento semantico en 3 niveles (`SkillCard` → `SkillSummary` → `SkillBody`), filtrando por modo activo, permisos y salud de capabilities antes del ranking.
  - *Traza*: doc 04 §Descubrimiento semantico y carga progresiva.
- **FR-035**: El `SkillLoader` MUST marcar `unavailable` (sin abortar) cualquier skill cuyas `required_capabilities` no existan en el `ToolRegistry`.
  - *Traza*: doc 04 §Concepto; EC-05.

### Grupo 7 — Eliminacion de auth de usuario (gap 12, correccion 021-D4)

- **FR-036**: El sistema MUST eliminar la autenticacion de usuario: SSO/SAML/OIDC, `enterprise/auth/token_auth.py`, `enterprise/auth/device_token.py`, login/sesiones de usuario y las ~30 referencias de auth en `api/` (rutas, dependencias y middleware de auth de usuario).
  - *Traza*: correccion usuario 021-D4; doc 06 §6.2 (quotas/scope obsoleto); decision #30 (porcion user-facing removida).
- **FR-037**: El sistema MUST conservar `enterprise/auth/oauth_manager.py` (OAuth de servicio) y el almacenamiento Fernet en `~/.vigilador/credentials/`, porque los connectors de ingestion lo requieren.
  - *Traza*: doc 08 §OAuth; decision #53; A-06.
- **FR-038**: El sistema MUST NOT implementar quotas por usuario; conserva telemetria de costo y circuit breakers tecnicos.
  - *Traza*: doc 00 #11; doc 08 "Sin quotas"; decision #29 obsoleta.

### Grupo 8 — Dreaming basico (gap 13)

- **FR-039**: El sistema MUST proveer `enterprise/dreaming/{scheduler,phases,reporter}.py`; el `scheduler` usa APScheduler con cron 3 AM + trigger idle >10 min.
  - *Traza*: doc 05 §Scheduler; decision #17; doc 07 F5a.
- **FR-040**: Dreaming MVP MUST ejecutar **solo** dos fases: `memory_consolidation` (fase 1) e `ingestion_sync` (fase 5); el `reporter` MUST registrar completitud (log minimo).
  - *Traza*: doc 00b F5a; doc 05 tabla de fases (filas 1, 5).
- **FR-041**: Las fases 2-4 y 6-10, los loops de autoaprendizaje, `agent_modifier`, la tabla SQL `agent_modifications` y `anomaly_detector` MUST quedar como roadmap (no implementadas/activadas en MVP); el codigo de roadmap ya construido MUST marcarse como no-MVP y MUST NOT presentarse como capacidad MVP activa.
  - *Traza*: doc 00b "Lo que NO entra en MVP"; doc 05; EC-09.

### Grupo 9 — Governance MVP (tool-gating, no-delete, PI defense, audit)

- **FR-042**: El `ToolRegistry.list_tools_for_role()` MUST aplicar tool-gating: una tool con `requires_key: true` sin su `env_var` presente, o con circuit breaker DOWN, MUST NO aparecer en el listing. La consulta MUST ser de solo lectura (CQS); las mutaciones de salud las hace `HealthMonitor`.
  - *Traza*: doc 08 §Tool-gating; decisiones #18, #81.
- **FR-043**: El sistema MUST aplicar la politica no-delete: toda capability `delete_*` MUST excluirse del registry en boot, salvo whitelist en `config/settings.yaml > tools.delete_whitelist` (solo `forget_user`).
  - *Traza*: doc 08 §"Politica no delete"; decision #45.
- **FR-044**: El sistema MUST proveer `enterprise/governance/prompt_injection_detector.py` (~200 LOC) con deteccion por heuristicas regex + dataset Lakera; toda entrada externa (emails, PDFs, scraping, mensajes) MUST pasar por el detector antes del LLM; un positivo MUST poner el contenido en cuarentena (no se pasa al LLM) y registrar el evento. La capa por embeddings queda roadmap.
  - *Traza*: doc 08 §PI defense; decision #106; doc 00b ("PI defense regex en MVP").
- **FR-045**: El sistema MUST registrar audit trail en JSONL en `~/.vigilador/audit/events_<fecha>.jsonl` (invocaciones de tools, llamadas LLM, decisiones del ComplexityClassifier, spawns de subagentes) con un index table para consultas; la tabla SQL `agent_modifications` queda roadmap.
  - *Traza*: doc 08 §"Audit estructurado JSONL"; doc 00b F5a.

### Grupo 10 — Frontend MVP + Onboarding + Seleccion de providers (gaps GAP-1, GAP-2, GAP-3)

- **FR-046**: El frontend MVP MUST exponer 4 superficies en `frontend/src/enterprise/` (sin pantalla de login, auth de usuario eliminada por D4): (a) onboarding, (b) chat con seleccion de modo (`/mode`) + visor de workstreams del 2.0 + historial basico, (c) estado de tools/MCPs (UP/DOWN), (d) datos empresariales (conectores + progreso de indexacion).
  - *Traza*: doc 00b C1.6 "Frontend MVP"; doc 00 #1; doc 07 F4a.
- **FR-047**: El onboarding wizard MUST capturar empresa + `company_geo` (pais/departamento/municipio/timezone) + seleccion de providers (LLM/embeddings/reranker) + conexion Google Workspace/Drive + lanzar la primera ingestion, completable en <15 min.
  - *Traza*: doc 07 §"Onboarding wizard"; doc 00b criterio de salida #2.
- **FR-048**: El backend MUST exponer endpoints `api/v2/enterprise/onboarding/*` (crear `config/company/*.md`, fijar `company_geo`, fijar providers, iniciar ingestion) **sin requerir auth de usuario**.
  - *Traza*: doc 07 §Onboarding; correccion D4.
- **FR-049**: El sistema MUST permitir seleccionar el provider de embeddings y el de reranker (settings `embedding_provider`/`reranker_provider`, persistidos en config), con default `gemini`/`cohere` reusando los gateways del 2.0.
  - *Traza*: doc 00 #2; doc 02; doc 07 F2 tarea 5. (GAP-3)
- **FR-050**: La superficie de tools/MCPs MUST listar las capacidades MVP con estado UP/DOWN (desde `MCPProcessSupervisor`/`HealthMonitor`) y permitir configurar API keys (tool-gating).
  - *Traza*: doc 00b C1.6; doc 08 §Tool-gating.

### Grupo 11 — SubagentRegistry (gap GAP-4)

- **FR-051**: El sistema MUST proveer `SubagentRegistry` (`enterprise/orchestration/subagent_registry.py`) con spawn/track basico (tabla `subagents`: id, tenant_id, parent_session_id, parent_agent_id, depth, role, status), usado por `PlaybookRunner` cuando un agente spawnea subagentes; pause/resume/approval gates quedan roadmap (F4b).
  - *Traza*: doc 03 §SubagentRegistry.

### Grupo 12 — CommandSkill (gap GAP-5)

- **FR-052**: El `SkillLoader` MUST soportar el modelo `CommandSkill` (comando parametrizable: `parameters`, `permissions`, `preconditions`, `requires_sandbox`, `hash`) para skills de los marketplaces que declaren comandos; ningun comando destructivo MUST exponerse sin aprobacion o sandbox.
  - *Traza*: doc 04 §CommandSkill; doc 00 #7.

---

## Key Entities

- **McpToolWrapper** (`enterprise/tooling/mcp_tool_wrapper.py`): adaptador que presenta un MCP externo como `ToolWrapper` (`is_external_mcp=True`); su `execute()` delega por JSON-RPC al proceso MCP. Es el puente que faltaba entre MCPs y el `ToolRegistry`.
- **MCPProcessSupervisor** (`enterprise/mcp/process_supervisor.py`): gestor del pool de **procesos MCP que queden como fallback (0..N)**; arranque, backoff, healthcheck, status, parada. ~150 LOC.
- **mcp_client** (`enterprise/tooling/mcp_client.py`): cliente MCP (STDIO/HTTP/SSE) portado de Hermes.
- **TurboVecIndex** (`infra/persistence/turbovec_index.py`): adapter del port `VectorIndex` que usa el paquete PyPI `turbovec` (Rust + bindings Python) **in-process**; indice vectorial unico del 3.0. Persistencia local en `~/.vigilador/turbovec/<tenant>.tq`.
- **IngestionOrchestrator** (`enterprise/ingestion/orchestrator.py`): coordina el pipeline discovery→ACL→extract→normalize→chunk→dedup→embed→TurboVec→metadata→search.
- **IngestionConnector** (port + `connectors/google_drive.py` ...): fuente de documentos empresariales; Drive primero.
- **ModeResolver / ModeContext / ModeLoader** (`enterprise/modes/`): resolucion de modo (5 pasos), snapshot frozen de contexto, validacion en boot.
- **ComplexityClassifier** (`enterprise/orchestration/complexity_classifier.py`): clasifica SIMPLE/MODERADA/COMPLEJA con 1 llamada LLM.
- **PlaybookRunner** (`enterprise/orchestration/playbook_runner.py`): carga playbook YAML, valida compatibilidad de modo, instancia agents, ejecuta flow.
- **Mode (`config/modes/<id>.yaml`)**: persona empresarial = soul_overlay + company_subset + company_geo + skills + playbooks + tools allowlist. MVP: `default`, `vigilancia-tech`, `CEO`.
- **Playbook (`config/playbooks/<id>.yaml`)**: flujo declarativo multi-agente. MVP: `technology-watch` (envuelve BranchCoordinator 2.0), `deep-research`, `general`.
- **SkillLoader / SkillRegistry / k_dense_adapter / agency_agents_adapter** (`enterprise/skills_marketplace/`): carga skills de `curated`/`learned`/marketplaces clonados en `_vendor/`; descubrimiento semantico de 3 niveles; sin dependencia de `.claude`.
- **computer_use** (`enterprise/tooling/builtin/desktop/computer_use/`): control de escritorio Windows 11 (pyautogui/pygetwindow/mss) con gate de aprobacion.
- **Dreaming (scheduler/phases/reporter)** (`enterprise/dreaming/`): ciclo nocturno; MVP solo `memory_consolidation` + `ingestion_sync`.
- **oauth_manager** (`enterprise/auth/oauth_manager.py`): OAuth de servicio para conectores (conservado); el resto de auth de usuario se elimina.
- **PromptInjectionDetector** (`enterprise/governance/prompt_injection_detector.py`): regex + Lakera; cuarentena de entradas externas.
- **Frontend MVP** (`frontend/src/enterprise/{onboarding,chat,sources,admin}`): 4 superficies sin login (onboarding, chat+modo+workstreams, estado tools/MCPs, datos empresariales).
- **OnboardingService** (`api/v2/enterprise/onboarding/*`): endpoints que crean COMPANY + `company_geo` + providers + primera ingestion, sin auth de usuario.
- **SubagentRegistry** (`enterprise/orchestration/subagent_registry.py`): spawn/track basico (tabla `subagents`, depth/status); pause/resume/approval = roadmap.
- **CommandSkill** (modelo en `enterprise/skills_marketplace/`): comando parametrizable (params/permissions/preconditions/requires_sandbox/hash) para skills de marketplace.

---

## Success Criteria

- **SC-001**: El `ToolRegistry` registra los 16 proveedores como **Tools** (nativas WRAP-SDK/CLONE-UPSTREAM + las que queden como MCP externo fallback); `tools list` muestra las 20+ capacidades MVP activas (4 documents + 16 proveedores); los proveedores que permanezcan como MCP arrancan UP via `MCPProcessSupervisor`.
- **SC-002**: Un agente ejecuta `execute()` sobre al menos un proveedor de cada dominio MVP (search, web, research, documents) y recibe `ToolResult` valido **sin saber el backend** (nativo `vigilador.tools.<domain>.<id>` o MCP externo `vigilador.mcp_ext.<id>`).
- **SC-003**: Matar un proceso MCP dispara restart con backoff y, tras recuperarse, vuelve a UP; 5 fallos lo dejan `STUCK` con alerta (verificable en logs/metricas).
- **SC-004**: `TurboVecIndex` (paquete `turbovec` PyPI) implementa el port `VectorIndex`; ingesta 100 documentos sample via Google Drive y una query semantica devuelve ≥1 resultado con cita; con la libreria no instalada o el indice no inicializado, la busqueda falla con error explicito (no fallback silencioso).
- **SC-005**: `/mode vigilancia-tech` ejecuta `technology-watch` que corre el `BranchCoordinator` del 2.0 con sus 6 ramas; la suite de tests del 2.0 sigue 100% verde (cero regresiones).
- **SC-006**: `/mode default` ejecuta `general` (1 agente) y responde usando tools descubiertas; `/mode CEO` ejecuta `deep-research` con salida structured + free-form.
- **SC-007**: Los repos K-Dense y agency-agents estan clonados bajo `src/.../_vendor/`; el `SkillLoader` registra skills `external:k-dense` y `external:agency-agents` y **no** referencia `.claude` (grep de `claude-local` en el path de runtime = 0).
- **SC-008**: El arranque del sistema no requiere login/token de usuario; no quedan rutas/dependencias de auth de usuario en `api/` (grep de auth de usuario = 0), y `oauth_manager` sigue permitiendo conectar Drive.
- **SC-009**: `computer_use` ejecuta screenshot + click en Windows 11; una accion destructiva exige aprobacion; sin display retorna error explicito.
- **SC-010**: Todo modulo importado desde Hermes ≤400 LOC y con header de atribucion (verificable por script); OpenClaw no aporta archivos de codigo (solo referencia).
- **SC-011**: Dreaming basico ejecuta solo `memory_consolidation` + `ingestion_sync` en el cron; ninguna otra fase/loop se ejecuta (verificable en el reporte/log).
- **SC-012**: Tool-gating oculta tools sin API key; politica no-delete excluye capabilities `delete_*` salvo whitelist; PI defense pone en cuarentena un payload `"ignore previous instructions"` antes del LLM; audit JSONL registra los eventos.
- **SC-013**: Un usuario nuevo completa el onboarding (empresa + `company_geo` + providers + conectar Drive + primera ingestion) en <15 min, sin pantalla de login; las 4 superficies del frontend MVP cargan operativas.
- **SC-014**: La superficie de tools/MCPs lista las capacidades con estado UP/DOWN y permite configurar API keys; una tool sin key aparece como no disponible (tool-gating).
- **SC-015**: `SubagentRegistry` registra un spawn con `depth`/`status`; un `CommandSkill` de marketplace con comando destructivo exige aprobacion/sandbox antes de ejecutarse.

---

## Delivery Constraints

- **Constitucion v1.2.0 — Simplicidad (#2) / KISS / YAGNI**: 021 implementa solo el backbone MVP (F1-F5a). No implementa playbooks/modos/loops/dominios de roadmap; el codigo de roadmap ya construido se marca, no se expande.
- **Constitucion v1.2.0 — Modularidad (#3) / SRP / SoC**: la extraccion Hermes se divide en cliente/schema/normalizador/politica/cache/wrapper; modulos ≤400 LOC; cero monolitos.
- **Constitucion v1.2.0 — Manejo de errores estricto (#4)**: `turbovec` no cargado, OAuth invalido, computer_use sin display y MCP fallback incompatible MUST propagar errores explicitos; sin `try/except` defensivos ni fallbacks silenciosos.
- **Constitucion v1.2.0 — Cambios quirurgicos (#5)**: el 2.0 no se toca; `technology-watch` envuelve el `BranchCoordinator` existente; `infra/mcp/mcp-providers.json` se referencia sin alterar.
- **Constitucion v1.2.0 — DIP**: connectors implementan `IngestionConnector`; `TurboVecIndex` implementa `VectorIndex`; `ModeResolver` implementa `ModeResolutionStrategy`; los proveedores se exponen via `ToolWrapper`.
- **Constitucion v1.2.0 — LSP**: las implementaciones del port `VectorIndex` (incluyendo `TurboVecIndex`) y de `ToolWrapper` (nativos y `McpToolWrapper`) MUST ser sustituibles por su contrato base sin alterar precondiciones ni postcondiciones — `TurboVecIndex.query()` se comporta igual que cualquier otra impl del port; `McpToolWrapper.execute()` retorna el mismo `ToolResult` que una tool nativa.
- **Constitucion v1.2.0 — ISP**: `ToolWrapper` expone solo `name`/`domain`/`is_external_mcp`/`requires_auth`/`healthcheck`/`execute` — sin atributos `tags`/`capabilities` que viven en el `CatalogEntry` (spec 018); ports separados (`VectorIndex`, `IngestionConnector`, `ModeResolutionStrategy`, `ChannelAdapter`) en lugar de una interfaz monolitica.
- **Constitucion v1.2.0 — CQS (#81)**: `list_tools_for_role` solo lee `tool_health`; `HealthMonitor` escribe.
- **C0 doc 00**: TurboVec indice unico (sin pgvector backup); preservar workstreams/ports/infra del 2.0; COPY-HERMES modularizado; sin quotas por usuario.
- **C1 doc 00b**: alcance MVP = 20 capacidades, 4 dominios, 3 modos, 3 playbooks, Dreaming basico. Manda sobre el alcance de otros docs.
- **Correcciones del usuario (021-D1..D5)**: TurboVec **nativo in-process** (D1 revisada); clonar marketplaces en `src/`; eliminar `.claude` local del runtime; eliminar auth de usuario (conservar OAuth de servicio); native-first + abstraccion universal de Tool.

---

## Dependencies

### Depends on

- **spec 009-mvp-foundation**: provee `ToolWrapper` (protocolo base), `ToolRegistry` + discovery, `HealthMonitor`, tabla `tool_health`, adapter LLM Xiaomimimo. 021 los consume.
- **spec 018-tool-mcp-catalog-ssot**: provee el catalogo SSOT (`config/tools/catalog.yaml`), la regla <5000 LOC y los campos de clasificacion. 021 los reusa para registrar los MCPs y tools.
- **spec 010-jerarquia-agent-mode-skill** y **spec 011-mode-router-catalogo-geo**: proveen las definiciones base de Mode/ModeResolver/company_geo. 021 las cablea al runtime.
- **2.0 preservado**: `application/execution/branch_coordinator.py` + 6 agentes de rama; `infra/embeddings/gemini_gateway.py`; `infra/reranking/semantic_reranker.py`; `infra/mcp/mcp-providers.json`.
- **Provider SDKs / REST** (para tools WRAP-SDK nativas): p.ej. `tavily-python`, `exa-py`, `firecrawl-py`, `arxiv`, `scholarly`, `pyalex`, `playwright`, `markitdown`, `google-api-python-client` (lista exacta a confirmar por el audit FR-055).
- **Paquete `turbovec`** (PyPI): indice vectorial nativo (Rust + bindings Python sobre TurboQuant) consumido in-process por `TurboVecIndex`.

### Depended on by

- **spec 015-skill-marketplace-claude-local**: 021 **supersede** su mecanismo claude-local (lo desactiva en runtime) y lo reemplaza por marketplaces clonados en `src/`.
- **Roadmap F3b/F4b/F4c/F5b**: las tools restantes, playbooks avanzados, modos restantes y loops de autoaprendizaje se construyen **sobre** el backbone que 021 deja operativo (MCP bridge, ingestion, orquestacion, Dreaming).

---

## Correcciones explicitas del usuario registradas en esta spec

| ID | Correccion | FR/Assumption |
|---|---|---|
| 021-D1 | TurboVec **nativo in-process** (PyPI `turbovec`) — revisada el 2026-05-29 por consistencia con D5 native-first | A-03, FR-009/010/011 |
| 021-D2 | Clonar los 2 repos de skills **dentro de `src/`** | A-04, FR-031 |
| 021-D3 | **Eliminar** skills `.claude` local del runtime | A-05, FR-033 |
| 021-D4 | **Eliminar** auth de usuario; conservar OAuth de servicio | A-06, FR-036/037/038 |
| 021-D5 | **Native-first**: internalizar proveedores como tools nativas (WRAP-SDK/CLONE-UPSTREAM), MCP-EXTERNO solo fallback; **TODO proveedor = `Tool`** en el registry | FR-053/054/055 |
| (gap) | MCPs clonados/declarados **se pasan a tools** | FR-001/002/007 |
| (gap) | Clonacion + extraccion de **Hermes y OpenClaw**, tools nuevas, **computer use** | FR-025/027/028/029 |
| GAP-1 | **Frontend MVP** (4 superficies, sin login) incorporado a 021 | FR-046/050 |
| GAP-2 | **Onboarding wizard** + endpoints sin auth | FR-047/048 |
| GAP-3 | **Seleccion de providers** embeddings/reranker | FR-049 |
| GAP-4 | **SubagentRegistry** basico | FR-051 |
| GAP-5 | **CommandSkill** model | FR-052 |
