# Feature Specification: Backend Optimization & Google Workspace MCP Revert

**Spec ID**: 022
**Status**: Draft
**Created**: 2026-06-01
**Supersedes**: parts of 021 (Google Workspace integration only)
**Depends on**: 009, 011, 015, 018, 021 MVP completed

## Problem Statement

Tras cerrar el MVP de 021, el backend acumula deuda de optimización medible y una desviación arquitectónica concreta:

1. **Hot paths con N+1**: cada llamada a `ToolRegistry.discover()` ejecuta 22 embeddings + 21 round-trips a DB (latencia 2-7s); `SkillRegistry.discover()` hace 312 embeddings (similar costo). Esto compromete UX en cualquier flujo que invoque selección de herramientas.
2. **Cold-start de skills inaceptable**: el `SkillLoader` carga 311 skills (143 K-Dense + 168 agency-agents), embedde cada description en boot y escribe HashTracker por cada skill (311 disk writes seriales). Boot estimado: 30-90 s.
3. **11 providers HTTP duplicados**: cada provider (Tavily, Brave, Exa, Jina, Firecrawl, Serper, Serper Patents, OpenAlex, Arxiv, Fetch, MiniMax Image) crea un `httpx.AsyncClient()` nuevo por llamada, sin connection pooling, sin retry policy unificada, sin error mapping consistente. ≈1537 LOC con ~70% boilerplate idéntico.
4. **`api/dependencies.py` monolítico**: 694 LOC, 10 `_build_*` functions; viola la preferencia constitucional ≤400 LOC y dificulta navegación/testing.
5. **3 servicios duplicados** entre composition roots 2.0 y 3.0: `EmbeddingGateway`, `KnowledgeGraphService`, `ToolHealthRepository`. Memoria duplicada (~6 MB) y comportamiento divergente posible.
6. **Desviación Google Workspace** (crítica): el plan original (ANEXO-B C1.4 vigente, 00b-mvp-scope, 06-catalogo-tools, 018 SC-003) especifica `google-workspace-mcp` (Taylor Wilsdon) como MCP STDIO Tier 2 con ~30+ capabilities (Gmail+Calendar+Drive+Docs+Sheets+Forms+Slides+Chats). La implementación real es un WRAP-SDK Python directo con sólo 4 capabilities (`read_docs`, `write_docs`, `read_sheets`, `send_email`), 174 LOC en `enterprise/tooling/builtin/productivity/google_workspace.py`. Esto reduce la oferta funcional 87% por el mismo costo de configuración OAuth.
7. **SDKs oficiales no aprovechados**: 5 providers tienen SDKs oficiales maduros (`tavily-python`, `exa-py`, `firecrawl-py`, `pyalex`, `arxiv`) que reducirían LOC y manejo de edge cases.
8. **Procesos internos reimplementados**: `fetch.py` (HTML→text custom), `infra/factcheck/{google,wikidata}.py` (HTTP scraping manual) duplican capacidades de paquetes maduros (`markitdown`, `qwikidata`).
9. **Correctness gaps**: `TurboVecIndex.add()` no tiene lock per-tenant → race condition en ingestion concurrente; `MCPSmartCache` no tiene `max_entries` (riesgo OOM en sesiones largas); DB pool no configurable.
10. **501 LOC dead code confirmado** + **30 archivos roadmap** (F5b/F4b/F4c) mezclados con runtime activo, ralentizando CI ~25%.

## Scope Boundaries

### In Scope

**Performance (mandatorio)**
- Pre-cómputo de embeddings de tool/skill descriptions en `register()`, persistidos en `~/.vigilador/cache/embeddings/`.
- Batch SQL para `_get_status()` de tool health (1 query vs N).
- Numpy para cosine similarity vectorizado.
- Gemini `batchEmbedContents` real (1 request por batch de 100).
- LRU cache en embedding gateway.
- DB pool 10 + overflow 20, configurable vía env.
- `MCPSmartCache.max_entries` configurable, TTL por env var.
- Skills boot optimization: frontmatter-only read en adapters, `HashTracker.save_all()` batch.
- Movimiento de skills non-MVP a `_cold/` (8 clínicas: clinical-decision-support, clinical-reports, treatment-plans, biomarker-classifier, neuropixels-analysis, pacsomatic, pydicom, scvelo).

**Provider migration (mandatorio)**
- **Google Workspace**: revert a MCP-EXTERNO. Eliminar `enterprise/tooling/builtin/productivity/google_workspace.py`. Declarar `google-workspace-mcp` (taylorwilsdon) en `config/mcp/external.yaml`. Actualizar `catalog.yaml` (`strategy: MCP-EXTERNO`, `runtime: stdio_external`, capabilities expandidas). Wirear vía `McpToolWrapper` + `MCPProcessSupervisor`.
- **SDK oficial migration** (5 providers): Tavily → `tavily-python`, Exa → `exa-py`, Firecrawl → `firecrawl-py`, OpenAlex → `pyalex`, Arxiv → `arxiv`.
- **BaseHTTPProvider** para los 6 restantes (Brave, Serper, Serper Patents, Jina, Fetch, MiniMax Image): connection pooling, retry policy 3-exponential sobre 5xx+ConnectError, error mapping unificado, healthcheck default.
- **Wire close()** en FastAPI lifespan para todos los HTTP clients (graceful shutdown).

**Composition root (mandatorio)**
- Split `api/dependencies.py` (694 LOC) en paquete `api/dependencies/` con 10 submodules (uno por workstream/función). `__init__.py` re-exporta toda la API pública: zero breaking changes para los 12 importadores externos actuales.
- Singleton dedup: `@lru_cache` en factories de `EmbeddingGateway`, `KnowledgeGraphService`, `ToolHealthRepository`. Pasar instancias compartidas entre 2.0 y 3.0 composition.
- Lazy imports de WS factories en lifespan para reducir boot time si workstreams están deshabilitados.

**Correctness fixes (mandatorio)**
- `TurboVecIndex._write_lock` per-tenant `asyncio.Lock` (separado de persist_lock para evitar deadlock).
- `AuditLog` y `PIQuarantineWriter`: flush sincrónico por evento (decisión usuario E-05: NO buffer, NO pérdida en crash).

**Cleanup (mandatorio)**
- Eliminar 501 LOC dead code confirmado: `infra/mcp/playwright_mcp.py`, `infra/mcp/minimax_image_mcp.py`, `enterprise/skills_marketplace/claude_local_adapter.py`.
- Aislar paquetes roadmap en `_roadmap/`:
  - `enterprise/_roadmap/artifacts/` (9 archivos F5b)
  - `enterprise/orchestration/_roadmap/app_development/` (11 archivos F4b)
  - `enterprise/orchestration/_roadmap/goal_pursuit/` (7 archivos F4b)
  - `enterprise/dreaming/_roadmap_loops/` (7 archivos F5b)
  - `enterprise/dreaming/phases/_roadmap/` (8 phases F5b, preservar `memory_consolidation` + `ingestion_sync`)
  - Tests correspondientes (~30 archivos) a `tests/.../_roadmap/`.
- `pytest.ini`: excluir `_roadmap/` de la suite por defecto; mantener invocable explícitamente.
- `scripts/check-layer-imports.py`: ignorar `_roadmap/`.

**Audit ampliado a procesos internos (opcional, fase 2)**
- Evaluar reemplazo de `application/agents/builtin/web/fetch.py` por `markitdown` + `httpx`.
- Evaluar reemplazo de `infra/factcheck/google_factcheck.py` por `google-api-python-client` (compartido con Workspace MCP).
- Evaluar reemplazo de `infra/factcheck/wikidata_factcheck.py` por `qwikidata`.

### Out of Scope

- **2.0 preservado**: `application/execution/branch_coordinator.py`, los 6 agentes de rama, `application/evaluation/ws_a..ws_e/`, `/api/v2/research/*`. Wrappers se mantienen vía `plugins/technology-watch/coordinator_wrapper.py`.
- **F4b roadmap**: decision-debate playbook, goal_pursuit ejecutor real, app-development pipeline, artifact-development.
- **F4c roadmap**: 5 modos diferidos (cfo, consultor-legal, marketing, operaciones-pyme, vendedor-b2b).
- **F5b roadmap**: 8 dreaming phases extra + 7 loops + agent_modifier SQL + anomaly detector.
- **D4 user auth**: ya removido en 021 F1.I.
- **Frontend refactor profundo**: solo se ajustan rutas/wiring si afectan backend.
- **Nuevas features**: este spec es exclusivamente optimización + revert + cleanup.
- **MiniMax LLM client** (`infra/llm/minimax_client.py`): es 2.0 legacy, no se toca.
- **Hermes governance ports**: spec 021 F1.G ya cerró lo que aplicaba a MVP.

## Assumptions

- **A-01 (E-01 ampliada)**: SDK oficial preferido sobre `BaseHTTPProvider` cuando el SDK es maduro (≥1 año en PyPI, releases regulares, mantenido por el provider o community con tracción). Para providers sin SDK aceptable, `BaseHTTPProvider`.
- **A-02 (E-02)**: TTL del MCP cache vía env vars `VT_MCP_CACHE_TTL_SHORT=1800` (30 min) y `VT_MCP_CACHE_TTL_LONG=604800` (7 días); defaults preservan comportamiento actual.
- **A-03 (E-03)**: 8 skills clínicas se mueven a `_vendor/_cold/k_dense/`; el resto de los 311 skills permanecen activos por default.
- **A-04 (E-04)**: Path de embedding cache: `~/.vigilador/cache/embeddings/{tools.json,skills.json}` con HMAC del content-hash.
- **A-05 (E-05)**: AuditLog y PIQuarantineWriter siguen sincrónicos (NO buffer); cada evento flush a disco antes del return.
- **A-06 (E-06)**: DB pool size 10, max_overflow 20. Configurables vía `VT_DB_POOL_SIZE` y `VT_DB_POOL_OVERFLOW`.
- **A-07 (E-07)**: `GeminiEmbeddingGateway.embed_documents()` migra a `batchEmbedContents` con batches de 100 (límite API Gemini). Single `embed()` mantiene shape actual.
- **A-08 (E-08)**: Olas secuenciales 1→2→3→4→5→6 (NO paralelas, evita merge conflicts).
- **A-09 (E-09)**: `numpy` (≥1.26) añadido a `pyproject.toml` como dependencia obligatoria.
- **A-10**: Google Workspace MCP requiere `GOOGLE_CLIENT_ID` + `GOOGLE_CLIENT_SECRET` (mismos env vars que el WRAP-SDK actual ya usa). El usuario pre-existente de la deviation no necesita re-configurar credenciales en Google Cloud.
- **A-11**: Tests baseline NUNCA deben romperse (gate sagrado): `application/execution/`, `application/evaluation/`, `/api/v2/research/*`, `enterprise/governance/test_audit_log*`, `enterprise/orchestration/test_dispatcher`. Pre-existing 580 passed se mantiene.
- **A-12**: `_roadmap/` paths siguen siendo importables explícitamente (no son borrados); solo se excluyen de pytest default y de check-layer-imports.
- **A-13**: Python 3.11+ asumido (ya en uso).
- **A-14**: Bun/npm para frontend siguen sin cambios; backend optimization no toca frontend.

## prompts/ — Audit y Reforma (NUEVO scope)

**Path**: `src/vigilancia_multiagente/prompts/` (51 archivos `.txt` en 5 subdirectorios)

**Estado actual** (verificado por grep en runtime):

| Subdir | Files | Consumidores reales | Decisión |
|---|---:|---|---|
| `branches/` | 6 | `application/governance/contract_loader.py:619` (los 6 agentes 2.0: avances, comercial, competitivo, oportunidades, pi_normativa, riesgo) | **2.0 ACTIVO — NO TOCAR** |
| `evaluation/` | 24 | `application/evaluation/ws_*/llm_*.py` + `api/routes/config_prompts.py:39` + `config/prompt_overrides.py:88` (8 templates × 3 ejemplos: assumption_detection, counterfactual, falsification, query_expand, stakeholder_{academic,competitor,investor,regulator}) | **2.0 ACTIVO — NO TOCAR** |
| `orchestration/` | 3 | `clarification_service.py:28` (clarify), `plan_builder.py:49` (planning), `report_synthesizer.py:179` (synthesis) | **2.0 ACTIVO — NO TOCAR** |
| `minimax_examples/` | 4 | `infra/llm/minimax_client.py:95-98` (MiniMax LLM legacy — Xiaomimimo es default MVP por D5) | **DELETE completo** (FR-033) — MiniMax LLM client se elimina como deuda técnica |
| `tools/` | 14 | **0 callers verificados** PERO contenido es **system-prompt rico** que enseña al LLM cómo seleccionar/usar cada tool (function_signature, best_for, selection_heuristics, chaining, fallback) | **PRESERVAR + WIREAR** (FR-034 nueva) — bug preexistente: el ToolRegistry expone `long_description` pero no carga estos archivos. Solución: wirear `get_docs(name)` para leerlos. |

**Hallazgo crítico (deuda técnica preexistente)**: `grep "description:|examples:|long_description"` sobre `enterprise/tooling/builtin/` retorna **0 matches**. Los provider tools concretos NO setean `description`/`examples`/`long_description`, solo `name` y `domain`. El LLM al hacer `discover()` ve únicamente `name` + `domain` + (si setteado) `≤80 chars description`. **`prompts/tools/*.txt` son la fuente correcta de la rich docs pero nunca fueron wireados** al runtime.

**FR-033 (REVISADA)**: El sistema **MUST** eliminar `infra/llm/minimax_client.py` (146 LOC), `prompts/minimax_examples/` (4 archivos), y `tests/test_minimax_client.py`. MiniMax LLM client se considera deuda técnica legacy (Xiaomimimo es default MVP por D5; MiniMax no aporta valor adicional). **`MiniMaxImageTool`** (image generation, builtin tool en `enterprise/tooling/builtin/creative/`) se preserva — es producto distinto.

**FR-034 (NUEVA)**: El sistema **MUST** wirear `ToolRegistry.get_docs(name) -> ToolDocs` para que `long_description` cargue automáticamente desde `src/vigilancia_multiagente/prompts/tools/<name>.txt` cuando exista. Si el archivo no existe, `long_description=""` (no error). El loader debe usar `infra/prompts/loader.py:load_prompt(f"tools/{name}")` con cache LRU.

**FR-035 (NUEVA)**: El sistema **MUST** actualizar `prompts/tools/<name>.txt` para los 11 providers refactorizados en Ola 4 (5 SDK + 6 BaseHTTPProvider) reflejando las signaturas nuevas. Crear `prompts/tools/google-workspace-mcp.txt` con las 25+ capabilities del MCP revert.

**FR-036 (NUEVA, antes FR-035)**: El sistema **MUST** preservar `prompts/branches/`, `prompts/evaluation/`, `prompts/orchestration/` sin cambios — son consumidos por 2.0 preservado.

**Net delta prompts/**:
- Eliminados: `minimax_examples/` (4) + `infra/llm/minimax_client.py` (146 LOC) + test = **5 archivos eliminados**
- Wireados (no eliminados): 14 archivos `tools/*.txt` se conservan + se cargan vía `get_docs()`
- Nuevos: 1 archivo `google-workspace-mcp.txt` + actualizaciones a los 14 existentes durante Ola 4
- Preservados sin cambio: 33 archivos en `branches/`, `evaluation/`, `orchestration/`

## Skills — Inventario detallado a archivar (NUEVO scope, reemplaza E-03 reducida)

La decisión E-03 inicial mencionaba "8 clínicas". Tras audit completo de los 143 skills K-Dense + 19 divisiones agency_agents (168 files), la lista correcta para `_cold/` es **mucho más amplia**:

### K-Dense → `_vendor/_cold/k_dense/skills/` (~62 skills científicas no-MVP)

**Bio/molecular/genetics (40)**:
- adaptyv, anndata, biopython, bioservices, bulk-rnaseq, cellxgene-census, cobrapy, datamol, deepchem, deeptools, depmap, dhdna-profiler, diffdock, dnanexus-integration, esm, geniml, gget, ginkgo-cloud-lab, glycoengineering, gtars, histolab, imaging-data-commons, labarchive-integration, lamindb, latchbio-integration, matchms, molfeat, molecular-dynamics, neurokit2, neuropixels-analysis, omero-integration, opentrons-integration, pathml, pathway-enrichment, primekg, protocolsio-integration, pydeseq2, pylabrobot, pyopenms, pysam, pytdc, scvelo, scvi-tools, tiledbvcf, torchdrug

**Clinical (5)**:
- clinical-decision-support, clinical-reports, treatment-plans, pacsomatic, pydicom

**Quantum/physics niche (5)**:
- cirq, pennylane, qiskit, qutip, fluidsim

**Bio-adjacent ML (sin uso B2B Colombia tech surveillance) (10)**:
- pyhealth, scikit-bio, scikit-survival, scanpy, geomaster, geopandas, fluidsim, dhdna-profiler, glycoengineering, optimize-for-gpu

**Astrophysics (1)**:
- astropy

**Astrofísica/genómica niche (1)**:
- aeon

**NOTA**: `consciousness-council` SE PRESERVA en activo (NO se mueve a `_cold/`). Razón: es la base del modo `decision-debate` F4b roadmap (CrewAI debate orchestration).

### agency_agents → `_vendor/_cold/agency_agents/` (~69 files non-B2B/non-Colombia)

**game-development (división completa, ~50 files)**:
- 5 subdirectorios + 20 archivos top-level

**spatial-computing (división completa, 6 files)**:
- arcraft-developer, meta-quest-developer, mobile-ar-developer, unity-vr-developer, unreal-engine-developer, webxr-developer

**specialized (audit individual — 13 de 41 files no-MVP movidos a `_cold/specialized/`)**:
- `specialized-civil-engineer.md` (no aplica B2B tech)
- `specialized-french-consulting-market.md`, `specialized-korean-business-navigator.md` (foco Colombia ≠ Francia/Corea)
- `study-abroad-advisor.md`, `zk-steward.md` (niche crypto), `real-estate-buyer-seller.md` (no MVP)
- `lsp-index-engineer.md` (super niche dev tooling)
- `healthcare-customer-service.md`, `healthcare-marketing-compliance.md` (sector específico)
- `hospitality-guest-services.md`, `retail-customer-returns.md` (industrias específicas)
- `loan-officer-assistant.md` (banca específica), `identity-graph-operator.md` (niche identity graph)

**Total a `_cold/`**: ~62 K-Dense + ~50 game-development + 6 spatial-computing + 13 specialized = **~131 directorios/archivos** (vs 8 originales).

### Skills MVP-relevant que SE PRESERVAN (~245 skills)

**K-Dense (~80 skills relevantes para tecnología surveillance B2B)**:
- Documents/reports: docx, pdf, pptx, pptx-posters, latex-posters, markdown-mermaid-writing, markitdown, infographics, scientific-slides, scientific-visualization, scientific-writing, venue-templates, scientific-schematics
- Literature/citations: citation-management, literature-review, paper-lookup, paperzilla, peer-review, scholar-evaluation, scientific-brainstorming, scientific-critical-thinking, hypothesis-generation, hypogenic, research-grants, research-lookup, what-if-oracle, market-research-reports, exa-search, bgpt-paper-search
- Generic ML/data (utilizable en análisis): autoskill, dask, modal, networkx, polars, polars-bio, pymc, pymoo, pufferlib, rdkit, scikit-learn, seaborn, shap, simpy, stable-baselines3, statistical-analysis, statsmodels, timesfm-forecasting, torch-geometric, transformers, umap-learn, vaex, xlsx, zarr-python, hugging-science, matplotlib, matlab, parallel-web
- Utilities: iso-13485-certification, database-lookup, get-available-resources, liteparse, generate-image, pdf, consciousness-council, scientific-critical-thinking, hypothesis-generation

**agency_agents (~167 archivos relevantes)**:
- engineering (29): backend, frontend, mobile, embedded, devops, sre, security, blockchain — TODO MVP
- strategy (16): trend analysis, competitive intelligence — TODO MVP
- marketing (30): SEO, content, lifecycle, social — TODO MVP
- specialized (28 de 41 archivos audit-positive): AI/governance, business automation, legal, compliance, HR, sales/strategy, executive support, engineering/QA, B2G Colombia, utilidades genéricas
- finance (5), product (5), sales (8), project-management (6), academic (5), support (6), testing (8), design (8): TODO MVP
- integrations (15 con 12 subdirs): MCP/API integrations — preservar
- examples, scripts, .github: estructura, NO son skills — preservar como están

**FR-037** (NUEVO, reemplaza FR-025/FR-036): El sistema **MUST** mover los siguientes paths bajo `_vendor/_cold/`:
- 62 K-Dense skill directorios (lista exhaustiva en `data-model.md`, NO incluye `consciousness-council` que se preserva para F4b)
- `agency_agents/game-development/` (división completa, ~50 archivos)
- `agency_agents/spatial-computing/` (división completa, 6 archivos)
- 13 archivos individuales de `agency_agents/specialized/` (lista exhaustiva en `data-model.md`)
**Total**: ~131 directorios/archivos. SkillCatalog filtra paths bajo `_cold/`. Activación opcional via `VT_COLD_SKILLS_ENABLED=1`.

## User Scenarios & Testing

### Primary User Story

Como **operador del sistema en producción**, quiero que el cold-start del backend baje de 30-90 s a <5 s, que la latencia de discovery de tools/skills sea <200 ms, y que un tenant que conecta Google Workspace obtenga acceso a Gmail+Calendar+Drive+Docs+Sheets+Forms en una sola configuración OAuth, en lugar de los 4 endpoints reducidos actuales.

### Acceptance Scenarios

1. **Given** una instancia recién bootada del backend con `enterprise_enabled=true`, **When** se mide tiempo desde `lifespan.startup` hasta `app.state.ready=True`, **Then** el tiempo es <5 s en hardware estándar (vs 30-90 s actual).
2. **Given** un agente ejecuta `ToolRegistry.discover(intent="benchmarks RAG", role="researcher", tenant_id=X)`, **When** se mide latencia p95 sobre 100 invocaciones consecutivas, **Then** la latencia p95 es <200 ms (vs 2-7 s actual).
3. **Given** un tenant completa onboarding y autoriza OAuth en Google Workspace, **When** lista capabilities bajo el dominio `productivity`, **Then** ve al menos 25 capabilities (Gmail send/read/search/labels, Calendar events/availability, Drive browse/files, Docs full edit, Sheets read/write, Forms create/responses) — NO solo 4.
4. **Given** Tavily devuelve un 503 transitorio en una búsqueda, **When** el provider ejecuta retry policy, **Then** retorna éxito en el segundo intento sin propagar error al agente y sin alertar al usuario.
5. **Given** 5 connectors ejecutan ingestion concurrentemente para el mismo tenant, **When** todos completan, **Then** el TurboVec index del tenant tiene 0 chunks corruptos o duplicados por race condition.
6. **Given** un agente invoca cualquier tool y el proceso del backend recibe SIGKILL inmediatamente después del return, **When** se inspecciona `~/.vigilador/audit/events_<fecha>.jsonl`, **Then** el evento `tool_invocation` correspondiente está presente (flush sincrónico).
7. **Given** un developer ejecuta `pytest tests/ -q` en clean checkout, **When** termina la suite, **Then** el tiempo es ≤30 s (vs ~40 s actual) y exit code 0.
8. **Given** un developer importa `from vigilancia_multiagente.api.dependencies import build_orchestration_services` post-split, **When** Python resuelve el import, **Then** funciona idénticamente al estado pre-split (re-exports preservan API pública).
9. **Given** un developer corre `find src/vigilancia_multiagente -maxdepth 6 -name '*.py' \| xargs wc -l \| awk '$1>400'`, **When** revisa el output, **Then** ningún archivo runtime excede 400 LOC (excepto los 2 ya documentados con justificación de cohesión: `dependencies.py` deja de existir; los pre-existentes no tocados se mantienen marcados).
10. **Given** el pool de DB está al 80% de utilización en una sesión de research pesada, **When** llega una request adicional, **Then** se procesa sin bloqueo (pool overflow disponible) en lugar de timeout.

### Edge Cases

- **EC-01**: Si `~/.vigilador/cache/embeddings/tools.json` está corrupto, el sistema regenera el cache desde cero en el siguiente boot sin abortar. Se loguea WARNING.
- **EC-02**: Si el SDK oficial migrado (ej. `tavily-python`) no está instalado pero la tool está habilitada, healthcheck retorna `UNCONFIGURED` con error explicit "SDK no instalado".
- **EC-03**: Si `google-workspace-mcp` (Node.js) no está disponible (npm uninstalled), el supervisor MCP loguea fallo, marca el provider DOWN, y el ToolRegistry no expone las capabilities. NO crashea el backend.
- **EC-04**: Si la API de Gemini no soporta `batchEmbedContents` (cambio de versión), el adapter cae a `embed()` por loop con WARNING + telemetría.
- **EC-05**: Si numpy no está instalado, el cosine similarity cae a pure-Python con WARNING en boot. Sistema funciona idénticamente.
- **EC-06**: Si un skill movido a `_cold/` es llamado explícitamente por nombre, falla con error claro "skill in cold storage; activate via config" en lugar de cargarlo silenciosamente.
- **EC-07**: Si dos requests concurrentes hacen `register()` de la misma tool, la segunda lanza `ValueError` (comportamiento actual preservado).
- **EC-08**: Si el TurboVec lock per-tenant lleva >30 s esperando, se aborta con error específico para que el caller decida (NO deadlock silencioso).

## Functional Requirements

### Performance

- **FR-001**: El sistema **MUST** pre-computar embeddings de tool descriptions en `ToolRegistry.register()` y cachearlos en disco; subsiguientes calls a `discover()` reusan el cache sin re-embedding mientras el content-hash de la description no cambie.
- **FR-002**: El sistema **MUST** ejecutar `_get_status()` para todas las tools registradas en una única query SQL (batch) por invocación de `discover()`.
- **FR-003**: El sistema **MUST** pre-computar embeddings de skill descriptions en boot y persistirlos en `~/.vigilador/cache/embeddings/skills.json`; en boots subsiguientes lee el cache si el HashTracker confirma que ningún skill cambió.
- **FR-004**: El sistema **MUST** usar `numpy` para cosine similarity vectorizado en `_cosine_similarity` cuando esté disponible; fallback a pure-Python si numpy no instalado.
- **FR-005**: El sistema **MUST** invocar Gemini `batchEmbedContents` cuando se llame `embed_documents(texts)` con `len(texts) > 1`; batch máximo 100 por request.
- **FR-006**: El sistema **MUST** mantener un LRU cache en `GeminiEmbeddingGateway.embed()` con tamaño máximo 1000 entries, key=hash del texto.
- **FR-007**: El sistema **MUST** configurar el pool SQLAlchemy con `pool_size=10, max_overflow=20` por defecto, ambos overridables vía `VT_DB_POOL_SIZE` y `VT_DB_POOL_OVERFLOW`.
- **FR-008**: El `MCPSmartCache` **MUST** implementar eviction LRU con `max_entries=1000` por defecto, configurable vía `VT_MCP_CACHE_MAX_ENTRIES`. TTL configurable vía `VT_MCP_CACHE_TTL_SHORT` (default 1800) y `VT_MCP_CACHE_TTL_LONG` (default 604800).

### Provider migration

- **FR-009**: El sistema **MUST** declarar `google-workspace-mcp` (`taylorwilsdon/google_workspace_mcp` versión pinneada) en `config/mcp/external.yaml` con healthcheck cada 60 s, restart policy on-failure, log JSONL en `~/.vigilador/mcp-logs/google-workspace.jsonl`.
- **FR-010**: El sistema **MUST** eliminar `src/vigilancia_multiagente/enterprise/tooling/builtin/productivity/google_workspace.py` y todas sus referencias en `enterprise_composition.py`, tests, y catalog.
- **FR-011**: El sistema **MUST** actualizar `config/tools/catalog.yaml` para `google_workspace`: `strategy: MCP-EXTERNO`, `runtime: stdio_external`, capabilities expandidas a las 25+ que expone el MCP upstream (Gmail send/read/search/labels/drafts, Calendar events/availability, Drive browse/files/shared, Docs read/write/insert/format, Sheets read/write/append, Forms create/responses).
- **FR-012**: El sistema **MUST** migrar `Tavily`, `Exa`, `Firecrawl`, `OpenAlex`, `Arxiv` a sus SDKs oficiales respectivos (`tavily-python`, `exa-py`, `firecrawl-py`, `pyalex`, `arxiv`).
- **FR-013**: El sistema **MUST** introducir `BaseHTTPProvider` (≤200 LOC) con connection pooling vía `httpx.AsyncClient` singleton (max_connections=100, max_keepalive=20), retry policy `(3, exponential_backoff [1s,2s,4s], retry_on=[503,502,504,ConnectError,ReadTimeout])`, error mapping unificado, healthcheck default basado en api_key gating.
- **FR-014**: El sistema **MUST** refactorizar `Brave`, `Serper`, `Serper Patents`, `Jina`, `Fetch`, `MiniMax Image` para heredar de `BaseHTTPProvider`. Cada subclase ≤80 LOC.
- **FR-015**: El sistema **MUST** wirear `BaseHTTPProvider.aclose()` y todos los SDK clients en FastAPI `lifespan.shutdown` para graceful close.

### Composition root

- **FR-016**: El sistema **MUST** dividir `api/dependencies.py` (694 LOC) en un paquete `api/dependencies/` con un submodule por `_build_*` function (10 archivos) + `__init__.py` con re-exports. Cada submodule ≤100 LOC. La API pública (símbolos importables) se preserva 100%.
- **FR-017**: El sistema **MUST** singleton-izar `EmbeddingGateway`, `KnowledgeGraphService`, `ToolHealthRepository` vía factories `@lru_cache` en `api/dependencies/_singletons.py`. Tanto 2.0 (`api/dependencies/`) como 3.0 (`api/enterprise_composition.py`) consumen las mismas instancias.
- **FR-018**: El sistema **MUST** mover los imports de WS-specific modules (`ws_a..ws_e`) a lazy imports dentro de los `_build_*_services()` que los usan, para reducir boot time si su feature flag está deshabilitada.

### Correctness

- **FR-019**: El sistema **MUST** proteger `TurboVecIndex.add()` con `asyncio.Lock` per-tenant (key = `tenant_id`), separado del lock de `persist()` para evitar deadlock.
- **FR-020**: El `AuditLog` **MUST** flush sincrónicamente cada evento (tool_invocation, llm_call, complexity, subagent_spawn) a `~/.vigilador/audit/events_<fecha>.jsonl` antes de retornar.
- **FR-021**: El `PIQuarantineJSONLWriter` **MUST** flush sincrónicamente cada evento a `~/.vigilador/audit/pi_quarantine_<fecha>.jsonl` antes de retornar.

### Cleanup

- **FR-022**: El sistema **MUST** eliminar los siguientes archivos confirmados como dead code: `src/vigilancia_multiagente/infra/mcp/playwright_mcp.py`, `src/vigilancia_multiagente/infra/mcp/minimax_image_mcp.py`, `src/vigilancia_multiagente/enterprise/skills_marketplace/claude_local_adapter.py`.
- **FR-023**: El sistema **MUST** mover los siguientes paquetes a paths `_roadmap/` (no eliminados, solo aislados):
  - `enterprise/artifacts/` (9 archivos) → `enterprise/_roadmap/artifacts/`
  - `enterprise/orchestration/app_development/` (11 archivos) → `enterprise/orchestration/_roadmap/app_development/`
  - `enterprise/orchestration/goal_pursuit/` (7 archivos) → `enterprise/orchestration/_roadmap/goal_pursuit/`
  - `enterprise/dreaming/loops/` (7 archivos) → `enterprise/dreaming/_roadmap_loops/`
  - 8 phases F5b en `enterprise/dreaming/phases/` → `enterprise/dreaming/phases/_roadmap/` (preservar `memory_consolidation.py` e `ingestion_sync.py` activos).
- **FR-024**: El sistema **MUST** mover los tests correspondientes a paths espejo `tests/.../_roadmap/` y configurar `pytest.ini` para excluirlos del run default. Deben seguir invocables explícitamente vía `pytest tests/.../_roadmap/`.
- **FR-025**: El sistema **MUST** mover 8 skills clínicas non-MVP de `_vendor/k_dense/skills/` a `_vendor/_cold/k_dense/skills/`: clinical-decision-support, clinical-reports, treatment-plans, biomarker-classifier, neuropixels-analysis, pacsomatic, pydicom, scvelo. SkillCatalog ignora paths bajo `_cold/`.
- **FR-026**: El sistema **MUST** actualizar `scripts/check-layer-imports.py` para ignorar `_roadmap/` y `_cold/` paths.

### Backwards compatibility

- **FR-027**: El sistema **MUST** preservar 100% la suite de tests 2.0 (`tests/application/`, `tests/api/routes/test_research_*`) verde sin modificaciones.
- **FR-028**: El sistema **MUST** preservar 100% la suite gate sagrada: `tests/test_orchestrator.py`, `tests/application/execution/`, `tests/application/evaluation/`, `tests/enterprise/governance/test_audit_log*.py`, `tests/enterprise/orchestration/test_dispatcher.py`.
- **FR-029**: El sistema **MUST** preservar `application/execution/branch_coordinator.py` y los 6 agentes de rama sin modificación (`git diff --stat` sobre estos archivos retorna 0 cambios).
- **FR-030**: El sistema **MUST** preservar la API pública del paquete `api.dependencies` post-split (todos los imports `from vigilancia_multiagente.api.dependencies import X` siguen funcionando).

### Audit & observability

- **FR-031**: El sistema **MUST** loguear cada migración a SDK en `docs/release-notes-022.md` con: provider, SDK destino, versión pinneada, LOC delta, tests afectados.
- **FR-032**: El sistema **MUST** generar `docs/optimization/synthesis_plan_v1.md` (ya existe) y mantenerlo como SSOT del trabajo de este spec; cualquier desviación en implementación se documenta como ADR adicional en `docs/optimization/adr-*.md`.

## Key Entities

- **BaseHTTPProvider**: clase base abstracta para providers HTTP sin SDK oficial. Encapsula connection pool, retry policy, healthcheck. Subclases implementan `execute(name, args)` y opcionalmente `_auth_headers()` cuando el patrón de auth difiere.
- **EmbeddingCache**: caché LRU + disk-cache para embeddings de tool/skill descriptions. Key = SHA-256 del content. Path `~/.vigilador/cache/embeddings/`.
- **MCPProcessSupervisor + McpToolWrapper**: stack existente que se reactiva para Google Workspace MCP. El supervisor levanta el proceso STDIO; el wrapper expone capabilities como `Tool`s en el `ToolRegistry`.
- **`_roadmap/` path convention**: convención de nomenclatura para paquetes que están en árbol pero NO en runtime activo. Excluidos de pytest default, layer-imports check, y composition roots.
- **`_cold/` path convention**: convención para skills cargados solo on-demand explícito. SkillCatalog los lista pero no los embedde en boot.
- **`api/dependencies/` package**: post-split del monolito 694 LOC. Cada submodule construye un workstream específico de servicios 2.0. `__init__.py` re-exporta para preservar API.

## Success Criteria

- **SC-001**: El cold-start del backend (medido desde `app.startup` hasta `app.state.ready=True`) baja de ~30-90 s a **<5 s** en hardware estándar (Intel i7 / 16 GB RAM, Windows 11), medible con `python -c "import time; t=time.perf_counter(); from vigilancia_multiagente.api.app import create_app; create_app(); print(time.perf_counter()-t)"`.
- **SC-002**: La latencia p95 de `ToolRegistry.discover()` baja de 2-7 s a **<200 ms**, medida sobre 100 invocaciones consecutivas con intent fijo en sesión warm.
- **SC-003**: La latencia p95 de `SkillRegistry.discover()` baja a **<300 ms** (margen mayor por 311 skills vs 21 tools), medida análogamente.
- **SC-004**: Un tenant que completa onboarding Google Workspace ve **≥25 capabilities** activas en el dominio `productivity` (vs 4 actuales). Verificable vía `curl /api/v2/enterprise/tools?domain=productivity` post-OAuth.
- **SC-005**: Tras 100 ejecuciones de Tavily con 30% de respuestas 503 inyectadas (mock), la tasa de éxito del agente ≥99% (retry absorbe los 503).
- **SC-006**: Tras 5 ingestion runs concurrentes para el mismo tenant con 1000 docs cada uno, la cuenta de chunks en TurboVec index = exactamente 5000 (sin duplicados ni faltantes).
- **SC-007**: Tras un SIGKILL del backend post-execución de 100 tools en sesión, el archivo `~/.vigilador/audit/events_<fecha>.jsonl` contiene exactamente 100 entries `tool_invocation` (flush sincrónico verificable).
- **SC-008**: La suite de tests `pytest tests/` (excluyendo `_roadmap/`) pasa en **<30 s** (vs ~40 s actual), con 0 regresiones (≥580 passed, 0 failed).
- **SC-009**: `find src/vigilancia_multiagente -maxdepth 8 -name '*.py' \| xargs wc -l \| awk '$1>400 {print}' \| wc -l` retorna 0 (ningún archivo nuevo o modificado por este spec excede 400 LOC).
- **SC-010**: `git diff --stat application/execution/branch_coordinator.py application/evaluation/ws_*` retorna 0 líneas modificadas tras completar todo el spec.
- **SC-011**: El total de LOC en src/ baja al menos **5%** combinando dead-code removal + provider consolidation, verificable con `tokei src/ tests/` antes/después.
- **SC-012**: El `scripts/check-layer-imports.py` retorna 0 violaciones tras todos los cambios.
- **SC-013**: 11 providers HTTP refactorizados (5 a SDK oficial, 6 a BaseHTTPProvider) tienen tests verdes individuales y pasan un nuevo `test_provider_contract.py` que verifica el `ToolWrapper` Protocol contract.
- **SC-014**: La cuenta total de capabilities expuestas por el `ToolRegistry` post-Google-Workspace-revert es **≥45** (21 actuales + ~25 nuevas del MCP).
- **SC-015**: La memoria RSS post-boot baja al menos **3 MB** por dedup de los 3 servicios duplicados, medible con `psutil.Process().memory_info().rss`.

## Delivery Constraints

### Constitución v1.2.0 (sagrada)

- **C-1 SRP**: cada módulo nuevo o modificado tiene una sola razón de cambio.
- **C-2 ≤400 LOC/file**: preferencia. Excepciones requieren justificación de cohesión documentada en docstring del módulo. Este spec elimina ≥2 violaciones existentes (`dependencies.py`, `domain/evaluation_entities.py`).
- **C-3 Explicit errors**: ningún `try/except: pass`. Errores se mapean a tipos específicos de cada subsistema.
- **C-4 CQS**: comandos retornan estado / valor explícito; queries son puras.
- **C-5 DIP**: dependencias siempre por Protocol. Tests inyectan fakes; producción inyecta concretos.
- **C-6 KISS/YAGNI**: ninguna abstracción especulativa; SDK migration solo donde el SDK es maduro.
- **C-7 #5 Cambios quirúrgicos**: NO `ruff check --fix` sobre directorios completos; solo archivos enumerados explícitamente. Reverts via `git checkout` ante collateral.

### Spec 021 D1-D5 (preservadas)

- **D1**: `TurboVecIndex` único 3.0; no pgvector fallback. Este spec añade lock per-tenant; no toca el contract.
- **D2**: `_vendor/{k_dense,agency_agents}/` mantienen su path. Este spec añade `_cold/` como subpath; **no** mueve _vendor fuera de src.
- **D3**: NO `.claude/skills` runtime. Este spec elimina `claude_local_adapter.py` (residual).
- **D4**: NO user auth. `oauth_manager` mantiene service connectors; Google Workspace MCP usa OAuth de servicio igual que el WRAP-SDK actual.
- **D5**: native-first reafirmada. SDK oficial > BaseHTTPProvider > MCP-EXTERNO. Google Workspace **vuelve** a MCP-EXTERNO porque su SDK oficial (Google's) ya está empaquetado dentro del MCP upstream y exponer 30+ capabilities directamente requeriría reimplementar todo el MCP (anti-YAGNI).

### MVP scope (C1) preservado

- 20 capabilities (4 dominios: search/web/research/documents). Este spec **expande** capabilities en `productivity` (Google Workspace MCP), pero `productivity` sigue siendo dominio diferido del MVP catalog (consistente con 00b-mvp-scope línea 167: "🟡 MCPs activos sin tools nuevas").
- 3 modos (default, vigilancia-tech, CEO).
- 3 playbooks (technology-watch, deep-research, general).

### Operational

- **O-01**: Cada ola se commitea solo si el usuario lo solicita explícitamente (política sesión actual: NO commits/pushes).
- **O-02**: Cada ola tiene plan de rollback granular (revert por archivo o por commit).
- **O-03**: Cada ola termina con suite verde antes de iniciar siguiente.
- **O-04**: La ola Google Workspace MCP (FR-009..FR-011) requiere validación manual del MCP upstream (npm install + smoke test del binary) antes de declararla en `external.yaml`. La operación de install del MCP queda fuera de este spec (es ops, no código).
- **O-05**: `numpy` se añade a `pyproject.toml` como dependency obligatoria; el cambio se valida con `pip install -e .` en clean env.

### Risks (resumen ejecutivo)

- **R-bajo**: dead-code removal, `_roadmap/` move (todos los archivos cubiertos por tests; reverts son `git checkout`).
- **R-medio**: provider migration (5 SDKs + 6 BaseHTTPProvider). Mitigación: incremental por provider, golden-output tests, respx mocks.
- **R-medio**: Google Workspace MCP revert. Mitigación: migration test que valida onboarding flow + capabilities exposed; rollback completo es revert de 1 commit.
- **R-medio**: TurboVec lock. Mitigación: lock granular separado per-operation; concurrent test con 5 connectors simulados.
- **R-bajo**: dependencies.py split. Mitigación: re-exports en __init__.py preservan API; smoke test importa todos los símbolos antes/después.

### Cronograma estimado

- 6 olas, secuenciales, 5-6 días de implementación efectiva.
- Spec → /speckit.plan → /speckit.tasks → /speckit.implement por ola.
