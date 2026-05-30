# Implementation Plan: Integracion Runtime MVP — Tools Native-First, Extraccion a src/ y Cableado de Orquestacion

**Feature ID**: 021-mvp-integration-extraction
**Created**: 2026-05-29
**Spec**: [spec.md](spec.md)

## Problem

El backbone del MVP (F1-F5a del plan v3.0) esta ausente o desconectado, mientras se sobre-construyo codigo de roadmap. Verificado en codigo: no hay puente MCP→`ToolWrapper` (los MCP de `.mcp-servers/` y `infra/mcp/mcp-providers.json` no llegan al `ToolRegistry`), no hay `MCPProcessSupervisor`, no existe `TurboVecIndex`, `enterprise/ingestion/` y `enterprise/memory/` estan vacios, no hay `PlaybookRunner`/`ComplexityClassifier` (asi que `technology-watch.yaml` no invoca el `BranchCoordinator` 2.0), faltan los archivos de governance F1 de Hermes, el `SkillLoader` usa `.claude` local en vez de los marketplaces externos, Hermes/OpenClaw (clonados en `documentation/`) no se han extraido a `src/`, no hay computer use, y hay auth de usuario que el usuario quiere eliminar. Ademas, codigo de roadmap (goal_pursuit 8py, app_development 12py, artifacts 10py, dreaming con 7 loops + 9 fases extra, 5 modos y 4 playbooks de roadmap) esta construido pero fuera del alcance MVP.

## Approach

Implementar el backbone MVP en el orden de fases del plan (F1→F2→F3a→F4a→F5a), aplicando las 5 correcciones del usuario (021-D1 **TurboVec nativo in-process** via paquete PyPI `turbovec` (revisada 2026-05-29 por consistencia con D5); D2 clonar marketplaces dentro de `src/`; D3 eliminar `.claude` del runtime; D4 eliminar auth de usuario conservando OAuth de servicio; **D5 estrategia native-first de tools + abstraccion universal `ToolWrapper`: internalizar proveedores como tools nativas — WRAP-SDK/CLONE-UPSTREAM — con MCP-EXTERNO solo como fallback, y exponer TODO proveedor como `Tool`**). Cada subsistema nuevo se conecta por su port (DIP) y se registra en el runtime real (no modulos sueltos). El codigo de roadmap ya construido se **marca deprecated/out-of-MVP** (no se borra) y se documenta su reactivacion futura. La extraccion de Hermes sigue C0 (≤400 LOC/modulo, atribucion, tests por modulo); OpenClaw es solo referencia. Reusa specs 009 (ToolWrapper/ToolRegistry/LLM) y 018 (catalogo SSOT) sin redefinirlos.

---

## Technical Context

| Area | Decision |
|------|----------|
| Estrategia de tools (native-first) | Default `WRAP-SDK` (tool nativa Python sobre SDK/REST del proveedor); `CLONE-UPSTREAM` para MCPs Python con logica propia (refactor a `src/`); `MCP-EXTERNO` solo **fallback** (TS/Go sin SDK). Clasificacion por audit (FR-055). |
| Abstraccion universal de Tool | TODO proveedor se expone como `ToolWrapper` en `ToolRegistry` (nativo `is_external_mcp=False` o MCP `is_external_mcp=True`); agentes/Skills solo ven Tools. Habilita multi-proveedor y proveedores sin MCP. |
| Puente MCP→tools (fallback) | `McpToolWrapper` envuelve los MCPs que queden externos; `execute()` delega JSON-RPC `tools/call` via `mcp_client`. Registro con metadata del catalogo SSOT (spec 018). |
| MCP client | Portado de Hermes `tools/mcp_tool.py` → `enterprise/tooling/mcp_client.py` (STDIO + HTTP + SSE), modularizado ≤400 LOC. |
| Supervisor | `enterprise/mcp/process_supervisor.py` ~150 LOC; backoff exp 1→32s, max 5, luego STUCK; healthcheck 60s; arranca **solo los MCPs que queden como fallback** (0..N) desde `config/mcp/external.yaml`. |
| TurboVec (D1 revisada) | **Nativo in-process** via paquete PyPI `turbovec` (Rust + bindings Python). Adapter `TurboVecIndex` (`infra/persistence/turbovec_index.py`) implementa el port `domain/ports/vector_index.py` llamando directo a la libreria. Persistencia local `~/.vigilador/turbovec/<tenant>.tq`. Sin pgvector backup. Indice vectorial unico. Coherente con native-first (D5). |
| Ingestion | `enterprise/ingestion/{orchestrator,chunking,dedup,acl_resolver}.py` + `connectors/google_drive.py` (primero). Reusa `GeminiEmbeddingGateway` + `SemanticReranker` del 2.0 por sus ports. |
| Orquestacion | `ComplexityClassifier` (1 llamada LLM) + `PlaybookRunner` (carga YAML, valida `mode_compatible`, instancia agents, flow sequential/rounds) + `ModeResolver` conectado al request → `ModeContext` frozen. |
| technology-watch | Envuelve el `BranchCoordinator` 2.0 (6 ramas) via `plugins/technology-watch/`. No reimplementa. |
| Skills (D2/D3) | Clonar K-Dense + agency-agents en `src/.../skills_marketplace/_vendor/{k_dense,agency_agents}/`. Adapters normalizan a SKILL.md unificado. `SkillLoader` quita `external:claude-local`. |
| Extraccion Hermes | COPY-HERMES modularizado: governance safety (file_safety/redact/path_security/url_safety/website_policy) + approvals + tooling base + memory + computer_use. Atribucion obligatoria. |
| Computer use | `enterprise/tooling/builtin/desktop/computer_use/`; backend Win11 `pyautogui`+`pygetwindow`+`mss`; gate de aprobacion en acciones destructivas. |
| Auth (D4) | Eliminar auth de usuario (route `enterprise_auth`, deps de usuario en `api/`); conservar `oauth_manager.py` (OAuth de servicio para conectores). Sin quotas. |
| Dreaming (F5a) | Solo `memory_consolidation` + `ingestion_sync`. Resto (loops + 9 fases) deprecated→roadmap. |
| Governance MVP | tool-gating (CQS, READ-ONLY), no-delete, PI defense regex+Lakera, audit JSONL. |
| LLM | Xiaomimimo `mimo-v2-flash` default (spec 009/C1.1) via adapter; sin acople a SDK. |

## External Constraints

| Constraint | Impact |
|------------|--------|
| Constitucion v1.2.0 #5 Cambios Quirurgicos | El 2.0 no se toca. `BranchCoordinator`, 6 ramas, `infra/mcp/mcp-providers.json`, embeddings/reranker del 2.0 intactos; se envuelven/reusan por port. |
| Constitucion v1.2.0 #2 / YAGNI | Solo backbone MVP. Roadmap (goal_pursuit, app_development, artifacts, loops, fases extra, 5 modos, 4 playbooks) NO se implementa ni expande; se marca deprecated. |
| Constitucion v1.2.0 #3 / SRP | Extraccion Hermes dividida en cliente/schema/normalizador/politica/cache/wrapper, ≤400 LOC. |
| Constitucion v1.2.0 #4 errores explicitos | `turbovec` no cargado, OAuth invalido, computer_use sin display → error explicito, sin fallback silencioso ni `try/except` defensivo. |
| Spec 009 + 018 | `ToolWrapper`, `ToolRegistry`, discovery, catalogo SSOT y regla <5000 LOC ya definidos. 021 los consume. |
| OpenClaw es TypeScript | No se copia codigo; solo referencia conceptual (hard-blocks + vision routing). |
| TurboVec nativo (D1 revisada) | Requiere `pip install turbovec`; validar disponibilidad de la libreria en F0/F2; si falla, EC-02 (busqueda deshabilitada con error). |
| Node disponible | Solo los proveedores que queden como **MCP externo fallback** (TS/Node) requieren Node; en native-first tiende a 0. Lo determina el audit (F0/plan). |
| Credenciales | Google Workspace MCP requiere OAuth (VT_GOOGLE_CLIENT_ID/SECRET). Sin credenciales → tool-gating lo oculta. |

---

## Variables

### Variables de entorno (`.env` / `.env.example`)

**Existentes (preservadas)**: `VT_DATABASE_URL`, `VT_XIAOMIMIMO_API_KEY` (LLM default), `VT_MINIMAX_API_KEY`, `VT_MINIMAX_IMAGE_API_KEY`, `VT_EMBEDDING_API_KEY` (Gemini), `VT_COHERE_API_KEY` (reranker), `VT_TAVILY_API_KEY`, `VT_EXA_API_KEY`, `VT_BRAVE_API_KEY`, `VT_SERPER_API_KEY`, `VT_JINA_API_KEY`, `VT_FIRECRAWL_API_KEY`, `VT_OPENALEX_API_KEY`, `VT_GOOGLE_FACTCHECK_API_KEY`.

**Nuevas (021)**:

| Variable | Uso | Fase |
|---|---|---|
| `VT_GOOGLE_CLIENT_ID` | OAuth client del `google-workspace-mcp` (Drive/Gmail/Docs) | F2/F3a |
| `VT_GOOGLE_CLIENT_SECRET` | OAuth secret del `google-workspace-mcp` | F2/F3a |

> Las credenciales OAuth de servicio se cifran con Fernet en `~/.vigilador/credentials/` (no en `.env`). `.env` solo guarda client_id/secret de arranque.

### Settings (`src/vigilancia_multiagente/config/settings.py`)

**Existentes (relevantes)**: `mcp_default_timeout_ms=30000`, `mcp_default_retry_limit=2`, `enterprise_enabled=True`, `modes_dir="config/modes"`, `playbooks_dir="config/playbooks"`, `skills_sources_enabled` (a modificar), `dreaming_enabled=False`.

**Nuevas/Modificadas (021)**:

| Campo | Valor default | Accion | FR |
|---|---|---|---|
| `mcp_external_config` | `"config/mcp/external.yaml"` | NUEVO — ruta del manifiesto de MCPs | FR-007 |
| `mcp_supervisor_enabled` | `True` | NUEVO — arranca `MCPProcessSupervisor` en lifespan | FR-004 |
| `mcp_logs_dir` | `"~/.vigilador/mcp-logs"` | NUEVO — logs por MCP | FR-007 |
| `vector_index_backend` | `"turbovec"` | NUEVO — selecciona `TurboVecIndex` (nativo, paquete PyPI `turbovec`) | FR-010 |
| `ingestion_enabled` | `True` | NUEVO — habilita pipeline de ingestion | FR-012 |
| `ingestion_connectors` | `["google_drive"]` | NUEVO — connectors activos MVP | FR-013 |
| `skills_sources_enabled` | `["curated","learned","external:k-dense","external:agency-agents"]` | MODIFICAR — quita `external:claude-local` | FR-033 |
| `skills_vendor_dir` | `"src/vigilancia_multiagente/enterprise/skills_marketplace/_vendor"` | NUEVO — destino de repos clonados | FR-031 |
| `computer_use_enabled` | `False` | NUEVO — gate global de computer use | FR-029 |
| `computer_use_app_allowlist` | `[]` | NUEVO — apps/paths permitidos | FR-030 |
| `audit_dir` | `"~/.vigilador/audit"` | NUEVO — audit trail JSONL | FR-045 |
| `tools_delete_whitelist` | `["forget_user"]` | NUEVO — excepcion politica no-delete | FR-043 |
| `pi_defense_enabled` | `True` | NUEVO — detector de prompt injection | FR-044 |
| ~~`claude_local_path`~~ | — | ELIMINAR (settings.py:142) | FR-033 |
| `embedding_provider` | `"gemini"` | NUEVO — provider de embeddings seleccionable | FR-049 |
| `reranker_provider` | `"cohere"` | NUEVO — provider de reranker seleccionable | FR-049 |
| `frontend_enabled` | `True` | NUEVO — habilita superficies `frontend/src/enterprise/` | FR-046 |
| `onboarding_enabled` | `True` | NUEVO — habilita endpoints `api/v2/enterprise/onboarding/*` | FR-047/048 |

### Rutas de filesystem (runtime, `~/.vigilador/`)

| Ruta | Contenido |
|---|---|
| `~/.vigilador/credentials/` | Tokens OAuth de servicio cifrados (Fernet) — conectores |
| `~/.vigilador/mcp-logs/<name>.jsonl` | Logs por proceso MCP |
| `~/.vigilador/memories/` | Snapshots de memoria (frozen_snapshot) |
| `~/.vigilador/audit/events_<fecha>.jsonl` | Audit trail (tools, LLM, complexity, subagents) |
| `~/.vigilador/audit/pi_quarantine_<fecha>.jsonl` | Entradas externas en cuarentena |
| `~/.vigilador/turbovec/` | Persistencia local del indice TurboVec nativo (`<tenant>.tq`) |

### Rutas de configuracion (repo, versionadas)

| Ruta | Contenido |
|---|---|
| `config/mcp/external.yaml` | Manifiesto de proveedores que queden como **MCP externo (fallback)** |
| `config/modes/{default,vigilancia-tech,ceo}.yaml` | 3 modos MVP |
| `config/playbooks/{technology-watch,deep-research,general}.yaml` | 3 playbooks MVP |
| `config/tools/catalog.yaml` | Catalogo SSOT (spec 018) — referenciado |
| `config/templates/` | Templates para `template_render`/`docx`/`pdf` |

---

## Files to Create / Modify

### New Files

| File | Purpose | FR |
|------|---------|----|
| `src/vigilancia_multiagente/enterprise/tooling/mcp_client.py` | Cliente MCP STDIO/HTTP/SSE (COPY-HERMES `tools/mcp_tool.py`, modularizado) | FR-003 |
| `src/vigilancia_multiagente/enterprise/tooling/mcp_tool_wrapper.py` | Adapter MCP→`ToolWrapper` (`is_external_mcp=True`) — **fallback** para proveedores que queden como MCP | FR-001/002 |
| `scripts/audit_mcp_strategy.py` | Audit por proveedor: lenguaje + SDK Python/REST + LOC → asigna `strategy`/`runtime` en `config/tools/catalog.yaml` | FR-055 |
| `src/vigilancia_multiagente/enterprise/tooling/builtin/{search,web,research,productivity,creative,execution}/` | Tools nativas **WRAP-SDK/CLONE-UPSTREAM** por proveedor (default native-first) | FR-053/054 |
| `src/vigilancia_multiagente/enterprise/mcp/process_supervisor.py` | `MCPProcessSupervisor` (start_all/restart/get_status/stop_all, backoff) ~150 LOC | FR-004/005/006 |
| `src/vigilancia_multiagente/enterprise/mcp/healthcheck.py` | Healthcheck por MCP (initialize + tools/list) | FR-006 |
| `config/mcp/external.yaml` | Manifiesto de proveedores que queden como MCP externo (fallback) | FR-007 |
| `src/vigilancia_multiagente/infra/persistence/turbovec_index.py` | `TurboVecIndex` implementa port `VectorIndex` **nativo in-process** sobre paquete PyPI `turbovec` | FR-010/011 |
| `src/vigilancia_multiagente/enterprise/ingestion/orchestrator.py` | Pipeline discovery→ACL→extract→normalize→chunk→dedup→embed→TurboVec→metadata | FR-012 |
| `src/vigilancia_multiagente/enterprise/ingestion/chunking.py` | Chunking | FR-012 |
| `src/vigilancia_multiagente/enterprise/ingestion/dedup.py` | Dedup | FR-012 |
| `src/vigilancia_multiagente/enterprise/ingestion/acl_resolver.py` | Resolucion ACL (tenant/roles/users) | FR-012 |
| `src/vigilancia_multiagente/enterprise/ingestion/connectors/google_drive.py` | Connector Drive (primero) | FR-013 |
| `src/vigilancia_multiagente/domain/ports/ingestion_connector.py` | Port `IngestionConnector` | FR-013 |
| `src/vigilancia_multiagente/enterprise/memory/frozen_snapshot.py` | Memoria (COPY-HERMES `memory_tool.py`, home→`~/.vigilador/memories/`) | FR-015 |
| `src/vigilancia_multiagente/enterprise/governance/file_safety.py` | Safety de archivos (COPY-HERMES) | FR-025 |
| `src/vigilancia_multiagente/enterprise/governance/redact.py` | Redaccion PII (COPY-HERMES) | FR-025 |
| `src/vigilancia_multiagente/enterprise/governance/path_security.py` | Path traversal (COPY-HERMES) | FR-025 |
| `src/vigilancia_multiagente/enterprise/governance/url_safety.py` | Validacion URL (COPY-HERMES) | FR-025 |
| `src/vigilancia_multiagente/enterprise/governance/website_policy.py` | robots.txt (COPY-HERMES) | FR-025 |
| `src/vigilancia_multiagente/enterprise/governance/approvals/{approval,interrupt,slash_confirm}.py` | Gates de aprobacion (COPY-HERMES) | FR-025/030 |
| `src/vigilancia_multiagente/enterprise/governance/prompt_injection_detector.py` | PI defense regex + Lakera (~200 LOC) | FR-044 |
| `src/vigilancia_multiagente/enterprise/governance/audit_log.py` | Audit trail JSONL + index | FR-045 |
| `src/vigilancia_multiagente/enterprise/tooling/{lazy_deps,schema_sanitizer,output_limits}.py` | Tooling base (COPY-HERMES) | FR-025 |
| `src/vigilancia_multiagente/enterprise/tooling/builtin/documents/template_render.py` | Tool `template_render` (Jinja2) | FR-028 |
| `src/vigilancia_multiagente/enterprise/tooling/builtin/documents/docx_generate.py` | Tool `docx_generate` (python-docx) | FR-028 |
| `src/vigilancia_multiagente/enterprise/tooling/builtin/documents/pdf_generate.py` | Tool `pdf_generate` (WeasyPrint) | FR-028 |
| `src/vigilancia_multiagente/enterprise/tooling/builtin/desktop/computer_use/{schema,tool,windows_backend}.py` | Computer use Win11 (COPY-HERMES + backend nuevo) | FR-029/030 |
| `src/vigilancia_multiagente/enterprise/orchestration/complexity_classifier.py` | `ComplexityClassifier` (SIMPLE/MODERADA/COMPLEJA) | FR-017 |
| `src/vigilancia_multiagente/enterprise/orchestration/playbook_runner.py` | `PlaybookRunner` (carga YAML, valida modo, instancia agents, flow) | FR-018 |
| `src/vigilancia_multiagente/enterprise/modes/mode_context.py` | `ModeContext` frozen snapshot | FR-019 |
| `plugins/technology-watch/__init__.py` + wrapper | Envoltura del `BranchCoordinator` 2.0 (6 ramas) | FR-023 |
| `config/modes/ceo.yaml` (normalizar a `CEO`) | Modo CEO MVP (existe `ceo.yaml`; alinear id) | FR-021 |
| `src/vigilancia_multiagente/enterprise/skills_marketplace/k_dense_adapter.py` | Adapter K-Dense | FR-032 |
| `src/vigilancia_multiagente/enterprise/skills_marketplace/agency_agents_adapter.py` | Adapter agency-agents | FR-032 |
| `src/vigilancia_multiagente/enterprise/skills_marketplace/_vendor/{k_dense,agency_agents}/` | Repos clonados dentro de `src/` | FR-031 |
| `src/vigilancia_multiagente/enterprise/dreaming/reporter.py` | Reporter minimo (log de completitud) | FR-040 |
| `frontend/src/enterprise/{onboarding,chat,sources,admin}/` | 4 superficies MVP (sin login): onboarding, chat+modo+workstreams, datos empresariales, estado tools/MCPs | FR-046/050 |
| `src/vigilancia_multiagente/api/routes/enterprise_onboarding.py` | Endpoints `api/v2/enterprise/onboarding/*` (COMPANY + company_geo + providers + ingestion), sin auth de usuario | FR-047/048 |
| `src/vigilancia_multiagente/enterprise/orchestration/subagent_registry.py` | `SubagentRegistry` spawn/track basico (tabla `subagents`) | FR-051 |
| `tests/enterprise/mcp/test_process_supervisor.py` y demas tests por modulo | Tests unitarios | todos |

### Modified Files

| File | Changes | FR |
|------|---------|----|
| `src/vigilancia_multiagente/enterprise/tooling/tool_registry.py` | Registrar `McpToolWrapper`s; tool-gating READ-ONLY (CQS); excluir capabilities `delete_*` salvo whitelist | FR-002/042/043 |
| `src/vigilancia_multiagente/config/settings.py` | Añadir campos nuevos (tabla Variables); `skills_sources_enabled` sin claude-local; eliminar `claude_local_path` | FR-033 + Variables |
| `src/vigilancia_multiagente/api/app.py` | Lifespan: arrancar `MCPProcessSupervisor`, ingestion, dreaming basico; quitar wiring de auth de usuario | FR-004/036 |
| `src/vigilancia_multiagente/api/router.py` | Desregistrar router `enterprise_auth` | FR-036 |
| `src/vigilancia_multiagente/api/dependencies.py` | Eliminar dependencias de auth de usuario (conservar las no-auth y las de autenticidad) | FR-036 |
| `src/vigilancia_multiagente/enterprise/skills_marketplace/skill_loader.py` | Quitar rama `external:claude-local` (lineas 9,50,58,71-72,136-138); cablear adapters k_dense/agency_agents | FR-032/033 |
| `src/vigilancia_multiagente/enterprise/modes/mode_resolver.py` | Conectar al flujo de request; producir `ModeContext` frozen | FR-019 |
| `src/vigilancia_multiagente/enterprise/dreaming/scheduler.py` | Limitar a `memory_consolidation` + `ingestion_sync`; deprecar registro de loops/fases extra | FR-040 |
| `config/playbooks/technology-watch.yaml` | Delegar al `plugins/technology-watch` (BranchCoordinator 2.0) | FR-023 |

---

## Inventario y Nombramiento de Tools

> Nombres reales tomados del catalogo SSOT `config/tools/catalog.yaml` (spec 018). **Convencion de nombres**: `id` de tool = entrada del catalogo; cada `capability` es un verbo invocable. Registro/logs: tools internas → `vigilador.tools.<domain>.<id>.<capability>`; MCPs externos → `vigilador.mcp_ext.<id>.<capability>`. Toda tool (interna o MCP) se registra en `ToolRegistry` via `ToolWrapper`.

### Tabla 1 — Proveedores → Tools (estrategia native-first; TODOS = `ToolWrapper`)

> **TODOS** los proveedores se exponen como `Tool` en el `ToolRegistry` (FR-054), con estrategia **native-first** (FR-053): por defecto `WRAP-SDK` (tool nativa Python sobre el SDK/REST del proveedor), `CLONE-UPSTREAM` para MCPs **Python** con logica propia (refactor a `src/`), y `MCP-EXTERNO` (proceso) **solo como fallback** (TS/Go sin SDK). La columna **Backend** indica el destino: **nativo in-process** (preferido) o proceso MCP (fallback); la estrategia final la fija el **audit (FR-055)**.
>
> **Estrategia estimada (a confirmar por audit)**: WRAP-SDK → `tavily` (tavily-python), `exa` (exa-py), `brave` (REST), `serper`/`serper_patents` (REST), `jina` (REST), `firecrawl` (firecrawl-py), `fetch` (httpx), `playwright` (playwright py, #50), `openalex` (pyalex/REST), `markitdown` (markitdown), `minimax_image` (REST), `google_workspace` (google-api-python-client); CLONE-UPSTREAM → `arxiv`, `google_scholar` (Python ya clonados en `.mcp-servers/`); `sandbox` → WRAP-SDK (e2b) o MCP-EXTERNO; MCP-EXTERNO → solo si el audit halla un proveedor sin SDK/REST Python.

| # | Proveedor (tool) | Dominio | Estrategia (native-first, est.) | Backend | Capabilities (verbos) |
|---|---|---|---|---|---|
| 1 | `tavily` | research/search | WRAP-SDK | nativo (tavily-python) | `web_search`, `news_search` |
| 2 | `exa` | research/search | WRAP-SDK | nativo (exa-py) | `semantic_search`, `find_similar` |
| 3 | `brave` | research/search | WRAP-SDK | nativo (REST) | `web_search`, `local_search` |
| 4 | `serper` | research/search | WRAP-SDK | nativo (REST) | `google_search`, `scholar_search`, `patent_search`, `news_search` |
| 5 | `serper_patents` | research | WRAP-SDK | nativo (REST) | `patent_search`, `patent_details` |
| 6 | `jina` | web | WRAP-SDK | nativo (REST) | `reader`, `extract_content` |
| 7 | `firecrawl` | web | WRAP-SDK | nativo (firecrawl-py) | `crawl_url`, `scrape_page`, `map_site` |
| 8 | `fetch` | web | WRAP-SDK | nativo (httpx) | `fetch_url`, `extract_text` |
| 9 | `playwright` | web | WRAP-SDK | nativo (playwright py, #50) | `navigate`, `screenshot`, `click`, `fill` |
| 10 | `google_scholar` | research | CLONE-UPSTREAM | nativo (Python clonado) | `search_papers`, `get_citations` |
| 11 | `arxiv` | research | CLONE-UPSTREAM | nativo (Python clonado) | `search_papers`, `get_paper`, `list_categories` |
| 12 | `openalex` | research | WRAP-SDK | nativo (pyalex/REST) | `search_works`, `get_authors`, `get_institutions` |
| 13 | `markitdown` | documents | WRAP-SDK | nativo (markitdown pip) | `convert_to_markdown`, `extract_text` |
| 14 | `sandbox` | execution | WRAP-SDK* | nativo (e2b) o MCP-EXTERNO | `run_code`, `execute_command` |
| 15 | `minimax_image` | creative | WRAP-SDK | nativo (REST/SDK) | `generate_image`, `edit_image` |
| 16 | `google_workspace` | productivity | WRAP-SDK | nativo (google-api-python-client) | `read_docs`, `write_docs`, `read_sheets`, `send_email` |

\* `sandbox`: nativo via SDK e2b si aporta; si no, queda como MCP-EXTERNO (ejecucion aislada). Lo decide el audit.

**Conteo de estrategia (estimado, a confirmar por audit FR-055)**: WRAP-SDK = 13, CLONE-UPSTREAM = 2 (`arxiv`, `google_scholar`), MCP-EXTERNO = 0 (solo si el audit halla un proveedor sin SDK/REST Python; `sandbox` es el unico candidato condicional). Es decir, **los 16 pasan a tool nativa**; STDIO/MCP externo deja de ser el default.

**Subconjunto busqueda/web/research (todos → tool nativa)**: `tavily`, `exa`, `brave`, `serper`, `serper_patents`, `jina`, `firecrawl`, `fetch`, `playwright`, `google_scholar`, `arxiv`, `openalex` (12 de 16) — WRAP-SDK salvo arxiv/google_scholar (CLONE-UPSTREAM).

**Indice vectorial (no expuesto como tool de agente)**:

| Componente | Tipo | Capabilities | Consumidor |
|---|---|---|---|
| `turbovec` (paquete PyPI) | libreria nativa Python (Rust + bindings) | `add`, `query`, `persist`, `rebuild` | `TurboVecIndex` (adapter del port `VectorIndex`, FR-009/010/011). Indice vectorial unico, in-process. No se expone al agente como tool de busqueda. |

### Tabla 2 — Tools NUEVAS (Tier 1 Python, creadas) — `is_external_mcp=False`

| Tool id | Dominio | Capabilities | SDK | Ruta |
|---|---|---|---|---|
| `template_render` | documents | `render_template`, `interpolate_variables` | Jinja2 / docxtpl | `enterprise/tooling/builtin/documents/template_render.py` |
| `docx_generate` | documents | `generate_docx`, `format_document` | python-docx | `enterprise/tooling/builtin/documents/docx_generate.py` |
| `pdf_generate` | documents | `generate_pdf`, `html_to_pdf` | WeasyPrint | `enterprise/tooling/builtin/documents/pdf_generate.py` |

### Tabla 3 — Tools REFACTORIZADAS (COPY-HERMES extraidas a `src/`) — `is_external_mcp=False`

| Tool id | Dominio | Capabilities | Origen Hermes | Ruta destino |
|---|---|---|---|---|
| `file_system` | documents | `read_file`, `write_file`, `list_dir`, `patch_file` | `tools/file_tools.py` (+`file_operations`,`file_state`,`agent/file_safety`) | `enterprise/tooling/builtin/documents/file_system.py` (+`_file_operations`,`_file_state`,`_file_safety`) |
| `computer_use` | desktop | `navigate`, `screenshot`, `click`, `fill`, `type` | `tools/computer_use/{schema,tool,backend,cua_backend}.py` | `enterprise/tooling/builtin/desktop/computer_use/{schema,tool,windows_backend}.py` |

> `computer_use` es adicion de 021 (mas alla de las 20 capacidades base de 00b) por peticion explicita del usuario; MUST anadirse al catalogo SSOT con `domain: desktop`, `strategy: COPY-HERMES`.

**Modulos de soporte refactorizados (COPY-HERMES, no son tools de agente)**: `mcp_client.py` (de `tools/mcp_tool.py`), `frozen_snapshot.py` (de `tools/memory_tool.py`), governance `{file_safety,redact,path_security,url_safety,website_policy}.py`, `approvals/{approval,interrupt,slash_confirm}.py`, tooling base `{lazy_deps,schema_sanitizer,output_limits}.py`.

### Resumen de conteo

| Categoria | Cantidad | Tools |
|---|---|---|
| Proveedores→Tools (native-first: WRAP-SDK/CLONE-UPSTREAM; MCP-EXTERNO fallback) | 16 | tavily, exa, brave, serper, serper_patents, jina, firecrawl, fetch, playwright, google_scholar, arxiv, openalex, markitdown, sandbox, minimax_image, google_workspace |
| NUEVAS (Tier 1) | 3 | template_render, docx_generate, pdf_generate |
| REFACTORIZADAS (Hermes) | 2 | file_system, computer_use |
| Indice vectorial (no-tool) | 1 | turbovec (paquete PyPI nativo) |
| **Total tools de agente** | **21** | 16 + 3 + 2 |

> Las 20 capacidades MVP de 00b = 16 MCP + 4 documents (`file_system` + 3 nuevas). `computer_use` es la adicion 021 (→ 21).

## Deprecated / Removed Code Inventory

> Convencion: **REMOVE** = se elimina del runtime (codigo borrado o desregistrado). **DEPRECATE→roadmap** = se conserva el archivo pero se marca fuera de MVP (no se importa/registra ni se presenta como capacidad activa); su reactivacion corresponde a F4b/F4c/F5b.

### A. Auth de usuario — REMOVE (correccion D4, FR-036)

| Path / Symbol | Accion | Razon | Reemplazo |
|---|---|---|---|
| `src/vigilancia_multiagente/api/routes/enterprise_auth.py` | REMOVE (ruta completa, 6 refs) | Login/sesiones de usuario sin sentido en version de prueba | Ninguno (acceso local) |
| `src/vigilancia_multiagente/api/router.py` (registro de `enterprise_auth`, 2 refs) | REMOVE registro | Quitar la ruta del router | — |
| `src/vigilancia_multiagente/api/dependencies.py` (deps de auth de usuario, ~10 refs) | REMOVE deps de usuario | Sin auth de usuario | Conservar deps no-auth |
| `src/vigilancia_multiagente/api/routes/enterprise_onboarding.py` (1 ref auth) | MODIFY (desacoplar auth) | Onboarding no debe exigir login | — |
| Superficie frontend de auth (login) | REMOVE (en spec de frontend) | D4 | — |
| `enterprise/auth/oauth_manager.py` + `__init__.py` | **KEEP** | OAuth de servicio para conectores (Drive/Gmail) | — |
| `research_evaluation.py` (2 matches `auth`) | **KEEP** (falso positivo) | Son de "authenticity" (workstream 2.0), no auth de usuario | — |

> Nota: `enterprise/auth/token_auth.py`, `device_token.py`, `capability_tokens.py` del plan **nunca se construyeron**; no hay nada que borrar. `capability_tokens` queda como roadmap F5b.

### B. Skills `.claude` local — REMOVE del runtime (correccion D3, FR-033)

| Path / Symbol | Accion | Razon | Reemplazo |
|---|---|---|---|
| `enterprise/skills_marketplace/claude_local_adapter.py` | REMOVE del runtime (desregistrar) | Usuario: no usar skills `.claude` | k_dense_adapter + agency_agents_adapter |
| `skill_loader.py` lineas 9, 50, 58, 71-72, 136-138 (`_load_external_claude_local`, ctor `claude_local_path`) | REMOVE | Quitar fuente claude-local | Ramas k-dense/agency-agents |
| `config/settings.py:141` `skills_sources_enabled` con `"external:claude-local"` | MODIFY | Cambiar a `["curated","learned","external:k-dense","external:agency-agents"]` | — |
| `config/settings.py:142` `claude_local_path` | REMOVE | Sin dependencia de `.claude/` | — |
| Dependencia runtime de `.claude/skills` | REMOVE | D3 | Repos en `src/.../_vendor/` |
| spec 015 (mecanismo claude-local) | SUPERSEDED por 021 | — | 021 grupo 6 |

### C. Roadmap sobre-construido — DEPRECATE→roadmap (NO borrar, FR-041)

| Path | Archivos | Destino | Razon |
|---|---|---|---|
| `enterprise/orchestration/goal_pursuit/` | 8 py | roadmap **F4b** | Playbook goal-pursuit fuera de MVP |
| `enterprise/orchestration/app_development/` | 12 py | roadmap **F4b** | Playbook app-development fuera de MVP |
| `enterprise/artifacts/` | 10 py | roadmap **F4b** | Playbook artifact-development fuera de MVP |
| `enterprise/dreaming/loops/` | 8 py (admin_repo_loop, company_self_update, prompt_self_improvement, regulatory_watcher, skill_learning, tool_composition, writing_style) | roadmap **F5b** | 5-7 loops de autoaprendizaje fuera de MVP |
| `enterprise/dreaming/phases/` | 9 de 11 (admin_repo_maintenance, config_refresher, dreaming_report, index_maintenance, regulatory_watch, scheduled_artifacts, self_improvement, skill_curator + `__init__`) | roadmap **F5b** | MVP solo `memory_consolidation.py` + `ingestion_sync.py` |
| `enterprise/dreaming/{orchestrator,phase_protocol,ports,metrics,models}.py` | 5 py | REVISAR/REDUCIR | Mantener nucleo minimo para 2 fases; deprecar lo que orquesta loops/fases roadmap |
| `config/modes/{cfo,consultor-legal,marketing,operaciones-pyme,vendedor-b2b}.yaml` | 5 yaml | roadmap **F4c** | Modos fuera de MVP (MVP: default, vigilancia-tech, ceo) |
| `config/playbooks/{app-development,artifact-development,decision-debate,goal-pursuit}.yaml` | 4 yaml | roadmap **F4b** | Playbooks fuera de MVP (MVP: technology-watch, deep-research, general) |

> Marcado de deprecacion: añadir cabecera `# ROADMAP (F4b|F4c|F5b) — fuera de MVP 021; no registrar en runtime` y excluir del wiring (composition root, scheduler, mode/playbook loaders los ignoran salvo flag). Los specs 012/013/014/017 quedan como specs de roadmap.

### D. Decisiones obsoletas confirmadas (no implementar)

| Item | Estado | Traza |
|---|---|---|
| Quotas por usuario | Obsoleta (C0) | doc 08; decision #29 |
| pgvector backup / A/B contra TurboVec | Obsoleta (C0) | doc 00 #4; decision #85 |
| TurboVec via MCP (D1 inicial) | Descartado por D1 revisada (2026-05-29): se usa nativo in-process via paquete PyPI `turbovec` por consistencia con D5 native-first | revision usuario |

---

## Constitution Check (Pre-Design)

- **Gate result**: PASS
- **Constitucion evaluada**: v1.2.0 (`.specify/memory/constitution.md`).
- **Alignment**:
  - **Pensar Antes de Codificar**: el plan parte de una auditoria verificada (gaps con evidencia) y un inventario exacto de codigo deprecated; supuestos explicitos (A-01..A-11) y correcciones del usuario (D1-D4) declarados.
  - **Simplicidad Obligatoria**: solo backbone MVP; el roadmap no se expande. Supervisor ~150 LOC; YAML para config; sin abstracciones especulativas.
  - **Modularidad Primero**: extraccion Hermes en modulos ≤400 LOC (cliente/schema/normalizador/politica/cache/wrapper); cada subsistema en su carpeta con un concern.
  - **Cambios Quirurgicos y Trazables**: el 2.0 intacto; `technology-watch` envuelve el `BranchCoordinator`; deprecaciones marcadas, no borradas; cada archivo importado con atribucion; cada FR con traza al plan.
  - **Entrega Verificable**: 12 SC del spec + verificacion por fase; tests por modulo; suite 2.0 sigue verde.
- **Diseno de Software**: SRP/SoC (modulos por concern), DIP (ports: `VectorIndex`, `IngestionConnector`, `ToolWrapper`, `ModeResolutionStrategy`), CQS (#81 tool-gating READ-ONLY), DRY (reusa 009/018; no redefine), KISS/YAGNI (MVP-only), OCP (modos/playbooks por YAML).

---

## Phases

### Phase F1 — Estrategia native-first de tools + audit + puente MCP (fallback) + supervisor + governance Hermes + remover auth

**Aplica decisiones**: 021-D5 (native-first + abstraccion universal de Tool), 021-D4 (eliminar auth de usuario; conservar OAuth de servicio).

1. Audit `scripts/audit_mcp_strategy.py`: por proveedor clona/inspecciona el repo, detecta lenguaje + SDK Python/REST + LOC y asigna `strategy`/`runtime` en `config/tools/catalog.yaml` (WRAP-SDK / CLONE-UPSTREAM / MCP-EXTERNO; regla <5000 LOC spec 018). (FR-055)
2. Construir tools **nativas** (default) por proveedor en `enterprise/tooling/builtin/<domain>/`: WRAP-SDK sobre SDK/REST (tavily, exa, brave, serper, jina, firecrawl, fetch, playwright, openalex, markitdown, minimax_image, google_workspace) y CLONE-UPSTREAM+refactor para los Python con logica propia (arxiv, google_scholar). Cada una implementa `ToolWrapper` (`is_external_mcp=False`). (FR-053)
3. Portar `tools/mcp_tool.py` (Hermes) → `enterprise/tooling/mcp_client.py` (STDIO/HTTP/SSE), modularizado ≤400 LOC, con atribucion. (FR-003)
4. Crear `McpToolWrapper` (**fallback**) + `MCPProcessSupervisor` (`enterprise/mcp/process_supervisor.py`) + `healthcheck.py` (backoff exp, STUCK, healthcheck 60s); `config/mcp/external.yaml` declara **solo** los proveedores que queden como MCP externo segun el audit. (FR-001/004/005/006/007)
5. Registrar **TODOS** los proveedores como `Tool` en el `ToolRegistry` (FR-054): las nativas directamente y las de fallback via `McpToolWrapper`; ver **Tabla 1 (Inventario)**; tool-gating READ-ONLY (CQS) + politica no-delete. (FR-002/042/043/054)
6. Extraer governance Hermes → `enterprise/governance/{file_safety,redact,path_security,url_safety,website_policy}.py` + `approvals/{approval,interrupt,slash_confirm}.py`; tooling base `{lazy_deps,schema_sanitizer,output_limits}.py`. Atribucion + tests. (FR-025/026)
7. **REMOVE auth de usuario**: borrar `api/routes/enterprise_auth.py`, desregistrar en `router.py`, limpiar deps de usuario en `dependencies.py`, desacoplar `enterprise_onboarding.py`. Conservar `oauth_manager.py`. (FR-036/037/038)
8. Arrancar supervisor en `api/app.py` lifespan (guardado por `mcp_supervisor_enabled`).

**Output**: 16 proveedores registrados como **Tools** (nativas WRAP-SDK/CLONE-UPSTREAM + MCP externo fallback); catalogo con `strategy` fijada por audit; supervisor operativo; governance F1; sin auth de usuario.
**Verificacion**: `tools list` muestra los 16 proveedores como Tools; los que queden como MCP externo arrancan UP via supervisor (restart con backoff al matarlos); grep auth de usuario en `api/` = 0; suite 2.0 verde.

### Phase F2 — TurboVec nativo + ingestion + memoria + skills marketplaces

**Aplica decisiones**: 021-D1 revisada (TurboVec nativo in-process), 021-D2 (clonar marketplaces dentro de `src/`), 021-D3 (eliminar claude-local del runtime).

1. Instalar el paquete PyPI `turbovec` y validar carga de la libreria + bindings Rust en Windows 11. (FR-009)
2. Crear `infra/persistence/turbovec_index.py` (`TurboVecIndex`) implementando el port `VectorIndex` (`add`, `query`, `persist`, `rebuild`) llamando in-process a la libreria; persistencia local `~/.vigilador/turbovec/<tenant>.tq`; `healthcheck()` explicito. (FR-010/011)
3. Crear `enterprise/ingestion/{orchestrator,chunking,dedup,acl_resolver}.py` + port `IngestionConnector` + `connectors/google_drive.py`. Reusar `GeminiEmbeddingGateway` + `SemanticReranker`. (FR-012/013/014)
4. Connectors obtienen credenciales de `oauth_manager` con scopes sin delete. (FR-016)
5. Portar `tools/memory_tool.py` → `enterprise/memory/frozen_snapshot.py` (home `~/.vigilador/memories/`). (FR-015)
6. Clonar `K-Dense-AI/scientific-agent-skills` + `msitarzewski/agency-agents` en `src/.../skills_marketplace/_vendor/{k_dense,agency_agents}/`; crear `k_dense_adapter.py` + `agency_agents_adapter.py`; quitar `external:claude-local` del `SkillLoader`; soportar modelo `CommandSkill` (params/permissions/preconditions/sandbox/hash); registrar en `SkillRegistry`. (FR-031/032/033/034/035/052)

**Output**: indice vectorial unico via MCP; ingestion Drive operativa; memoria; skills externos cargados sin `.claude`.
**Verificacion**: ingesta 100 docs + query con citas; libreria `turbovec` no instalada / indice no inicializado → error explicito en `healthcheck()`; `SkillLoader` registra `external:k-dense`/`agency-agents`; grep `claude-local` en runtime = 0.

### Phase F3a — Tools Tier 1 nuevas + computer use

1. Crear las 3 tools NUEVAS (ver **Tabla 2**): `template_render.py` (Jinja2), `docx_generate.py` (python-docx), `pdf_generate.py` (WeasyPrint) en `builtin/documents/`, cada una `ToolWrapper`, registradas. (FR-028)
2. Extraer Hermes `tools/computer_use/{schema,tool}.py` → `builtin/desktop/computer_use/` (tool REFACTORIZADA, ver **Tabla 3**); reescribir backend `windows_backend.py` con `pyautogui`+`pygetwindow`+`mss`; capabilities navigate/screenshot/click/fill/type; anadir entrada al catalogo SSOT. (FR-029)
3. Gate de aprobacion en acciones destructivas; error explicito sin display. (FR-030)

**Output**: 20 capacidades MVP activas (4 Tier1 + 16 Tier2); computer use Win11.
**Verificacion**: `tools list` = 20; cada modulo ≤400 LOC + atribucion; screenshot+click en Win11; accion destructiva pide aprobacion.

### Phase F4a — Orquestacion: Mode/Complexity/Playbook + 3 modos + 3 playbooks

1. Crear `ComplexityClassifier` (`enterprise/orchestration/complexity_classifier.py`). (FR-017)
2. Crear `PlaybookRunner` (`enterprise/orchestration/playbook_runner.py`): carga YAML, valida `mode_compatible`, instancia agents, flow sequential/rounds. (FR-018)
3. Conectar `ModeResolver` al flujo de request + `ModeContext` frozen (`enterprise/modes/mode_context.py`); `ModeLoader` valida en boot. (FR-019/020)
4. Dejar 3 modos MVP (`default`, `vigilancia-tech`, `CEO`) y deprecar los 5 de roadmap; dejar 3 playbooks MVP y deprecar los 4 de roadmap. (FR-021/022)
5. `plugins/technology-watch/` envuelve el `BranchCoordinator` 2.0; `technology-watch.yaml` delega ahi. (FR-023)
6. `general` (1 agente) y `deep-research` (Clarify→Plan→Approve→Execute→Fuse→Report). (FR-024)
7. `SubagentRegistry` (`enterprise/orchestration/subagent_registry.py`) + tabla `subagents`; `PlaybookRunner` lo usa al spawnear subagentes. (FR-051)
8. Frontend MVP — 4 superficies en `frontend/src/enterprise/{onboarding,chat,sources,admin}` (sin login): onboarding, chat+modo+visor workstreams, datos empresariales, estado tools/MCPs (UP/DOWN + API keys). (FR-046/050)
9. Onboarding — endpoints `api/v2/enterprise/onboarding/*` (COMPANY + `company_geo` + seleccion providers `embedding_provider`/`reranker_provider` + conectar Drive + primera ingestion) sin auth de usuario. (FR-047/048/049)

**Output**: jerarquia Channel→Mode→Playbook→Agent→Skill→Tool operativa end-to-end.
**Verificacion**: `/mode vigilancia-tech` corre las 6 ramas 2.0 sin regresiones; `/mode default`→general; `/mode CEO`→deep-research; modos/playbooks roadmap no aparecen como MVP.

### Phase F5a — Dreaming basico + PI defense + audit

1. Limitar `enterprise/dreaming/scheduler.py` a `memory_consolidation` + `ingestion_sync`; crear `reporter.py` minimo; deprecar loops + 9 fases. (FR-039/040/041)
2. Crear `prompt_injection_detector.py` (regex + Lakera); pipeline de entradas externas → cuarentena. (FR-044)
3. Crear `audit_log.py` (JSONL en `~/.vigilador/audit/`) + index. (FR-045)

**Output**: ciclo nocturno minimo; PI defense; audit trail.
**Verificacion**: cron ejecuta solo 2 fases; payload "ignore previous instructions" en cuarentena; audit JSONL registra eventos.

---

## Trazabilidad FR → Fase

| Fase | Requisitos funcionales cubiertos |
|---|---|
| **F1** | FR-053, FR-054, FR-055 (estrategia native-first + abstraccion universal de Tool + audit); FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-008 (puente MCP fallback/supervisor/cliente/manifiesto/circuit breaker); FR-025, FR-026 (governance Hermes + atribucion); FR-036, FR-037, FR-038 (remover auth de usuario / conservar OAuth / sin quotas); FR-042, FR-043 (tool-gating CQS + no-delete) |
| **F2** | FR-009, FR-010, FR-011 (TurboVec **nativo in-process** + port + error explicito); FR-012, FR-013, FR-014, FR-015, FR-016 (ingestion + connectors + embeddings/reranker reuse + memoria + scopes sin delete); FR-031, FR-032, FR-033, FR-034, FR-035 (marketplaces clonados en src/ + adapters + sin claude-local + discovery 3 niveles + unavailable); FR-052 (CommandSkill) |
| **F3a** | FR-027 (OpenClaw solo referencia); FR-028 (3 tools Tier 1); FR-029, FR-030 (computer use Win11 + gate de aprobacion) |
| **F4a** | FR-017 (ComplexityClassifier); FR-018 (PlaybookRunner); FR-019, FR-020 (ModeResolver + ModeContext + ModeLoader); FR-021, FR-022 (3 modos + 3 playbooks MVP); FR-023 (technology-watch envuelve BranchCoordinator 2.0); FR-024 (general + deep-research); FR-046, FR-047, FR-048, FR-049, FR-050 (frontend MVP + onboarding + seleccion de providers); FR-051 (SubagentRegistry) |
| **F5a** | FR-039, FR-040, FR-041 (Dreaming basico = 2 fases; resto roadmap); FR-044 (PI defense regex+Lakera); FR-045 (audit JSONL) |

> Cobertura: FR-001 a FR-055 (55/55). Cada FR traza a una fase; el detalle por archivo esta en "Files to Create / Modify" y las citas al plan en `spec.md`.

## Rollout Strategy

- **Incremental por fase** (F1→F5a); no se avanza sin verificacion. Cada subsistema detras de su flag (`mcp_supervisor_enabled`, `ingestion_enabled`, `computer_use_enabled`, `dreaming_enabled`, `pi_defense_enabled`).
- **Backward compatibility**: el 2.0 intacto; `technology-watch` envuelve el `BranchCoordinator`; los 15 MCPs del 2.0 se referencian sin alterar `mcp-providers.json`.
- **Coexistencia roadmap**: el codigo deprecated permanece en el repo, marcado y no registrado; reactivable por su spec (012/013/014/017) cuando se levante el flag.
- **Rollback por fase**: F1 supervisor → `mcp_supervisor_enabled=false`. F2 libreria `turbovec` no carga → busqueda semantica deshabilitada con error; reinstalar/recompilar el paquete; reconstruir desde fuentes. F3a tool rota → `enabled:false` en catalogo. F4a → `enterprise_enabled=false` cae a 2.0 puro. F5a → `dreaming_enabled=false`.

## Success Criteria

Se cumplen los criterios SC-001..SC-012 del [spec.md](spec.md). Resumen verificable:
- **SC-001/002/003**: 16 proveedores registrados como Tools (nativas WRAP-SDK/CLONE-UPSTREAM + MCP fallback); ejecucion por dominio sin conocer el backend; restart/backoff de los que queden como MCP.
- **SC-004**: `TurboVecIndex` (paquete PyPI `turbovec` nativo) implementa el port; 100 docs + query con citas; libreria no cargada → error explicito.
- **SC-005/006**: `/mode vigilancia-tech` corre 6 ramas 2.0 sin regresiones; `general`/`deep-research` operativos.
- **SC-007/008**: skills `external:k-dense`/`agency-agents` cargados; `claude-local` y auth de usuario = 0 en runtime.
- **SC-009/010**: computer use Win11 con aprobacion; modulos Hermes ≤400 LOC + atribucion; OpenClaw 0 archivos.
- **SC-011/012**: Dreaming solo 2 fases; tool-gating + no-delete + PI defense + audit JSONL operativos.

## Constitution Check (Post-Design)

- **Status**: PASS
- **Justification**:
  - **Pensar Antes de Codificar**: plan basado en evidencia (gaps + inventario deprecated exacto), correcciones del usuario explicitas, supuestos declarados.
  - **Simplicidad / YAGNI**: solo MVP; roadmap deprecated sin expandir; supervisor minimo; config YAML.
  - **Modularidad / SRP / SoC**: extraccion Hermes ≤400 LOC; subsistemas por concern; ports para DIP.
  - **Cambios Quirurgicos**: 2.0 intacto; deprecaciones marcadas no borradas; atribucion + traza por FR.
  - **Manejo de errores estricto**: `turbovec` no cargado/OAuth/computer_use con errores explicitos; sin fallbacks silenciosos.
  - **Entrega Verificable**: 12 SC + verificacion por fase + tests por modulo + suite 2.0 verde.
  - **Diseno**: DIP (4 ports), CQS (#81), DRY (reusa 009/018), OCP (YAML), KISS.
