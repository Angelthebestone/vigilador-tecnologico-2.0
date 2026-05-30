# Tasks: Integracion Runtime MVP — Tools Native-First, Extraccion a src/ y Cableado de Orquestacion

**Input**: `specs/021-mvp-integration-extraction/spec.md`, `specs/021-mvp-integration-extraction/plan.md`
**Feature**: Cierre del backbone MVP F1-F5a — proveedores como Tools native-first (D5), TurboVec nativo (D1 revisada), ingestion empresarial, orquestacion (Mode/Playbook/Complexity wrapping 2.0 BranchCoordinator), 3 modos + 3 playbooks MVP, frontend 4 superficies sin login (D4), skills marketplaces clonados en src/ (D2, sin claude-local D3), Hermes extraido modular, computer use Win11, dreaming basico (2 fases), deprecaciones marcadas no borradas.

**Traza a spec**: FR-001..FR-055, SC-001..SC-015. **Decisiones**: 021-D1..D5.

**Testing strategy**: test-before-implementation por modulo. Cada fase con criterios verificables. Cero modificaciones al 2.0 (cambios quirurgicos). Roadmap (goal_pursuit/app_development/artifacts/loops/9 fases extra/5 modos/4 playbooks) DEPRECATE no DELETE.

---

## Phase 0: Setup — audit, settings, scaffolding

Objetivo: validar entorno, clasificar proveedores con audit (FR-055), preparar variables y directorios base. Todo lo posterior depende de la clasificacion del audit.

Independent Test Criteria: `python scripts/audit_mcp_strategy.py` produce reporte JSON; settings cargan sin errores; directorios `~/.vigilador/{credentials,mcp-logs,memories,audit,turbovec}` existen; `.env.example` tiene las nuevas variables.

- [ ] T001 Crear `scripts/audit_mcp_strategy.py` que por cada proveedor de spec 018 catalog detecte lenguaje principal, presencia de SDK Python/REST estable, LOC del repo (regla <5000 LOC), y proponga `strategy` (WRAP-SDK / CLONE-UPSTREAM / MCP-EXTERNO) + `runtime` (`python_internal` / `process_stdio` / `process_http`); escribe reporte en `docs/audit-mcp-strategy.json` y actualiza `config/tools/catalog.yaml` fijando `loc_validated: true` (FR-055)
- [ ] T002 Ejecutar `python scripts/audit_mcp_strategy.py` y revisar `docs/audit-mcp-strategy.json`. Confirmar la lista de proveedores que quedan WRAP-SDK, los CLONE-UPSTREAM (arxiv, google_scholar candidatos por estar ya clonados en `.mcp-servers/`), y los que pasen a MCP-EXTERNO (idealmente 0)
- [ ] T003 [P] Anadir variables nuevas a `.env.example`: `VT_GOOGLE_CLIENT_ID`, `VT_GOOGLE_CLIENT_SECRET` (OAuth google-workspace para ingestion). NO incluir `VT_TURBOVEC_MCP_*` (TurboVec es nativo). NO incluir variables de auth de usuario (D4)
- [ ] T004 [P] Ampliar `src/vigilancia_multiagente/config/settings.py` con los campos nuevos: `mcp_external_config="config/mcp/external.yaml"`, `mcp_supervisor_enabled=True`, `mcp_logs_dir="~/.vigilador/mcp-logs"`, `vector_index_backend="turbovec"`, `ingestion_enabled=True`, `ingestion_connectors=["google_drive"]`, `embedding_provider="gemini"`, `reranker_provider="cohere"`, `frontend_enabled=True`, `onboarding_enabled=True`, `skills_vendor_dir="src/vigilancia_multiagente/enterprise/skills_marketplace/_vendor"`, `computer_use_enabled=False`, `computer_use_app_allowlist=[]`, `audit_dir="~/.vigilador/audit"`, `tools_delete_whitelist=["forget_user"]`, `pi_defense_enabled=True`. **MODIFICAR** `skills_sources_enabled` a `["curated","learned","external:k-dense","external:agency-agents"]` (sin `external:claude-local`). **ELIMINAR** campo `claude_local_path` (settings.py:142). (FR-033, FR-049, todas las Variables del plan)
- [ ] T005 [P] Crear directorios runtime con permisos 0700 en `scripts/setup_runtime_dirs.py` que cree `~/.vigilador/{credentials,mcp-logs,memories,audit,turbovec}/` si no existen; ejecutar el script una vez para validar
- [ ] T006 [P] Crear directorios placeholder en src para Phase F1: `enterprise/mcp/` (vacio + `__init__.py`), `enterprise/governance/approvals/` (`__init__.py`), `enterprise/tooling/builtin/{search,web,research,productivity,creative,execution,desktop}/` (markers + `__init__.py`). NO afecta runtime aun

---

## Phase F1: Native-first tools + supervisor fallback + governance Hermes + remover auth de usuario

Objetivo: implementar la estrategia native-first: proveedores como tools nativas (WRAP-SDK/CLONE-UPSTREAM), MCP fallback solo para los que el audit deje fuera. Importar governance F1 de Hermes. Eliminar auth de usuario.

**Aplica decisiones**: D5 (native-first + abstraccion universal de Tool), D4 (eliminar auth de usuario).
**Principle alignment** (constitucion v1.2.0): **#5 Cambios quirurgicos** (REMOVE auth en commit aislado, T046-T051; cero cambios al 2.0); **DIP** (todos los proveedores via `ToolWrapper`, T015-T034); **ISP** (`ToolWrapper` minimo, sin tags/capabilities; esos viven en `CatalogEntry`); **CQS #81** (tool-gating READ-ONLY en `list_tools_for_role`, T044-T045); **DRY** (cliente MCP modularizado de Hermes, no reescrito).

Dependencia: Phase 0 (audit completo + settings + dirs). Spec 009 (`ToolWrapper`/`ToolRegistry`/`HealthMonitor`/LLM Xiaomimimo). Spec 018 (catalogo SSOT).

Independent Test Criteria: 16 proveedores listados como Tools en `ToolRegistry`; matar un MCP fallback dispara restart con backoff; grep auth de usuario en `api/` retorna 0; suite 2.0 sigue verde.

### F1.A — Cliente MCP + Supervisor (fallback)

- [ ] T007 Crear test `tests/enterprise/tooling/test_mcp_client.py` con 4 tests: cliente STDIO conecta y ejecuta `initialize`+`tools/list`; cliente HTTP/SSE conecta y ejecuta `tools/call`; timeout en `initialize` propaga error explicito; cliente cerrado libera el proceso/socket
- [ ] T008 Implementar `src/vigilancia_multiagente/enterprise/tooling/mcp_client.py` portado de Hermes `tools/mcp_tool.py` (STDIO + HTTP + SSE), modularizado ≤400 LOC, con header `# Adapted from Hermes Agent — Original file: tools/mcp_tool.py — License: <MIT|Apache-2.0>`. Hacer T007 verde (FR-003)
- [ ] T009 [P] Crear test `tests/enterprise/mcp/test_process_supervisor.py` con 6 tests: `start_all()` arranca N procesos; `get_status(name)` retorna PID+uptime+last_error; matar proceso dispara restart con backoff exponencial 1→2→4→8→16→32s; tras 5 fallos consecutivos marca `STUCK` y deja de reintentar; `stop_all()` cierra graceful; healthcheck cada 60s actualiza estado
- [ ] T010 Implementar `src/vigilancia_multiagente/enterprise/mcp/process_supervisor.py` (~150 LOC): clase `MCPProcessSupervisor` con `start_all()`, `restart(name)`, `get_status(name)`, `stop_all()`; backoff 1→32s max 5; STUCK + alerta tras 5 fallos. Hacer T009 verde (FR-004, FR-005)
- [ ] T011 [P] Implementar `src/vigilancia_multiagente/enterprise/mcp/healthcheck.py` (≤200 LOC): healthcheck por MCP via `initialize`+`tools/list` cada `healthcheck_interval_sec` (default 60s); expone estado para tool-gating; metricas Prometheus `vigilador_mcp_process_status{name}`, `_restarts_total{name}`, `_uptime_seconds{name}` (FR-006, FR-008)

### F1.B — Adapter MCP→ToolWrapper (fallback) + manifest

- [ ] T012 Crear test `tests/enterprise/tooling/test_mcp_tool_wrapper.py` con 4 tests: `McpToolWrapper` implementa `ToolWrapper` con `is_external_mcp=True`; `healthcheck()` ejecuta `initialize`+`tools/list`; `execute(tool_name, args)` delega `tools/call` JSON-RPC y retorna `ToolResult`; logica de dominio NO se ejecuta in-process
- [ ] T013 Implementar `src/vigilancia_multiagente/enterprise/tooling/mcp_tool_wrapper.py`: adapter MCP→`ToolWrapper` (`is_external_mcp=True`); `requires_auth` derivado del catalogo; `execute()` delega via JSON-RPC. Hacer T012 verde (FR-001)
- [ ] T014 [P] Crear `config/mcp/external.yaml` declarando **solo** los proveedores que el audit (T002) haya dejado como MCP externo (idealmente vacio o muy reducido); campos por entrada: `name`, `command`, `args`, `env` (`${VAR}`), `healthcheck_interval_sec`, `restart_policy`, `log_file`. Si la lista es vacia, dejar el archivo con header explicativo y `mcps: []` (FR-007)

### F1.C — Tools nativas WRAP-SDK por proveedor (los 13 estimados)

> Cada tool nativa: archivo dedicado en `enterprise/tooling/builtin/<domain>/<provider>.py` ≤400 LOC; implementa `ToolWrapper` con `is_external_mcp=False`; usa el SDK/REST del proveedor; tests por archivo.

- [ ] T015 [P] Crear test `tests/enterprise/tooling/builtin/search/test_tavily.py` (3 tests: ToolWrapper interface; web_search y news_search retornan resultados con citas; error sin VT_TAVILY_API_KEY)
- [ ] T016 Implementar `enterprise/tooling/builtin/search/tavily.py` (WRAP-SDK sobre `tavily-python`); capabilities `web_search`, `news_search`. Hacer T015 verde (FR-053, FR-054)
- [ ] T017 [P] Crear test `tests/enterprise/tooling/builtin/search/test_exa.py` + implementar `enterprise/tooling/builtin/search/exa.py` (WRAP-SDK `exa-py`; capabilities `semantic_search`, `find_similar`)
- [ ] T018 [P] Crear test + implementar `enterprise/tooling/builtin/search/brave.py` (WRAP-SDK REST; capabilities `web_search`, `local_search`)
- [ ] T019 [P] Crear test + implementar `enterprise/tooling/builtin/search/serper.py` (WRAP-SDK REST; capabilities `google_search`, `scholar_search`, `patent_search`, `news_search`)
- [ ] T020 [P] Crear test + implementar `enterprise/tooling/builtin/research/serper_patents.py` (WRAP-SDK REST; capabilities `patent_search`, `patent_details`)
- [ ] T021 [P] Crear test + implementar `enterprise/tooling/builtin/web/jina.py` (WRAP-SDK REST `r.jina.ai`; capabilities `reader`, `extract_content`)
- [ ] T022 [P] Crear test + implementar `enterprise/tooling/builtin/web/firecrawl.py` (WRAP-SDK `firecrawl-py`; capabilities `crawl_url`, `scrape_page`, `map_site`)
- [ ] T023 [P] Crear test + implementar `enterprise/tooling/builtin/web/fetch.py` (WRAP-SDK `httpx`; capabilities `fetch_url`, `extract_text`)
- [ ] T024 [P] Crear test + implementar `enterprise/tooling/builtin/web/playwright.py` (WRAP-SDK `playwright` Python, decision #50 cero Node; capabilities `navigate`, `screenshot`, `click`, `fill`)
- [ ] T025 [P] Crear test + implementar `enterprise/tooling/builtin/research/openalex.py` (WRAP-SDK `pyalex`/REST; capabilities `search_works`, `get_authors`, `get_institutions`)
- [ ] T026 [P] Crear test + implementar `enterprise/tooling/builtin/documents/markitdown.py` (WRAP-SDK paquete `markitdown` de Microsoft; capabilities `convert_to_markdown`, `extract_text`)
- [ ] T027 [P] Crear test + implementar `enterprise/tooling/builtin/creative/minimax_image.py` (WRAP-SDK REST/SDK MiniMax; capabilities `generate_image`, `edit_image`)
- [ ] T028 [P] Crear test + implementar `enterprise/tooling/builtin/productivity/google_workspace.py` (WRAP-SDK `google-api-python-client` + OAuth via `oauth_manager`; capabilities `read_docs`, `write_docs`, `read_sheets`, `send_email`)

### F1.D — Tools nativas CLONE-UPSTREAM (Python ya clonados)

- [ ] T029 Crear test `tests/enterprise/tooling/builtin/research/test_arxiv.py` (3 tests: ToolWrapper; `search_papers`/`get_paper`/`list_categories` retornan datos validos; rate-limit propagado como error)
- [ ] T030 Refactorizar `.mcp-servers/arxiv/arxiv-mcp-server-0.5.0/` a `enterprise/tooling/builtin/research/arxiv.py` + modulos auxiliares (≤400 LOC c/u) implementando `ToolWrapper`; header de atribucion al repo upstream + licencia. Hacer T029 verde (FR-053 CLONE-UPSTREAM)
- [ ] T031 [P] Crear test + refactorizar `.mcp-servers/google-scholar/Google-Scholar-MCP-Server-main/` a `enterprise/tooling/builtin/research/google_scholar.py` (capabilities `search_papers`, `get_citations`); header de atribucion + licencia (FR-053)

### F1.E — Sandbox (tool nativa o fallback segun audit)

- [ ] T032 Implementar `enterprise/tooling/builtin/execution/sandbox.py`: si el audit T002 lo dejo WRAP-SDK (e2b-py u otro), tool nativa; si quedo MCP-EXTERNO, declararlo en `external.yaml`. Capabilities `run_code`, `execute_command`. Tests acordes

### F1.F — Universal abstraction: registro de TODOS los proveedores como Tools

- [ ] T033 Crear test `tests/enterprise/tooling/test_universal_tool_registration.py` con 4 tests: al arranque el `ToolRegistry` registra exactamente 16 proveedores como `Tool` (suma de WRAP-SDK + CLONE-UPSTREAM + MCP-EXTERNO segun audit); cada uno expone `name`, `domain`, `is_external_mcp`, capabilities; agentes/Skills solo ven la abstraccion `Tool` (no detectan backend); proveedor sin API key queda gated-out
- [ ] T034 Wirear en `src/vigilancia_multiagente/api/enterprise_composition.py`: al arranque, registrar las tools nativas (T016-T032) como `ToolWrapper(is_external_mcp=False)` y los MCPs fallback como `McpToolWrapper(is_external_mcp=True)` via `MCPProcessSupervisor.start_all()`. Hacer T033 verde (FR-002, FR-054)

### F1.G — Governance Hermes (F1 safety + approvals + tooling base)

- [ ] T035 [P] Crear tests `tests/enterprise/governance/test_{file_safety,redact,path_security,url_safety,website_policy}.py` (3 tests cada uno: input valido/invalido/edge case)
- [ ] T036 Importar `agent/file_safety.py` (Hermes) → `enterprise/governance/file_safety.py` (≤400 LOC, header de atribucion). Hacer test T035 file_safety verde (FR-025, FR-026)
- [ ] T037 [P] Importar `agent/redact.py` → `enterprise/governance/redact.py` (≤400 LOC, atribucion). Hacer test redact verde
- [ ] T038 [P] Importar `tools/path_security.py` → `enterprise/governance/path_security.py` (≤400 LOC, atribucion). Hacer test path_security verde
- [ ] T039 [P] Importar `tools/url_safety.py` → `enterprise/governance/url_safety.py` (≤400 LOC, atribucion). Hacer test url_safety verde
- [ ] T040 [P] Importar `tools/website_policy.py` → `enterprise/governance/website_policy.py` (≤400 LOC, atribucion). Hacer test website_policy verde
- [ ] T041 [P] Crear tests `tests/enterprise/governance/approvals/test_{approval,interrupt,slash_confirm}.py` (3 tests cada uno)
- [ ] T042 [P] Importar `tools/approval.py`, `tools/interrupt.py`, `tools/slash_confirm.py` → `enterprise/governance/approvals/{approval,interrupt,slash_confirm}.py` (≤400 LOC c/u, atribucion). Hacer T041 verde
- [ ] T043 [P] Crear tests + importar `tools/lazy_deps.py`, `tools/schema_sanitizer.py`, `tools/tool_output_limits.py` → `enterprise/tooling/{lazy_deps,schema_sanitizer,output_limits}.py` (≤400 LOC c/u, atribucion) (FR-025)

### F1.H — Tool-gating + politica no-delete (CQS)

- [ ] T044 Crear test `tests/enterprise/tooling/test_tool_gating.py` con 4 tests: tool con `requires_key=true` y env_var ausente NO aparece en `list_tools_for_role`; tool con circuit breaker DOWN excluida; capability `delete_*` excluida del registry salvo whitelist `forget_user`; `list_tools_for_role` es READ-ONLY (no muta `tool_health`)
- [ ] T045 Implementar tool-gating en `enterprise/tooling/tool_registry.py` (modificacion aditiva): metodo `list_tools_for_role` aplica filtros de credenciales + circuit breaker + `tools_delete_whitelist`; CQS preservado (#81). Hacer T044 verde (FR-042, FR-043)

### F1.I — Eliminar auth de usuario (D4) — REMOVE

- [ ] T046 [P] Crear test `tests/api/test_no_user_auth.py` con 3 tests: rutas accesibles sin token de usuario; ningun endpoint retorna 401 por falta de auth de usuario; OAuth de servicio (`oauth_manager`) sigue disponible para conectores
- [ ] T047 ELIMINAR archivo `src/vigilancia_multiagente/api/routes/enterprise_auth.py` (ruta completa de login/sesiones de usuario, ~6 refs) (FR-036)
- [ ] T048 MODIFICAR `src/vigilancia_multiagente/api/router.py`: remover `from .routes import enterprise_auth` y desregistrar el router del `api_v2_router`
- [ ] T049 MODIFICAR `src/vigilancia_multiagente/api/dependencies.py`: remover dependencias de auth de usuario (~10 refs); CONSERVAR las no-auth y las relacionadas con `authenticity` (workstream 2.0, falso positivo)
- [ ] T050 MODIFICAR `src/vigilancia_multiagente/api/routes/enterprise_onboarding.py`: desacoplar la unica ref de auth de usuario; el onboarding NO debe exigir login. Conservar el OAuth de servicio para conectores
- [ ] T051 MODIFICAR `src/vigilancia_multiagente/api/app.py` lifespan: retirar wiring de auth de usuario (si existia); CONSERVAR `oauth_manager` para conectores. Hacer T046 verde (FR-037, FR-038)

### F1.J — Verificacion F1

- [ ] T052 Ejecutar `pytest tests/enterprise/tooling/ tests/enterprise/mcp/ tests/enterprise/governance/ tests/api/test_no_user_auth.py` y confirmar verde. Verificar via `grep -r "Adapted from Hermes Agent" src/vigilancia_multiagente/enterprise/governance/` que cada archivo importado tiene atribucion. Verificar `grep "from vigilancia_multiagente.api.routes.enterprise_auth" -r src/` retorna 0. Suite 2.0 (`pytest tests/application/ tests/infra/`) sigue verde

---


## Phase F2: TurboVec nativo + ingestion + memoria + skills marketplaces (clone en src/, sin claude-local)

Objetivo: indice vectorial nativo `turbovec`, pipeline de ingestion empresarial (Drive primero), memoria frozen-snapshot, marketplaces externos K-Dense + agency-agents clonados dentro de `src/.../_vendor/`, eliminacion de claude-local del runtime.

**Aplica decisiones**: D1 revisada (TurboVec nativo in-process), D2 (clonar marketplaces dentro de `src/`), D3 (eliminar claude-local del runtime).
**Principle alignment** (constitucion v1.2.0): **DIP** (`TurboVecIndex` implementa el port `VectorIndex`, T055; `IngestionConnector` port, T058); **LSP** (`TurboVecIndex` sustituible por cualquier impl del port sin alterar contrato); **#4 Errores estrictos** (libreria `turbovec` DOWN → error explicito, T053; sin fallback silencioso); **SRP/SoC** (orchestrator/chunking/dedup/acl_resolver en archivos separados, T060-T063); **DRY** (reusa Gemini/Cohere del 2.0 sin modificarlos).

Dependencia: Phase F1 (tools + governance + auth removed). Reusa Gemini/Cohere del 2.0 sin modificarlos.

Independent Test Criteria: ingesta 100 docs sample via Drive con citas; libreria `turbovec` no cargada → error explicito; `SkillLoader` registra `external:k-dense` + `external:agency-agents`; `grep claude-local src/.../skill_loader.py` = 0; suite 2.0 verde.

### F2.A — TurboVec nativo in-process (D1 revisada)

- [ ] T053 Crear test `tests/infra/persistence/test_turbovec_index.py` con 5 tests: `pip install turbovec` cargado expone `import turbovec`; `TurboVecIndex.add(chunks)` indexa; `query(embedding, k)` retorna top-k con distancias; `persist()` escribe `<tenant>.tq`; `healthcheck()` retorna DOWN explicito si la libreria falla al importar/inicializar
- [ ] T054 Anadir `turbovec` a `pyproject.toml` como dependencia (paquete PyPI Rust + bindings Python sobre TurboQuant) y validar `pip install -e .` carga la libreria en Windows 11 (FR-009)
- [ ] T055 Implementar `src/vigilancia_multiagente/infra/persistence/turbovec_index.py` (≤400 LOC): adapter `TurboVecIndex` que implementa el port `domain/ports/vector_index.py` (`add`, `query`, `persist`, `rebuild`) llamando in-process a `turbovec`; persistencia local en `~/.vigilador/turbovec/<tenant>.tq`; `healthcheck()` con error explicito si falla. Hacer T053 verde (FR-010, FR-011)

### F2.B — Memoria (frozen snapshot)

- [ ] T056 [P] Crear test `tests/enterprise/memory/test_frozen_snapshot.py` (4 tests: snapshot at session start es inmutable durante la sesion; rebuild solo en `/mode` switch; persistencia en `~/.vigilador/memories/`; carga incremental)
- [ ] T057 Importar Hermes `tools/memory_tool.py` → `src/vigilancia_multiagente/enterprise/memory/frozen_snapshot.py` (≤400 LOC, atribucion `# Adapted from Hermes Agent — Original file: tools/memory_tool.py — License: MIT`); home redirigido a `~/.vigilador/memories/`. Hacer T056 verde (FR-015)

### F2.C — Ingestion pipeline (Drive primero)

- [ ] T058 [P] Crear `src/vigilancia_multiagente/domain/ports/ingestion_connector.py`: port `IngestionConnector` con metodos `discover() -> list[DocumentRef]`, `extract(ref) -> RawDoc`, `acl_for(ref) -> ACLScope` (FR-013)
- [ ] T059 [P] Crear test `tests/enterprise/ingestion/test_orchestrator.py` (5 tests: pipeline completo discovery→ACL→extract→normalize→chunk→dedup→embed→TurboVec→metadata; query semantica retorna citas; ACL filtra resultados por tenant_id; libreria `turbovec` DOWN propaga error; conector OAuth invalido detiene esa fuente sin afectar otras)
- [ ] T060 Implementar `src/vigilancia_multiagente/enterprise/ingestion/orchestrator.py` (≤400 LOC): coordina pipeline; consume `GeminiEmbeddingGateway` y `SemanticReranker` del 2.0 via sus ports (FR-012, FR-014). Hacer T059 verde
- [ ] T061 [P] Implementar `src/vigilancia_multiagente/enterprise/ingestion/chunking.py` (≤400 LOC): chunking por tokens con overlap configurable; tests propios
- [ ] T062 [P] Implementar `src/vigilancia_multiagente/enterprise/ingestion/dedup.py` (≤400 LOC): dedup por hash + similitud; tests propios
- [ ] T063 [P] Implementar `src/vigilancia_multiagente/enterprise/ingestion/acl_resolver.py` (≤400 LOC): resuelve `ACLScope(tenant_id, roles[], users[])` por documento; aplica filtro WHERE en `query`; tests propios
- [ ] T064 [P] Crear test `tests/enterprise/ingestion/connectors/test_google_drive.py` (4 tests: discovery por carpeta; extract de DOC/SHEET; OAuth scopes Drive `drive.readonly`/`drive.file` (sin delete); error sin VT_GOOGLE_CLIENT_ID/SECRET)
- [ ] T065 Implementar `src/vigilancia_multiagente/enterprise/ingestion/connectors/google_drive.py` (≤400 LOC): connector Drive primero usando `oauth_manager` con scopes sin delete. Hacer T064 verde (FR-013, FR-016)

### F2.D — Skills marketplaces clonados en src/ (D2) + adapters

- [ ] T066 Clonar `https://github.com/K-Dense-AI/scientific-agent-skills` dentro de `src/vigilancia_multiagente/enterprise/skills_marketplace/_vendor/k_dense/` (preservar `LICENSE`, registrar URL+commit_sha+content_hash en `docs/skills-marketplaces-attribution.md`) (FR-031)
- [ ] T067 [P] Clonar `https://github.com/msitarzewski/agency-agents` dentro de `src/vigilancia_multiagente/enterprise/skills_marketplace/_vendor/agency_agents/` (preservar `LICENSE`, registrar URL+commit_sha+content_hash en `docs/skills-marketplaces-attribution.md`) (FR-031)
- [ ] T068 [P] Crear test `tests/enterprise/skills_marketplace/test_k_dense_adapter.py` (4 tests: scan de `_vendor/k_dense/<categoria>/<id>/SKILL.md`; normaliza a schema unificado SKILL.md con `source: external:k-dense`; mapea categorias a taxonomia Vigilador; falla si frontmatter invalido)
- [ ] T069 Implementar `src/vigilancia_multiagente/enterprise/skills_marketplace/k_dense_adapter.py` (~150 LOC): adapter que produce `SkillCard` desde repos clonados (FR-032). Hacer T068 verde
- [ ] T070 [P] Crear test `tests/enterprise/skills_marketplace/test_agency_agents_adapter.py` (4 tests: scan de `_vendor/agency_agents/<division>/<agent>/`; cada agent → Skill con `source: external:agency-agents`, tags=division+roles, audit.level=alto; inyeccion de do/dont_rules)
- [ ] T071 Implementar `src/vigilancia_multiagente/enterprise/skills_marketplace/agency_agents_adapter.py` (~200 LOC). Hacer T070 verde (FR-032)

### F2.E — Eliminar claude-local del runtime (D3) — REMOVE

- [ ] T072 Crear test `tests/enterprise/skills_marketplace/test_no_claude_local.py` (3 tests: `SkillLoader` con sources `["curated","learned","external:k-dense","external:agency-agents"]` carga sin error; runtime no intenta abrir `.claude/skills/`; cualquier referencia a `external:claude-local` retorna error de fuente desconocida)
- [ ] T073 MODIFICAR `src/vigilancia_multiagente/enterprise/skills_marketplace/skill_loader.py`: eliminar import de `ClaudeLocalAdapter` (linea ~9), parametro `claude_local_path` del ctor (lineas ~50,58), rama `if "external:claude-local" in self._sources_enabled` (~71-72), metodo `_load_external_claude_local` (~136-138). Cablear ramas K-Dense y agency-agents en su lugar. Hacer T072 verde (FR-033)

### F2.F — SkillRegistry + discovery 3 niveles + CommandSkill

- [ ] T074 [P] Crear test `tests/enterprise/skills_marketplace/test_skill_registry.py` (5 tests: SkillCard ≤80 chars descripcion; SkillSummary inputs/outputs; SkillBody full SKILL.md; filtra por mode_compatible; reranking por health de capabilities)
- [ ] T075 Extender `src/vigilancia_multiagente/enterprise/skills_marketplace/skill_registry.py`: discovery 3 niveles (SkillCard/SkillSummary/SkillBody); filtra por modo activo, permisos, capability health, `company_geo`; embed search sobre description/tags/capabilities. Hacer T074 verde (FR-034)
- [ ] T076 [P] Crear test `tests/enterprise/skills_marketplace/test_skill_unavailable.py` (2 tests: skill con `required_capabilities` no presentes en `ToolRegistry` → marcado `unavailable` sin abortar carga; skill `unavailable` no aparece en discovery)
- [ ] T077 Implementar logica de `unavailable` en `skill_loader.py` (FR-035). Hacer T076 verde
- [ ] T078 [P] Crear test `tests/enterprise/skills_marketplace/test_command_skill.py` (4 tests: `CommandSkill` con `parameters`, `permissions`, `preconditions`, `requires_sandbox`, `hash`; comando destructivo (`requires_sandbox=true`) NO ejecuta sin aprobacion; comando con preconditions no satisfechas falla con error claro; hash cambia → revalidacion)
- [ ] T079 Implementar modelo `CommandSkill` en `src/vigilancia_multiagente/enterprise/skills_marketplace/skill_models.py` (extension); soportarlo en `SkillLoader` cuando un marketplace declare comandos. Hacer T078 verde (FR-052)

### F2.G — Verificacion F2

- [ ] T080 Ejecutar `pytest tests/infra/persistence/test_turbovec_index.py tests/enterprise/memory/ tests/enterprise/ingestion/ tests/enterprise/skills_marketplace/` y confirmar verde. Validar manualmente: ingesta de 100 docs sample via Drive (con `VT_GOOGLE_CLIENT_ID/SECRET` configurados) + query semantica retorna ≥1 resultado con cita; `grep -r "claude-local" src/vigilancia_multiagente/enterprise/skills_marketplace/skill_loader.py` retorna 0; `grep -r "claude_local_path" src/vigilancia_multiagente/config/settings.py` retorna 0

---


## Phase F3a: Tools Tier 1 nuevas (documents) + computer use Win11

Objetivo: las 3 tools nuevas de documents (`template_render`, `docx_generate`, `pdf_generate`) ya en builtin/documents/; computer use desde Hermes con backend Win11 + gate de aprobacion en acciones destructivas.

Dependencia: Phase F1 (governance file_safety/path_security/redact + ToolRegistry); Phase 0 (catalogo + audit); Phase F2 no es prerequisito directo.

Independent Test Criteria: 4 tools de documents listadas en `ToolRegistry`; computer use ejecuta screenshot+click; accion destructiva exige aprobacion; sin display retorna error explicito.

### F3a.A — 3 tools nuevas de documents

- [ ] T081 [P] Crear test `tests/enterprise/tooling/builtin/documents/test_template_render.py` (3 tests: ToolWrapper interface; renderiza Jinja2 MD con variables; template inexistente → error)
- [ ] T082 Implementar `src/vigilancia_multiagente/enterprise/tooling/builtin/documents/template_render.py` (~300 LOC) con Jinja2/docxtpl; capabilities `render_template`, `interpolate_variables`. Hacer T081 verde (FR-028)
- [ ] T083 [P] Crear test + implementar `enterprise/tooling/builtin/documents/docx_generate.py` (~250 LOC, `python-docx`); capabilities `generate_docx`, `format_document` (FR-028)
- [ ] T084 [P] Crear test + implementar `enterprise/tooling/builtin/documents/pdf_generate.py` (~250 LOC, WeasyPrint); capabilities `generate_pdf`, `html_to_pdf` (FR-028)

### F3a.B — Computer use Windows 11

- [ ] T085 Crear test `tests/enterprise/tooling/builtin/desktop/test_computer_use.py` con 6 tests: `ToolWrapper` con `domain="desktop"`; `screenshot` retorna imagen via `mss`; `click` aplica via `pyautogui` con coordenada o ventana via `pygetwindow`; `fill`/`type` aplica modificadores; sin display retorna error explicito (FR-030 EC-08); accion en app fuera de `computer_use_app_allowlist` exige gate de aprobacion (FR-030)
- [ ] T086 Importar Hermes `tools/computer_use/schema.py` y `tools/computer_use/tool.py` → `src/vigilancia_multiagente/enterprise/tooling/builtin/desktop/computer_use/{schema,tool}.py` (≤400 LOC, atribucion). Conservar contratos de input/output (FR-029)
- [ ] T087 Reescribir el backend para Windows 11 en `src/vigilancia_multiagente/enterprise/tooling/builtin/desktop/computer_use/windows_backend.py` usando `pyautogui` + `pygetwindow` + `mss`; eliminar dependencia macOS `cua_backend.py` original (FR-029)
- [ ] T088 Implementar gate de aprobacion en `tool.py`: antes de acciones destructivas (cerrar sin guardar, instalar, settings del sistema) o apps fuera de `computer_use_app_allowlist`, invocar `enterprise/governance/approvals/approval.py`. Sin display → error explicito. Hacer T085 verde (FR-030)
- [ ] T089 Anadir entrada `computer_use` al catalogo SSOT (`config/tools/catalog.yaml`): `domain: desktop`, `strategy: COPY-HERMES`, `runtime: python_internal`, `mvp: true` (extension 021 sobre las 20 base); registrar en `ToolRegistry` (FR-029)

### F3a.C — Verificacion F3a

- [ ] T090 Ejecutar `pytest tests/enterprise/tooling/builtin/documents/ tests/enterprise/tooling/builtin/desktop/` y confirmar verde. Verificar `wc -l src/vigilancia_multiagente/enterprise/tooling/builtin/desktop/computer_use/*.py` cada archivo ≤400 LOC. Verificar `grep -r "Adapted from Hermes Agent" src/vigilancia_multiagente/enterprise/tooling/builtin/desktop/` aparece. `tools list` muestra 21 tools MVP activas (16 proveedores + 4 documents + computer_use)

---

## Phase F4a: Orquestacion (Mode/Complexity/Playbook) + 3 modos + 3 playbooks + frontend MVP + onboarding + SubagentRegistry

Objetivo: cablear el flujo Channel→Mode→Playbook→Agent→Skill→Tool; los 3 modos y 3 playbooks MVP operativos; `technology-watch` envuelve el `BranchCoordinator` 2.0; frontend 4 superficies sin login; onboarding wizard sin auth de usuario.

**Aplica decisiones**: D4 (frontend y onboarding sin login).
**Principle alignment** (constitucion v1.2.0): **OCP** (modos y playbooks en YAML — extensibles sin modificar `PlaybookRunner`/`ModeLoader`, T101-T108); **POLA** (`ComplexityClassifier` loggea su decision, T091-T092; `ModeResolver` loguea el modo elegido); **#5 Cambios quirurgicos** (`technology-watch` envuelve `BranchCoordinator` 2.0 sin tocarlo, T107-T108; verificable via `git diff --stat` en T141); **Convencion sobre configuracion** (defaults sensatos en cada modo: `tone`, `intensity:REACTIVE`, `tools.domains`); **DIP** (`ModeResolver` implementa `ModeResolutionStrategy`).

Dependencia: Phases F1+F2+F3a. 2.0 preservado (`application/execution/branch_coordinator.py` y 6 ramas).

Independent Test Criteria: `/mode vigilancia-tech` corre 6 ramas 2.0 sin regresiones; `/mode default` → general; `/mode CEO` → deep-research; onboarding completable <15 min sin login; frontend lista 4 superficies; SubagentRegistry registra spawn con depth/status.

### F4a.A — ComplexityClassifier + PlaybookRunner

- [ ] T091 [P] Crear test `tests/enterprise/orchestration/test_complexity_classifier.py` (4 tests: clasifica SIMPLE/MODERADA/COMPLEJA con 1 LLM call; loggea razon (POLA); usa el adapter LLM seleccionado en settings; timeout en LLM propaga error)
- [ ] T092 Implementar `src/vigilancia_multiagente/enterprise/orchestration/complexity_classifier.py` (≤300 LOC); 1 llamada LLM ~50 tok prompt + ~10 tok response. Hacer T091 verde (FR-017)
- [ ] T093 [P] Crear test `tests/enterprise/orchestration/test_playbook_runner.py` (6 tests: carga `config/playbooks/<id>.yaml` y valida schema; rechaza si `mode_compatible` no incluye el modo activo; instancia agents segun `agents[]`; ejecuta flow `sequential`; ejecuta flow `rounds`; aplica `guardrails` (max_total_llm_calls))
- [ ] T094 Implementar `src/vigilancia_multiagente/enterprise/orchestration/playbook_runner.py` (≤400 LOC). Hacer T093 verde (FR-018)

### F4a.B — ModeResolver + ModeContext + ModeLoader

- [ ] T095 [P] Crear test `tests/enterprise/modes/test_mode_resolver.py` (5 tests: resuelve `/mode <id>` explicito; autodetect por canal en `config/channels/<canal>.yaml`; heuristica regex sobre primer mensaje; fallback LLM clasifica intent→mode; cae a `default`)
- [ ] T096 Implementar/extender `src/vigilancia_multiagente/enterprise/modes/mode_resolver.py` con la cascada de 5 pasos; conectar al flujo de request en `api/app.py`/dispatcher. Hacer T095 verde (FR-019)
- [ ] T097 [P] Crear test `tests/enterprise/modes/test_mode_context.py` (3 tests: snapshot frozen al inicio de sesion; inmutable durante la sesion; rebuild solo en `/mode otro`)
- [ ] T098 Implementar `src/vigilancia_multiagente/enterprise/modes/mode_context.py` (frozen dataclass) con SOUL overlay + COMPANY subset + `company_geo` + skills allowlist + playbooks allowed + tools allowlist. Hacer T097 verde (FR-019)
- [ ] T099 [P] Crear test `tests/enterprise/modes/test_mode_loader.py` (4 tests: valida skills/playbooks/tools referenciados existen; rechaza modo invalido; `audit.approval_required_for_files` valida paths; `company_geo` con al menos `country`)
- [ ] T100 Extender `src/vigilancia_multiagente/enterprise/modes/mode_loader.py`: validacion en boot; modos invalidos excluidos del listing `/mode`. Hacer T099 verde (FR-020)

### F4a.C — 3 modos MVP + deprecacion de modos roadmap

- [ ] T101 [P] Crear/normalizar `config/modes/default.yaml` con campos: `id`, `display_name="Asistente generalista"`, `soul_overlay {tone:"neutro, formal"}`, `company_subset {files:["identity.md"]}`, `company_geo {country:"Colombia"}` por defecto, `skills.categories:["*:FREE"]`, `playbooks.default:"general"`, `tools.domains:["search","web","documents"]`, `mode_settings.intensity:"REACTIVE"` (FR-021)
- [ ] T102 [P] Crear/normalizar `config/modes/vigilancia-tech.yaml`: `playbooks.default:"technology-watch"`, `tools.domains:["search","research","web","analytics"]`, conservando comportamiento del 2.0 (FR-021)
- [ ] T103 [P] Crear/normalizar `config/modes/CEO.yaml`: `playbooks.default:"deep-research"` (decision-debate esta deprecado por T110, F4b roadmap); `playbooks.allowed:["deep-research","general"]` con comentario YAML `# roadmap F4b: decision-debate, market-research, goal-pursuit`; `tools.domains:["search","research","productivity","communication","analytics"]` (FR-021)
- [ ] T104 DEPRECATE (no DELETE) `config/modes/{cfo,consultor-legal,marketing,vendedor-b2b,operaciones-pyme}.yaml`: anadir cabecera YAML `# ROADMAP F4c — fuera de MVP 021; no registrar en runtime` y excluirlos del wiring del `ModeLoader` salvo flag (FR-041)

### F4a.D — 3 playbooks MVP + deprecacion de playbooks roadmap

- [ ] T105 [P] Crear/normalizar `config/playbooks/general.yaml`: 1 agente generalista; `tool discovery` progresivo; `flow.type: "sequential"` con 1 fase; `mode_compatible` incluye `default` y todos (FR-022, FR-024)
- [ ] T106 [P] Crear/normalizar `config/playbooks/deep-research.yaml`: flow Clarify→Plan→Approve→Execute→Fuse→Report; `mode_compatible: "*"` (FR-022, FR-024)
- [ ] T107 Crear `plugins/technology-watch/__init__.py` + `plugins/technology-watch/coordinator_wrapper.py` que envuelve `application/execution/branch_coordinator.py` (2.0) sin reimplementarlo; expone interfaz que `PlaybookRunner` invoca (FR-023)
- [ ] T108 Normalizar `config/playbooks/technology-watch.yaml` para que delegue al `plugins/technology-watch/coordinator_wrapper.py`; declara los 6 agentes de rama del 2.0; `mode_compatible: ["vigilancia-tech","CEO","default"]` (FR-022, FR-023)
- [ ] T109 [P] Crear test `tests/enterprise/orchestration/test_technology_watch_wraps_2_0.py` (3 tests: invocar el playbook ejecuta `BranchCoordinator` 2.0 con sus 6 ramas; outputs structured + free-form devueltos; suite 2.0 sigue verde tras la integracion)
- [ ] T110 DEPRECATE (no DELETE) `config/playbooks/{decision-debate,goal-pursuit,app-development,artifact-development}.yaml` con cabecera `# ROADMAP F4b — fuera de MVP 021; no registrar en runtime` (FR-041)

### F4a.E — SubagentRegistry basico

- [ ] T111 [P] Crear test `tests/enterprise/orchestration/test_subagent_registry.py` (4 tests: spawn registra fila en tabla `subagents` con `depth`/`status`; `parent_session_id` y `parent_agent_id` enlazan; status valido `ACTIVE|COMPLETED|FAILED`; depth >0 cuando hay padre)
- [ ] T112 Crear migracion SQL `infra/db/migrations/021_subagents.sql`: tabla `subagents (id UUID, tenant_id, parent_session_id, parent_agent_id, depth INT, role, spawn_reason, status, last_progress_at, created_at, completed_at)`
- [ ] T113 Implementar `src/vigilancia_multiagente/enterprise/orchestration/subagent_registry.py` (≤300 LOC): spawn/track basico; pause/resume/approval = roadmap. Hacer T111 verde (FR-051)

### F4a.F — Frontend MVP 4 superficies (sin login)

- [ ] T114 [P] Crear estructura `frontend/src/enterprise/{onboarding,chat,sources,admin}/` con `index.tsx` placeholder en cada una; sin pantalla de login (D4) (FR-046)
- [ ] T115 Implementar `frontend/src/enterprise/onboarding/`: wizard que captura empresa + `company_geo` + seleccion `embedding_provider`/`reranker_provider` + conexion Drive + lanza primera ingestion (FR-047, FR-049)
- [ ] T116 [P] Implementar `frontend/src/enterprise/chat/`: chat con selector de modo (`/mode <id>`) + visor de workstreams del 2.0 (reusa componentes existentes) + historial basico (FR-046)
- [ ] T117 [P] Implementar `frontend/src/enterprise/sources/`: vista de conectores (Drive activo, OneDrive/Outlook/Gmail diferidos) + progreso de indexacion (FR-046)
- [ ] T118 [P] Implementar `frontend/src/enterprise/admin/`: lista de tools/MCPs MVP con estado UP/DOWN (lee de `MCPProcessSupervisor`/`HealthMonitor` y `ToolRegistry`) + configurar API keys (FR-050)

### F4a.G — Onboarding endpoints sin auth

- [ ] T119 [P] Crear test `tests/api/routes/test_enterprise_onboarding.py` (5 tests: POST `/api/v2/enterprise/onboarding/company` crea `config/company/identity.md` + `company_geo` sin token de usuario; POST `/providers` fija `embedding_provider`/`reranker_provider`; POST `/connectors/drive` inicia OAuth de servicio; POST `/ingest/initial` lanza ingestion; flujo completable <15 min)
- [ ] T120 Implementar (o ampliar) `src/vigilancia_multiagente/api/routes/enterprise_onboarding.py` con los 4 endpoints; ningun endpoint exige login de usuario (D4); usa `oauth_manager` para conectores. Hacer T119 verde (FR-047, FR-048)

### F4a.H — Wiring final del flujo en API

- [ ] T121 Cablear en `src/vigilancia_multiagente/api/app.py` lifespan + dispatcher: `ChannelGateway → ModeResolver → ModeContext → OrchestratorService (2.0) → ComplexityClassifier → PlaybookRunner → (BranchCoordinator|general|deep-research) → ToolRegistry`. Verificar end-to-end con `/mode vigilancia-tech` (FR-019)

### F4a.I — Verificacion F4a

- [ ] T122 Ejecutar `pytest tests/enterprise/orchestration/ tests/enterprise/modes/ tests/api/routes/test_enterprise_onboarding.py` y confirmar verde. Manual: `/mode vigilancia-tech` corre 6 ramas 2.0 sin regresiones; `/mode default` ejecuta `general`; `/mode CEO` ejecuta `deep-research` con structured + free-form; frontend lista 4 superficies y arranca sin login. Suite 2.0 sigue verde

---


## Phase F5a: Dreaming basico + PI defense regex + audit JSONL

Objetivo: ciclo nocturno minimo (solo 2 fases: `memory_consolidation` + `ingestion_sync`); deteccion de prompt injection regex+Lakera con cuarentena; audit trail JSONL. Fases 2-4, 6-10 + 7 loops + `agent_modifier` + tabla SQL `agent_modifications` + `anomaly_detector` quedan ROADMAP (deprecadas).

Dependencia: Phases F2 (ingestion para `ingestion_sync`) + F1 (governance).

Independent Test Criteria: cron 3 AM ejecuta solo 2 fases; payload `"ignore previous instructions"` en input externo → cuarentena; `~/.vigilador/audit/events_<fecha>.jsonl` registra eventos; nada de loops/fases extra se ejecuta.

### F5a.A — Dreaming scheduler + 2 fases MVP + reporter

- [ ] T123 [P] Crear test `tests/enterprise/dreaming/test_scheduler_mvp.py` (4 tests: APScheduler arma job cron 3AM; trigger idle >10 min dispara fuera del cron; el scheduler MVP solo registra `memory_consolidation` + `ingestion_sync`; ninguna fase de roadmap se registra)
- [ ] T124 MODIFICAR `src/vigilancia_multiagente/enterprise/dreaming/scheduler.py`: limitar el registro a las 2 fases MVP via lista explicita; **NO** registrar `loops/*` ni las 9 fases roadmap. Hacer T123 verde (FR-039, FR-040)
- [ ] T125 [P] Verificar (no implementar) que `enterprise/dreaming/phases/memory_consolidation.py` y `enterprise/dreaming/phases/ingestion_sync.py` existen y funcionan in-place (codigo previo). Si no funcionan en MVP, ajustar minimamente para consumir `frozen_snapshot` (T057) e `IngestionOrchestrator` (T060) (FR-040)
- [ ] T126 [P] Crear `src/vigilancia_multiagente/enterprise/dreaming/reporter.py` (≤200 LOC): reporter minimo MVP que loguea completitud por fase en JSONL (`~/.vigilador/audit/dreaming_<fecha>.jsonl`); el Dreaming Report extendido queda roadmap (FR-040)

### F5a.B — Deprecacion de fases extra + 7 loops (DEPRECATE no DELETE)

- [ ] T127 Anadir cabecera `# ROADMAP F5b — fuera de MVP 021; no registrar en runtime` a las 9 fases extra de `enterprise/dreaming/phases/` (`admin_repo_maintenance.py`, `config_refresher.py`, `dreaming_report.py`, `index_maintenance.py`, `regulatory_watch.py`, `scheduled_artifacts.py`, `self_improvement.py`, `skill_curator.py`) **conservar** `memory_consolidation.py` e `ingestion_sync.py` sin cabecera (FR-041)
- [ ] T128 [P] Anadir misma cabecera ROADMAP a los 7 loops en `enterprise/dreaming/loops/` (`admin_repo_loop.py`, `company_self_update.py`, `prompt_self_improvement.py`, `regulatory_watcher.py`, `skill_learning.py`, `tool_composition.py`, `writing_style.py`) (FR-041)
- [ ] T129 [P] Anadir cabecera ROADMAP a los modulos roadmap-only que ya estan construidos: `enterprise/orchestration/goal_pursuit/*.py` (8 archivos, F4b), `enterprise/orchestration/app_development/*.py` (12 archivos, F4b), `enterprise/artifacts/*.py` (10 archivos, F4b). Confirmar que ninguno se importa desde `api/app.py` ni desde los 3 playbooks MVP (FR-041)
- [ ] T130 Verificar wiring: `grep -r "from vigilancia_multiagente.enterprise.dreaming.loops" src/` retorna 0 imports activos en runtime; `grep -r "from vigilancia_multiagente.enterprise.orchestration.goal_pursuit" src/` retorna 0 imports activos. Si aparecen imports vivos, removerlos (FR-041)

### F5a.C — PI defense regex + Lakera

- [ ] T131 [P] Crear test `tests/enterprise/governance/test_prompt_injection_detector.py` (5 tests: payload `"ignore previous instructions"` → cuarentena; payload Lakera dataset positivo → cuarentena; input limpio pasa; positivo registra evento JSONL en `~/.vigilador/audit/pi_quarantine_<fecha>.jsonl`; tasa de FP <5% sobre dataset de 100 inputs validos)
- [ ] T132 Implementar `src/vigilancia_multiagente/enterprise/governance/prompt_injection_detector.py` (~200 LOC): heuristicas regex + dataset Lakera; pipeline: TODO input externo (emails, PDFs, scraping, mensajes) pasa por el detector ANTES del LLM. Embedding layer = roadmap. Hacer T131 verde (FR-044)
- [ ] T133 Wirear el detector en los puntos de entrada de input externo: ingestion (`enterprise/ingestion/orchestrator.py` antes de embed) y connectors. Si positivo, NO pasar al LLM, registrar en JSONL y emitir alerta

### F5a.D — Audit trail JSONL + index

- [ ] T134 [P] Crear test `tests/enterprise/governance/test_audit_log.py` (5 tests: invocacion de tool registra evento JSONL; llamada LLM registra prompt+model+tokens+latency; decision de `ComplexityClassifier` registra entrada+salida+razon; spawn de subagente registra `parent`/`depth`; rotacion diaria por `events_<fecha>.jsonl`)
- [ ] T135 Implementar `src/vigilancia_multiagente/enterprise/governance/audit_log.py` (~250 LOC): escribe JSONL en `~/.vigilador/audit/`; tabla SQL `agent_modifications` queda ROADMAP (no se crea ahora). Hacer T134 verde (FR-045)
- [ ] T136 Wirear `audit_log` en `ToolRegistry.execute()`, en el adapter LLM (Xiaomimimo wrapper de spec 009), en `ComplexityClassifier`, y en `SubagentRegistry.spawn()`. Verificar end-to-end ejecutando una sesion completa y leyendo el JSONL del dia (FR-045)

### F5a.E — Verificacion F5a

- [ ] T137 Ejecutar `pytest tests/enterprise/dreaming/ tests/enterprise/governance/test_prompt_injection_detector.py tests/enterprise/governance/test_audit_log.py` y confirmar verde. Manual: trigger del cron 3 AM produce log de completitud para SOLO `memory_consolidation` + `ingestion_sync` (verificar contando entradas en `dreaming_<fecha>.jsonl`); enviar payload `"ignore previous instructions"` desde un connector → cuarentena visible en `pi_quarantine_<fecha>.jsonl`. Verificar `grep -r "ROADMAP F5b" src/vigilancia_multiagente/enterprise/dreaming/loops/` cubre los 7 archivos

---

## Phase Polish: Verificacion integral (SC-001..SC-015) + cierre

Objetivo: verificar los 15 success criteria del spec con evidencia, suite completa verde, layer-imports limpio, atribucion presente, plan-coverage al 100% material MVP.

Dependencia: Phases 0-F5a completadas.

Independent Test Criteria: SC-001..SC-015 cumplidos con artefactos verificables; pytest completo (2.0 + 3.0) verde; check-layer-imports 0 violaciones nuevas; basedpyright + ruff limpios sobre codigo nuevo.

- [ ] T138 [P] **SC-001 + SC-002**: ejecutar `tools list` (CLI o endpoint admin) y confirmar que el `ToolRegistry` registra los 16 proveedores como `Tool` (suma de WRAP-SDK + CLONE-UPSTREAM + MCP-EXTERNO) + 4 documents + computer_use = 21 tools MVP activas. Ejecutar `execute()` desde un agente sobre al menos un proveedor de cada dominio MVP (search/web/research/documents) y verificar `ToolResult` valido sin que el agente conozca el backend (logs `vigilador.tools.<domain>.<id>` o `vigilador.mcp_ext.<id>`)
- [ ] T139 [P] **SC-003**: matar manualmente un proceso MCP fallback (si lo hay tras audit) y verificar restart con backoff 1→32s; tras 5 fallos consecutivos confirmar `STUCK` + alerta + no mas reintentos. Si el audit dejo MCP-EXTERNO=0, declarar SC-003 como N/A con nota
- [ ] T140 [P] **SC-004**: ingesta 100 docs sample via Drive + query semantica retorna ≥1 resultado con cita; desinstalar `turbovec` (`pip uninstall turbovec`) y verificar que `TurboVecIndex.healthcheck()` reporta DOWN con error explicito (no fallback silencioso); reinstalar
- [ ] T141 [P] **SC-005**: `/mode vigilancia-tech` ejecuta el playbook `technology-watch` que envuelve `BranchCoordinator` con sus 6 ramas; `pytest tests/application/` (suite 2.0) sigue 100% verde. Verificar 0 modificaciones a `application/execution/branch_coordinator.py` con `git diff --stat`
- [ ] T142 [P] **SC-006**: `/mode default` ejecuta `general`; `/mode CEO` ejecuta `deep-research` con structured + free-form (verificable por el shape del output)
- [ ] T143 [P] **SC-007**: `grep -r "external:k-dense" src/vigilancia_multiagente/enterprise/skills_marketplace/` muestra registro; mismo para `external:agency-agents`. `grep -r "claude-local" src/vigilancia_multiagente/` retorna 0 referencias en runtime (excepto historiales/specs documentales)
- [ ] T144 [P] **SC-008**: el sistema arranca sin pantalla de login; `grep -r "from vigilancia_multiagente.api.routes.enterprise_auth" src/` retorna 0; `oauth_manager` sigue permitiendo conectar Drive (validable via UI o curl al endpoint OAuth)
- [ ] T145 [P] **SC-009**: en Win11, `computer_use` ejecuta `screenshot` + `click`; intentar una accion destructiva exige aprobacion (gate); en headless retorna error explicito de "no display"
- [ ] T146 [P] **SC-010**: `find src/vigilancia_multiagente/enterprise -name '*.py' -exec wc -l {} \;` confirma ≤400 LOC por modulo en codigo importado; `grep -r "Adapted from Hermes Agent" src/vigilancia_multiagente/enterprise/` lista todos los archivos importados con atribucion. **FR-027 (OpenClaw solo referencia)**: `find src/ -path '*openclaw*'` retorna 0 archivos copiados; `grep -ri "openclaw" src/vigilancia_multiagente/` retorna solo comentarios de referencia conceptual (no imports ni codigo copiado)
- [ ] T147 [P] **SC-011**: leer `~/.vigilador/audit/dreaming_<fecha>.jsonl` tras un ciclo cron y confirmar que registra exactamente `memory_consolidation` e `ingestion_sync`, ninguna fase extra. `grep -r "ROADMAP F5b" src/vigilancia_multiagente/enterprise/dreaming/` cubre las 9 fases extra + 7 loops
- [ ] T148 [P] **SC-012**: una tool sin `env_var` configurada NO aparece en `list_tools_for_role`; capabilities `delete_*` excluidas (excepto `forget_user`); enviar payload `"ignore previous instructions"` → entry en `pi_quarantine_<fecha>.jsonl`; auditoria diaria en `events_<fecha>.jsonl` con eventos de tool/LLM/complexity/subagent
- [ ] T149 [P] **SC-013**: simular onboarding completo (POST endpoints `/onboarding/company`, `/providers`, `/connectors/drive`, `/ingest/initial`) en menos de 15 min sin login; las 4 superficies del frontend MVP cargan operativas
- [ ] T150 [P] **SC-014**: la superficie `frontend/src/enterprise/admin/` lista las tools/MCPs con estado UP/DOWN; configurar una API key faltante muestra la tool como disponible
- [ ] T151 [P] **SC-015**: `SubagentRegistry.spawn()` registra fila con `depth`/`status`; un `CommandSkill` con `requires_sandbox=true` no ejecuta sin pasar el gate de `enterprise/governance/approvals/approval.py`
- [ ] T152 Ejecutar `pytest -q` completo (2.0 + 3.0) y confirmar 0 regresiones (suite 2.0 al 100%). Lista de tests nuevos del 021 todos verdes
- [ ] T153 Ejecutar `python scripts/check-layer-imports.py` y confirmar 0 violaciones nuevas; `ruff check src/ tests/` sin issues nuevos en codigo de 021; `basedpyright` (modo standard) sin nuevos errores en codigo nuevo
- [ ] T154 Verificar inventario final: `find src/vigilancia_multiagente/enterprise/skills_marketplace/_vendor -maxdepth 2 -type d` muestra `k_dense/` y `agency_agents/`. `python scripts/audit_mcp_strategy.py --report` muestra estrategia final por proveedor coherente con la Tabla 1 del plan
- [ ] T155 Generar `docs/release-notes-021.md` con: 5 correcciones del usuario aplicadas (D1..D5); 21 tools MVP listadas con su estrategia; matriz FR→archivo→test; codigo deprecado (paths con cabecera ROADMAP); SDKs/paquetes nuevos en `pyproject.toml` (incluye `turbovec`)

---

## Dependencies

- **Phase 0** (Setup) precede a TODAS las fases. T001 (audit) precede al wiring final de F1.F.
- **Phase F1** precede a F2 (governance + tools necesarios para ingestion+skills) y a F3a (governance file_safety necesario para `file_system`/`computer_use`).
- **Phase F2** precede a F4a (Mode/Playbook necesitan TurboVec+ingestion+skills disponibles).
- **Phase F3a** puede solaparse con F2 (independientes excepto por governance comun).
- **Phase F4a** precede a F5a (audit trail consume eventos del runtime; PI defense se inyecta en ingestion).
- **Phase F5a** precede a Polish (verificacion).
- **Spec 009** es prerequisito (`ToolWrapper`, `ToolRegistry`, `HealthMonitor`, LLM Xiaomimimo).
- **Spec 018** es prerequisito (catalogo SSOT, regla <5000 LOC, ToolWrapper contract).
- **2.0 preservado** intocado: `application/execution/branch_coordinator.py`, 6 agentes de rama, `infra/embeddings/gemini_gateway.py`, `infra/reranking/semantic_reranker.py`, `infra/mcp/mcp-providers.json`.

### Dependencias internas clave

- T001 → T002 → T014 (audit decide que entra a `external.yaml`).
- T007 → T008 (test antes de implementacion del cliente MCP).
- T009 → T010 (test antes de supervisor).
- T012 → T013 (test antes del wrapper).
- T034 (registro universal) requiere T013, T016, T017..T032 completos.
- T046 → T047..T051 (test de no-auth antes de ELIMINAR).
- T053 → T054 → T055 (test → install → impl TurboVec).
- T058 → T060 (port `IngestionConnector` antes de orchestrator).
- T072 → T073 (test no-claude-local antes de la modificacion del loader).
- T085 → T086..T088 (tests computer_use antes de extraccion+backend+gate).
- T091..T100 (Mode/Complexity/PlaybookRunner) preceden a T101..T110 (modos+playbooks YAML).
- T107 → T108 → T109 (wrapper antes del YAML; YAML antes del test de envoltura).
- T123..T126 (Dreaming MVP) preceden a T127..T130 (deprecaciones).

---

## Parallel Execution Examples

### Phase 0

- T003, T004, T005, T006 son [P] entre si tras T001+T002.

### Phase F1 — Bloque tools nativas (mas paralelo del proyecto)

Tras T013 (`McpToolWrapper`):

- T015..T028 son **todos [P]** (cada tool nativa en archivo distinto + test propio); pueden distribuirse en paralelo entre 12+ desarrolladores.
- T029..T031 (CLONE-UPSTREAM arxiv/google_scholar) en paralelo a las anteriores.
- T035..T043 (governance Hermes) **todos [P]** entre si (archivos distintos).

### Phase F1 — Auth removal (secuencial, riesgo medio)

- T046 (test) → T047 (delete file) → T048 (router) → T049 (deps) → T050 (onboarding) → T051 (app.py). Secuencial por dependencia entre archivos.

### Phase F2 — Bloque ingestion + skills

- T058, T061, T062, T063 [P] (ports/utilidades en archivos distintos).
- T066 y T067 [P] (clones independientes).
- T068, T070, T074, T076, T078 [P] (tests de skills marketplace).

### Phase F3a

- T081, T083, T084 [P] entre si (3 tools nuevas independientes).

### Phase F4a

- T091, T093, T095, T097, T099 [P] (tests de orquestacion+modos).
- T101, T102, T103 [P] (3 modos YAML).
- T105, T106 [P] (2 playbooks YAML; technology-watch va aparte por wrapper).
- T114, T116, T117, T118 [P] (4 superficies del frontend).

### Phase Polish

- T138..T151 **todos [P]** (verificaciones independientes); T152, T153, T154, T155 secuenciales al final.

---

## Implementation Strategy

1. **Cerrar Phase 0 primero** (1-2 dias): el audit T001+T002 define el resto del plan. Sin audit no se puede decidir cuantos MCP fallback quedan ni cuantas tools nativas hay que escribir.
2. **F1 en dos tracks paralelos** (3-4 semanas): track A = supervisor + cliente MCP + wrapper fallback (T007..T014); track B = 16 tools nativas (T015..T032). Track A tipicamente queda corto (idealmente 0 fallback); track B es la masa de trabajo. Governance Hermes (T035..T043) en paralelo.
3. **Auth removal (T046..T051)** debe ir tarde en F1, una vez que el resto del wiring funciona, para evitar romper tests intermedios. Hacer commit aislado.
4. **F2 (3-4 semanas)** comienza tras F1; TurboVec nativo + ingestion + skills marketplaces. Eliminar claude-local (T072..T073) tras tener k_dense+agency_agents activos.
5. **F3a (1-2 semanas)** puede solaparse con la cola de F2 (no dependen entre si excepto governance file_safety).
6. **F4a (3-4 semanas)** es la integracion: Mode/Complexity/Playbook + 3 modos + 3 playbooks (con `technology-watch` envolviendo el `BranchCoordinator`) + frontend 4 superficies + onboarding sin login + SubagentRegistry. Es la fase que hace que el MVP sea visible end-to-end.
7. **F5a (1 semana)** es ligera: scheduler de 2 fases + PI defense + audit JSONL + deprecaciones (cabeceras ROADMAP).
8. **Polish (1 semana)** valida los 15 SC con evidencia automatizada y produce `release-notes-021.md`.
9. **Principio quirurgico**: cero modificaciones a `application/execution/branch_coordinator.py`, las 6 ramas, `infra/embeddings/gemini_gateway.py`, `infra/reranking/semantic_reranker.py`, `infra/mcp/mcp-providers.json`. Toda extension es aditiva.
10. **No commit/push sin permiso del usuario** (regla operativa); las verificaciones T152..T155 corren localmente.

---

## Format Validation

Todas las tareas T001..T155 siguen el formato requerido:
- Checkbox `- [ ]` al inicio.
- Task ID secuencial (T001..T155).
- Marcador `[P]` solo en tareas paralelizables (archivos distintos, sin dependencia).
- Descripcion con accion + path concreto del archivo.
- Traza a FR/SC en Independent Test Criteria por fase.

**Total task count**: 155 tareas.
**Task count per phase**:
- Phase 0 (Setup + audit): 6
- Phase F1 (Native-first + supervisor + governance Hermes + remover auth): 46
- Phase F2 (TurboVec native + ingestion + memoria + skills marketplaces + sin claude-local): 28
- Phase F3a (3 tools nuevas + computer use): 10
- Phase F4a (Orquestacion + 3 modos + 3 playbooks + frontend MVP + onboarding + SubagentRegistry): 32
- Phase F5a (Dreaming basico + PI defense + audit + deprecaciones): 15
- Phase Polish (Verificacion SC-001..015 + cierre): 18

**MVP scope**: las 155 tareas cubren el backbone MVP F1-F5a end-to-end con las 5 correcciones del usuario (D1..D5), las 21 tools de agente operativas (16 proveedores native-first + 4 documents + computer_use), las 4 superficies del frontend sin login, el onboarding sin auth, y la deprecacion (no borrado) del codigo de roadmap (goal_pursuit, app_development, artifacts, 9 fases extra + 7 loops de Dreaming, 5 modos roadmap, 4 playbooks roadmap). Cero codigo de produccion para roadmap (YAGNI). Cero modificaciones al 2.0 (cambios quirurgicos).
