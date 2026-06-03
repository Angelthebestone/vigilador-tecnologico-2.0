# Implementation Plan: Backend Optimization & Google Workspace MCP Revert

**Spec**: [spec.md](spec.md)
**Research**: [research.md](research.md)
**Branch**: main (NO feature branch — política user NO commits)
**Created**: 2026-06-01

## Problem

Backend acumuló 4 hot-paths con N+1 (discover() 22 embeddings/query, skills boot 30-90s, 11 providers sin pooling, dependencies.py monolítico 694 LOC), 1 desviación arquitectónica crítica (Google Workspace WRAP-SDK con 4 capabilities en lugar de MCP-EXTERNO con ~30+ del plan original ANEXO-B C1.4 vigente), 5 SDKs oficiales no aprovechados, 3 servicios duplicados cross-composition, 501 LOC dead code, y 30 archivos roadmap mezclados con runtime activo. Todo medible y verificable.

## Approach

6 olas secuenciales (~5-6 días) que aterrizan los 32 FRs del spec sin tocar 2.0:

1. **Infra base** (aditiva, sin cambio de comportamiento): `BaseHTTPProvider`, `EmbeddingCache` (L1 LRU + L2 disk), sync writers preservados.
2. **N+1 fix tools**: pre-compute embeddings en register, batch SQL en `_get_status`, integración con `EmbeddingCache`.
3. **Skills boot optimization**: disk-cache embeddings, batch HashTracker save, frontmatter-only adapters, `_cold/` move.
4. **Provider migration**: 5 SDK migrations + 6 BaseHTTPProvider refactors + `Google Workspace MCP revert`.
5. **Composition root**: split `dependencies.py` → paquete, singleton dedup, lazy WS imports.
6. **Correctness + cleanup**: TurboVec lock per-tenant, MCP cache LRU, DB pool config, dead-code remove, `_roadmap/` move.

Cada ola termina con suite gate-sagrada verde (FR-028) y rollback determinista por archivo.

---

## Technical Context

| Area | Decision |
|------|----------|
| **Plataforma** | Python 3.11+ con asyncio. `numpy>=1.26` añadida obligatoria (FR-004). |
| **Build** | `pyproject.toml` con dependencias pinneadas (R-01: tavily-python, exa-py, firecrawl-py, pyalex, arxiv). |
| **Runtime composition** | `api/app.py` lifespan + split `api/dependencies/` (10 submodules) + `api/enterprise_composition.py` con singleton dedup. |
| **HTTP layer** | `BaseHTTPProvider` (R-04) con httpx pool 100/20, retry 3-exponential, error mapping. |
| **Cache** | Two-tier: in-memory LRU 1000 + disk JSON `~/.vigilador/cache/embeddings/` (R-05). Invalidación por content-hash. |
| **Embeddings** | Gemini `batchEmbedContents` cuando disponible, fallback `asyncio.gather` (R-02). |
| **Vector index** | TurboVec con `dict[UUID, asyncio.Lock]` per-tenant (R-06). Locks separados write vs persist. |
| **Audit log** | Sync flush + `os.fsync` por evento (R-07). NO buffer. |
| **MCP supervisor** | Reactiva `MCPProcessSupervisor` para `google-workspace-mcp` (R-03). |
| **Skills** | `_cold/` subpath en `_vendor/`. Adapters filtran por path. Activación via env. (R-09). |
| **Type checking** | basedpyright-standard preservado. |
| **Testing** | pytest + respx (mocks HTTP) + golden output fixtures por provider. |

## External Constraints

| Constraint | Impact |
|------------|--------|
| **2.0 PRESERVADO (sagrado)** | `git diff --stat application/execution/ application/evaluation/` debe retornar 0 cambios al final de cada ola y al cierre. SC-010 verifica. |
| **NO commits/pushes** | Todas las olas dejan código uncommitted. Rollback via `git checkout`. Sin feature branches. |
| **Constitución v1.2.0** | ≤400 LOC/file (mandatorio en archivos nuevos), SRP, explicit errors, KISS, #5 quirúrgico. |
| **Spec 021 D1-D5** | TurboVec único, vendor en src, NO claude-local, NO user auth, native-first reafirmada. |
| **MVP scope C1** | 20 caps + 4 dominios + 3 modos + 3 playbooks. Productivity expansion via MCP NO altera dominios MVP. |
| **Python 3.11+ async** | Todos los locks son `asyncio.Lock`, NO `threading.Lock`. |
| **basedpyright-standard** | Imports tipados, fallbacks (numpy, Gemini batch) deben preservar shape. |

---

## Files to Create / Modify

### New Files

| File | Purpose | Ola |
|------|---------|-----|
| `src/vigilancia_multiagente/enterprise/tooling/builtin/_base/__init__.py` | Re-export BaseHTTPProvider | 1 |
| `src/vigilancia_multiagente/enterprise/tooling/builtin/_base/http_provider.py` | BaseHTTPProvider (~180 LOC) | 1 |
| `src/vigilancia_multiagente/enterprise/tooling/builtin/_base/retry_policy.py` | RetryPolicy + decorator (~60 LOC) | 1 |
| `src/vigilancia_multiagente/infra/embeddings/embedding_cache.py` | Two-tier LRU+disk cache (~120 LOC) | 1 |
| `src/vigilancia_multiagente/api/dependencies/__init__.py` | Re-exports (~30 LOC) | 5 |
| `src/vigilancia_multiagente/api/dependencies/orchestration.py` | _build_orchestration_services (~70 LOC) | 5 |
| `src/vigilancia_multiagente/api/dependencies/agents.py` | _build_agent_services (~80 LOC) | 5 |
| `src/vigilancia_multiagente/api/dependencies/execution.py` | _build_execution_services (~30 LOC) | 5 |
| `src/vigilancia_multiagente/api/dependencies/strategic_signals.py` | (~80 LOC) | 5 |
| `src/vigilancia_multiagente/api/dependencies/deep_analysis.py` | (~80 LOC) | 5 |
| `src/vigilancia_multiagente/api/dependencies/data_intelligence.py` | (~80 LOC) | 5 |
| `src/vigilancia_multiagente/api/dependencies/source_quality.py` | (~70 LOC) | 5 |
| `src/vigilancia_multiagente/api/dependencies/assurance.py` | (~70 LOC) | 5 |
| `src/vigilancia_multiagente/api/dependencies/governance.py` | (~70 LOC) | 5 |
| `src/vigilancia_multiagente/api/dependencies/session.py` | (~50 LOC) | 5 |
| `src/vigilancia_multiagente/api/dependencies/_singletons.py` | @lru_cache factories (~60 LOC) | 5 |
| `tests/enterprise/tooling/test_base_http_provider.py` | Unit tests retry/timeout/pooling (~200 LOC) | 1 |
| `tests/infra/embeddings/test_embedding_cache.py` | LRU + disk + invalidation (~150 LOC) | 1 |
| `tests/enterprise/tooling/test_provider_contract.py` | Parametrized contract verification (~80 LOC) | 4 |
| `tests/enterprise/tooling/test_tavily_sdk.py` | Tavily SDK migration verify | 4 |
| `tests/enterprise/tooling/test_exa_sdk.py` | Exa SDK migration | 4 |
| `tests/enterprise/tooling/test_firecrawl_sdk.py` | Firecrawl SDK migration | 4 |
| `tests/enterprise/tooling/test_pyalex_migration.py` | OpenAlex SDK | 4 |
| `tests/enterprise/tooling/test_arxiv_sdk.py` | Arxiv SDK | 4 |
| `tests/enterprise/tooling/test_google_workspace_mcp.py` | MCP integration smoke | 4 |
| `tests/enterprise/tooling/test_tool_registry_loads_long_description.py` | FR-034: verifica que get_docs() carga rich docs desde prompts/tools/ | 6 |
| `src/vigilancia_multiagente/prompts/tools/google-workspace-mcp.txt` | FR-035: nuevo system-prompt rich con 25+ capabilities Google Workspace MCP | 4 |
| `tests/infra/persistence/test_turbovec_concurrent.py` | Lock concurrency (~120 LOC) | 6 |
| `tests/infra/db/test_pool_config.py` | DB pool env config (~50 LOC) | 6 |
| `docs/release-notes-022.md` | Changelog migración SDK + revert MCP | Cierre |

### Modified Files

| File | Changes | Ola |
|------|---------|-----|
| `pyproject.toml` | +numpy, +tavily-python, +exa-py, +firecrawl-py, +pyalex, +arxiv | 4 |
| `pytest.ini` | --ignore=tests/.../_roadmap/ por default | 6 |
| `src/vigilancia_multiagente/enterprise/tooling/tool_registry.py` | Pre-compute embeddings en register, batch _get_status, EmbeddingCache wire, **+ get_docs() carga `prompts/tools/<name>.txt` como long_description (FR-034)** | 2+6 |
| `src/vigilancia_multiagente/infra/persistence/tool_health_repository.py` | +get_statuses_batch(names: list[str]) | 2 |
| `src/vigilancia_multiagente/enterprise/skills_marketplace/skill_registry.py` | EmbeddingCache disk wire, batch save | 3 |
| `src/vigilancia_multiagente/enterprise/skills_marketplace/skill_loader.py` | Frontmatter-only read paths | 3 |
| `src/vigilancia_multiagente/enterprise/skills_marketplace/k_dense_adapter.py` | Filtrar `_cold/` paths, frontmatter-only | 3 |
| `src/vigilancia_multiagente/enterprise/skills_marketplace/agency_agents_adapter.py` | Filtrar `_cold/` paths | 3 |
| `src/vigilancia_multiagente/enterprise/skills_marketplace/hash_tracker.py` | save_all() batch method | 3 |
| `src/vigilancia_multiagente/infra/embeddings/gemini_gateway.py` | batchEmbedContents wire + LRU | 3 |
| `src/vigilancia_multiagente/enterprise/tooling/builtin/research/tavily.py` | → tavily-python SDK (~40 LOC) | 4 |
| `src/vigilancia_multiagente/enterprise/tooling/builtin/research/exa.py` | → exa-py SDK | 4 |
| `src/vigilancia_multiagente/enterprise/tooling/builtin/research/firecrawl.py` | → firecrawl-py SDK | 4 |
| `src/vigilancia_multiagente/enterprise/tooling/builtin/research/openalex.py` | → pyalex SDK | 4 |
| `src/vigilancia_multiagente/enterprise/tooling/builtin/research/arxiv.py` | → arxiv SDK | 4 |
| `src/vigilancia_multiagente/enterprise/tooling/builtin/research/brave.py` | → BaseHTTPProvider | 4 |
| `src/vigilancia_multiagente/enterprise/tooling/builtin/research/serper.py` | → BaseHTTPProvider | 4 |
| `src/vigilancia_multiagente/enterprise/tooling/builtin/research/serper_patents.py` | → BaseHTTPProvider | 4 |
| `src/vigilancia_multiagente/enterprise/tooling/builtin/research/jina.py` | → BaseHTTPProvider | 4 |
| `src/vigilancia_multiagente/enterprise/tooling/builtin/web/fetch.py` | → BaseHTTPProvider | 4 |
| `src/vigilancia_multiagente/enterprise/tooling/builtin/creative/minimax_image.py` | → BaseHTTPProvider | 4 |
| `config/mcp/external.yaml` | +google-workspace-mcp manifest entry | 4 |
| `config/tools/catalog.yaml` | google_workspace: strategy=MCP-EXTERNO, runtime=stdio_external, capabilities expanded | 4 |
| `src/vigilancia_multiagente/prompts/tools/{tavily,exa,firecrawl,openalex,arxiv,brave,serper,serper_patents,jina,fetch,minimax_image}.txt` (11 archivos) | FR-035: actualizar function_signature + best_for + chaining tras migración a SDK / BaseHTTPProvider | 4 |
| `src/vigilancia_multiagente/api/enterprise_composition.py` | Pasar embedding_gateway singleton; remover GoogleWorkspaceTool | 4+5 |
| `src/vigilancia_multiagente/api/app.py` | Wire BaseHTTPProvider.aclose() en lifespan.shutdown | 4 |
| `src/vigilancia_multiagente/infra/db/connection.py` | pool_size=10, max_overflow=20 (env configurable) | 6 |
| `src/vigilancia_multiagente/infra/persistence/turbovec_index.py` | Per-tenant asyncio.Lock dict, separate write/persist locks | 6 |
| `src/vigilancia_multiagente/infra/mcp/mcp_cache.py` | LRU max_entries config, env TTL | 6 |
| `src/vigilancia_multiagente/enterprise/governance/audit_log.py` | os.fsync per write (verify) | 6 |
| `src/vigilancia_multiagente/enterprise/governance/pi_quarantine_writer.py` | os.fsync per write (verify) | 6 |
| `scripts/check-layer-imports.py` | Skip _roadmap/ + _cold/ paths | 6 |

### Removed Files

| File | Razón | Ola |
|------|-------|-----|
| `src/vigilancia_multiagente/infra/mcp/playwright_mcp.py` | 0 imports externos, suplantado por enterprise/tooling/builtin/web/playwright.py | 6 |
| `src/vigilancia_multiagente/infra/mcp/minimax_image_mcp.py` | 0 imports externos, suplantado por enterprise/tooling/builtin/creative/minimax_image.py | 6 |
| `src/vigilancia_multiagente/enterprise/skills_marketplace/claude_local_adapter.py` | D3: NO claude-local en runtime | 6 |
| `src/vigilancia_multiagente/enterprise/tooling/builtin/productivity/google_workspace.py` | Revert a MCP-EXTERNO (FR-010) | 4 |
| `tests/enterprise/tooling/builtin/productivity/test_google_workspace.py` | Reemplazado por test_google_workspace_mcp.py | 4 |
| `src/vigilancia_multiagente/infra/llm/minimax_client.py` (146 LOC) | FR-033 revisada: MiniMax LLM legacy. Xiaomimimo es default MVP por D5. NO se mueve a `_legacy/` — DELETE total. | 6 |
| `tests/test_minimax_client.py` | FR-033: dependency de `minimax_client.py` | 6 |
| `src/vigilancia_multiagente/prompts/minimax_examples/*.txt` (4) | FR-033: solo consumidos por `minimax_client.py` | 6 |

### Moved Files (a `_roadmap/`, `_cold/`)

| Source → Target | Files | Ola |
|---|---|---|
| `src/.../enterprise/artifacts/*.py` → `enterprise/_roadmap/artifacts/` | 9 | 6 |
| `src/.../enterprise/orchestration/app_development/*.py` → `orchestration/_roadmap/app_development/` | 11 | 6 |
| `src/.../enterprise/orchestration/goal_pursuit/*.py` → `orchestration/_roadmap/goal_pursuit/` | 7 | 6 |
| `src/.../enterprise/dreaming/loops/*.py` → `dreaming/_roadmap_loops/` | 7 | 6 |
| 8 phases F5b → `dreaming/phases/_roadmap/` | 8 | 6 |
| **`_vendor/k_dense/skills/{62 científicas}/` → `_vendor/_cold/k_dense/skills/`** (FR-037; **NO incluye** `consciousness-council`) | **62 dirs** | **3** |
| **`_vendor/agency_agents/game-development/` → `_vendor/_cold/agency_agents/game-development/`** | **~50 archivos** | **3** |
| **`_vendor/agency_agents/spatial-computing/` → `_vendor/_cold/agency_agents/spatial-computing/`** | **6 archivos** | **3** |
| **`_vendor/agency_agents/specialized/{13 archivos}` → `_vendor/_cold/agency_agents/specialized/`** | **13 archivos** | **3** |
| Tests roadmap → `tests/.../_roadmap/` | ~30 | 6 |

---

## Constitution Check (Pre-Design)

- **Gate result**: PASS

- **Alignment**:
  - **Pensar Antes de Codificar**: 14 assumptions documentadas en spec (A-01..A-14). 9 decisiones del usuario (E-01..E-09) cerradas con rationale. Phase 0 (research.md) resuelve 15 puntos técnicos. 0 NEEDS CLARIFICATION restantes.
  - **Simplicidad Obligatoria**: SDKs oficiales en lugar de re-implementación; BaseHTTPProvider centraliza patrón compartido (no abstracción especulativa); ningún feature flag agregado (R-14). Lock granularidad mínima (R-06).
  - **Modularidad Primero**: cada FR mapea a 1-3 archivos. `BaseHTTPProvider` como módulo SRP. `_singletons.py` como SRP factory. `_roadmap/` separa runtime de futuro. SoC entre infra (cache, db, embeddings) y enterprise (tools, governance).
  - **Manejo de Errores Estricto**: retry policy explícita en BaseHTTPProvider (3 intentos + tipos específicos). Lock timeout explícito (30s, EC-08). EmbeddingCache corruption auto-recovery con WARNING (EC-01). NO `try/except: pass`. ProviderUnconfiguredError vs HealthcheckResult diferenciados.
  - **Cambios Quirúrgicos y Trazables**: matriz FR↔archivo en este plan. Cada ola = subset disjoint de archivos. Rollback granular `git checkout <archivo>` por FR. NO `ruff --fix` sobre directorios (Constitución #5).
  - **Entrega Verificable**: 15 SCs cuantitativos en spec. Plan de testing por ola con gate sagrado (FR-028). Pre/post measurement automatizable con scripts.

- **Diseño de Software**:
  - **SRP**: cada submodule de `dependencies/` 1 workstream; `BaseHTTPProvider` 1 patrón HTTP; `EmbeddingCache` 1 responsabilidad cache.
  - **DIP**: `BaseHTTPProvider` extendido (subclasses) o reemplazado por SDKs (drop-in). Tests inyectan respx mocks vía fixture.
  - **DRY**: 11 providers HTTP boilerplate consolidado en BaseHTTPProvider. 3 servicios duplicados deduplicados via `@lru_cache`.
  - **KISS**: `_cold/` es path filter (no nuevo schema). `_roadmap/` es directorio con `pytest --ignore`.
  - **YAGNI**: NO se añade Redis, NO event bus, NO feature flags, NO config UI. Solo lo que el spec explícita.
  - **Bajo Acoplamiento**: `embedding_cache.py` sin deps a tooling/skills (puerto). Tools heredan de base sin saber de cache.
  - **POLA**: imports `from api.dependencies import X` siguen funcionando post-split (re-exports).
  - **CQS**: `EmbeddingCache.get()` query, `set()` command. `BaseHTTPProvider.post()` command, `healthcheck()` query. AuditLog `log_*()` commands.

---

## Phases

### Phase 1 — Infra base (aditiva)

**FRs**: FR-013 (BaseHTTPProvider), FR-006 (LRU cache)
**Riesgo**: Bajo (código aditivo, 0 cambio comportamiento existente)
**LOC**: +280 / -0

1. Crear `enterprise/tooling/builtin/_base/{__init__, http_provider, retry_policy}.py` con la API definida en R-04.
2. Crear `infra/embeddings/embedding_cache.py` con two-tier (R-05).
3. Tests: `test_base_http_provider.py` (retry mock 503→200, timeout, pool reuse), `test_embedding_cache.py` (LRU evict, disk persist, hash invalidation).
4. Verificar: `pytest tests/enterprise/tooling/test_base_http_provider.py tests/infra/embeddings/test_embedding_cache.py -x` → verde.
5. Gate sagrado: pytest baseline → 0 regression.

**Output**: 5 nuevos archivos en `_base/` y `infra/embeddings/embedding_cache.py`. 2 nuevos test files. Sin modificar código existente.

**Rollback**: `rm -rf _base/ embedding_cache.py test_base_http_provider.py test_embedding_cache.py`. Cero impact.

---

### Phase 2 — N+1 fix tools

**FRs**: FR-001 (precompute embeddings), FR-002 (batch SQL)
**Depende**: Phase 1 (EmbeddingCache existe)
**Riesgo**: Medio (cambio en hot path discover)
**LOC**: +50 / -15

1. Modificar `enterprise/tooling/tool_registry.py`:
   - `register()` calcula embedding de description → cachea via `EmbeddingCache.set(content_hash, vector)`.
   - `discover()` consulta `EmbeddingCache.get_many()` para todas las tools (1 lookup), pre-fetched.
   - `discover()` invoca nuevo `tool_health_repo.get_statuses_batch(names)` (1 query SQL).
2. Modificar `infra/persistence/tool_health_repository.py`:
   - Añadir `async def get_statuses_batch(self, names: list[str], tenant_id: UUID) -> dict[str, str]`.
   - SQL: `SELECT name, status FROM tool_health WHERE tenant_id = $1 AND name = ANY($2)`.
3. Tests: `test_discover_precomputed_embeddings.py`, `test_get_statuses_batch.py`.
4. Benchmark: `test_discover_latency_under_500ms` (warm).
5. Gate sagrado.

**Output**: 2 archivos modificados, 3 nuevos test files. Latencia discover() <200ms (SC-002).

**Rollback**: `git checkout tool_registry.py tool_health_repository.py`.

---

### Phase 3 — Skills boot optimization

**FRs**: FR-003 (skill embed cache), FR-005 (Gemini batch), FR-025 (`_cold/`)
**Depende**: Phase 1 (EmbeddingCache)
**Riesgo**: Medio (cambio en adapters parsing)
**LOC**: +90 / -20

1. Modificar `enterprise/skills_marketplace/skill_registry.py`:
   - Constructor recibe `embedding_cache: EmbeddingCache`.
   - `_load_skills()` consulta cache disk antes de embed; HashTracker valida frescura.
2. Modificar `k_dense_adapter.py` y `agency_agents_adapter.py`:
   - `scan()` filtra paths que contengan `/_cold/`.
   - Lectura frontmatter-only en boot (regex `^---\n.*?\n---` non-greedy con `re.DOTALL`).
3. Modificar `hash_tracker.py`:
   - Añadir `save_all()` que escribe todas las entries en 1 file write.
   - `update()` solo modifica memoria; persiste solo al final del registry build.
4. Modificar `infra/embeddings/gemini_gateway.py`:
   - `embed_documents()` chunks en batches de 100, llama `client.embed_content_batch()` si disponible (R-02).
   - LRU `@lru_cache` envuelto el método interno `_embed_single`.
5. Mover 62 K-Dense skill directorios + 2 agency_agents divisions completas + 13 archivos individuales `specialized/` a `_vendor/_cold/`:
   - **K-Dense (62)** — lista exhaustiva en `data-model.md` Section "Skills `_cold/`". **NO incluye** `consciousness-council` (preservada para F4b decision-debate roadmap): adaptyv, aeon, anndata, astropy, biopython, bioservices, bulk-rnaseq, cellxgene-census, cirq, clinical-decision-support, clinical-reports, cobrapy, datamol, deepchem, deeptools, depmap, dhdna-profiler, diffdock, dnanexus-integration, esm, fluidsim, geniml, geomaster, geopandas, gget, ginkgo-cloud-lab, glycoengineering, gtars, histolab, imaging-data-commons, labarchive-integration, lamindb, latchbio-integration, matchms, molecular-dynamics, molfeat, neurokit2, neuropixels-analysis, omero-integration, opentrons-integration, optimize-for-gpu, pacsomatic, pathml, pathway-enrichment, pennylane, primekg, protocolsio-integration, pydeseq2, pydicom, pyhealth, pylabrobot, pyopenms, pysam, pytdc, qiskit, qutip, scanpy, scikit-bio, scikit-survival, scvelo, scvi-tools, tiledbvcf, torchdrug.
   - **agency_agents (2 divisions completas)**: `game-development/` (~50 files) + `spatial-computing/` (6 files).
   - **agency_agents/specialized/ (13 archivos individuales)**: `specialized-civil-engineer.md`, `specialized-french-consulting-market.md`, `specialized-korean-business-navigator.md`, `study-abroad-advisor.md`, `zk-steward.md`, `real-estate-buyer-seller.md`, `lsp-index-engineer.md`, `healthcare-customer-service.md`, `healthcare-marketing-compliance.md`, `hospitality-guest-services.md`, `retail-customer-returns.md`, `loan-officer-assistant.md`, `identity-graph-operator.md`.
   - Comando: `git mv <source> <target>` por cada path. Updates en imports de tests si los hay (probablemente cero).
6. Tests: `test_skill_embedding_disk_cache.py`, `test_hash_tracker_batch.py`, `test_frontmatter_only_read.py`, `test_gemini_batch_embed.py`, `test_cold_skills_filtered.py`.
7. Gate sagrado + measure: `time python -c "from vigilancia_multiagente.api.app import create_app; create_app()"` < 5 s (SC-001).

**Output**: 4 archivos modificados + 8 directorios movidos. 5 nuevos test files. Boot <5s.

**Rollback**: `git checkout` + `mv _vendor/_cold/* _vendor/k_dense/skills/`.

---

### Phase 4 — Provider migration

**FRs**: FR-009..FR-015
**Depende**: Phase 1 (BaseHTTPProvider)
**Riesgo**: Medio (11 archivos tocados, riesgo concentrado en providers con auth no-estándar)
**LOC**: +130 / -520 (neto -390)

1. Add deps a `pyproject.toml`: numpy, tavily-python, exa-py, firecrawl-py, pyalex, arxiv. `pip install -e .` verify.
2. **Migrar providers a SDK oficial** (orden R-08, uno a la vez con test verde):
   1. **Tavily** (PoC): refactor a `TavilyClient(api_key)`, sólo expose 1 método `execute("search", query)` mapeado a `client.search(query)`. ~40 LOC.
   2. **OpenAlex**: `pyalex.Works().filter(...)`. Polite pool con `pyalex.config.email`.
   3. **Arxiv**: `arxiv.Client().results(arxiv.Search(query=...))`.
   4. **Exa**: `exa_py.Exa(api_key).search(query)`, opcional `find_similar`, `extract`.
   5. **Firecrawl**: `firecrawl_py.AsyncFirecrawlApp(api_key).scrape_url(url)`.
3. **Migrar a BaseHTTPProvider** (6 providers):
   - Brave: subclass con custom header `X-Subscription-Token`.
   - Serper: header `X-API-KEY`, body endpoint POST.
   - Serper Patents: extends Serper, endpoint diferente.
   - Jina: simple Bearer.
   - Fetch: sin auth, opcional `markitdown` para HTML→text.
   - MiniMax Image: multipart support.
4. **Google Workspace MCP revert**:
   - Eliminar `enterprise/tooling/builtin/productivity/google_workspace.py` y test.
   - Editar `config/tools/catalog.yaml`: `google_workspace` → `strategy: MCP-EXTERNO`, `runtime: stdio_external`, capabilities expandidas (~25-30 listadas).
   - Editar `config/mcp/external.yaml`: añadir entry `google-workspace-mcp` con `command: npx`, `args: [-y, @taylorwilsdon/google-workspace-mcp]`, `env: {GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI}`, healthcheck 60s, restart on-failure.
   - Editar `enterprise_composition.py`: remover instanciación GoogleWorkspaceTool del builtin_tools tuple. El supervisor MCP lo levanta automáticamente; `MCPProcessSupervisor.start_all()` ya está wireado en lifespan.
   - Crear `tests/.../test_google_workspace_mcp.py` smoke test.
   - **Crear `prompts/tools/google-workspace-mcp.txt`** (FR-035) con guidance estructurada (function_signature por capability, best_for, selection_heuristics, chaining para flows multi-step Gmail+Calendar+Drive).

5. **Actualizar `prompts/tools/<name>.txt`** (FR-035) para los 11 providers refactorizados en pasos 2-3:
   - Tavily: actualizar firma a SDK API (`tavily-python.search`).
   - Exa: agregar `find_similar`, `extract` capabilities.
   - Firecrawl: actualizar a `firecrawl-py` async API.
   - OpenAlex: pyalex idiomático.
   - Arxiv: SDK `arxiv` API.
   - Brave, Serper, Serper Patents, Jina, Fetch, MiniMax Image: validar/actualizar tras BaseHTTPProvider refactor.
   - **Eliminar `prompts/tools/scholar.txt`** si Google Scholar SDK migration ya elimina el wrapper específico (mantener solo si scholar persiste como tool name).
   - Cada update preserva el formato XML estructurado (`<tool>`, `<function_signature>`, `<best_for>`, `<selection_heuristics>`, `<chaining>`, `<fallback>`, `<rules>`).

6. Wire `BaseHTTPProvider.aclose()` y SDK clients en `app.py:lifespan.shutdown`.
7. Crear `test_provider_contract.py` paramétrico (R-15).
8. Gate sagrado + verify SC-004 (≥25 capabilities productivity post-MCP), SC-013 (provider contract), SC-005 (retry).

**Output**: 11 providers refactorizados (5 a SDK, 6 a base). 1 archivo eliminado (Google Workspace). 2 archivos config actualizados. 7 nuevos test files (1 por SDK + contract + MCP smoke).

**Rollback**: cada provider tiene su archivo. `git checkout enterprise/tooling/builtin/research/tavily.py` revierte solo Tavily.

---

### Phase 5 — Composition root split + singleton dedup

**FRs**: FR-016, FR-017, FR-018
**Depende**: Phase 4 (composition referencia stable)
**Riesgo**: Bajo (Python file→package transparente; re-exports preservan API)
**LOC**: +625 / -580 (neto +45)

1. Crear `api/dependencies/__init__.py` con todos los re-exports de los 10 `_build_*` symbols + helpers.
2. Crear los 10 submodules en `api/dependencies/{orchestration,agents,execution,strategic_signals,deep_analysis,data_intelligence,source_quality,assurance,governance,session}.py` cada uno ≤100 LOC con su `_build_*_services` original.
3. Crear `api/dependencies/_singletons.py`:
   - `@lru_cache def get_embedding_gateway() -> GeminiEmbeddingGateway`
   - `@lru_cache def get_knowledge_graph_service() -> KnowledgeGraphService`
   - `@lru_cache def get_tool_health_repo(database) -> ToolHealthRepository`
4. Modificar `api/enterprise_composition.py`:
   - Importar singletons desde `api.dependencies._singletons`.
   - Pasar `embedding_gateway = get_embedding_gateway()` (no instanciar nuevo).
5. Eliminar `api/dependencies.py` (el monolítico 694 LOC). El package toma su lugar.
6. Lazy imports: mover imports de `application.evaluation.ws_*` a dentro de `_build_*_services()` que los usan (deferred until WS flag check).
7. Tests: `test_dependencies_reexports.py` verifica que todos los símbolos del original siguen importables.
8. Gate sagrado completo (FULL `pytest tests/`).

**Output**: 11 archivos nuevos en `api/dependencies/`, 1 archivo eliminado. API pública preservada 100% via re-exports.

**Rollback**: `git rm -r api/dependencies/ && git checkout HEAD~1 -- api/dependencies.py` recupera el original.

---

### Phase 6 — Correctness, cleanup, _roadmap aislamiento

**FRs**: FR-007, FR-008, FR-019, FR-020, FR-021, FR-022, FR-023, FR-024, FR-026
**Depende**: Phases 1-5 completas (cleanup al final preserva visibilidad)
**Riesgo**: Medio (TurboVec lock cambia hot path; cleanup amplio)
**LOC**: +85 / -30 + 30 archivos movidos

1. **Correctness fixes**:
   - `infra/persistence/turbovec_index.py`: `self._tenant_locks: dict[UUID, asyncio.Lock] = {}`. `_get_lock(tid)` lazy con `asyncio.Lock` compartido. `add()` adquiere `_write_lock`, `persist()` adquiere `_persist_lock` separado.
   - `enterprise/governance/audit_log.py`: verificar `os.fsync(fh.fileno())` post-write. Si falta, añadir.
   - `enterprise/governance/pi_quarantine_writer.py`: ídem fsync.
2. **Config**:
   - `infra/db/connection.py`: `pool_size=int(os.environ.get("VT_DB_POOL_SIZE", 10))`, `max_overflow=int(os.environ.get("VT_DB_POOL_OVERFLOW", 20))`.
   - `infra/mcp/mcp_cache.py`: añadir `max_entries: int = int(os.environ.get("VT_MCP_CACHE_MAX_ENTRIES", 1000))`. LRU eviction con `collections.OrderedDict`. TTL via `VT_MCP_CACHE_TTL_SHORT/LONG`.
3. **Dead code remove** (FR-022, FR-033 revisada):
   - `git rm src/vigilancia_multiagente/infra/mcp/playwright_mcp.py`
   - `git rm src/vigilancia_multiagente/infra/mcp/minimax_image_mcp.py`
   - `git rm src/vigilancia_multiagente/enterprise/skills_marketplace/claude_local_adapter.py`
   - `git rm src/vigilancia_multiagente/infra/llm/minimax_client.py` (146 LOC, MiniMax LLM legacy — Xiaomimimo es default MVP)
   - `git rm tests/test_minimax_client.py`
   - `git rm -r src/vigilancia_multiagente/prompts/minimax_examples/` (4 archivos)
   - **NO eliminar**: `prompts/tools/*.txt` (FR-034 los wirea como ToolDocs.long_description)
   - **NO eliminar**: `enterprise/tooling/builtin/creative/minimax_image.py` (MiniMaxImageTool sigue activo en builtin tools)

4. **prompts/ wiring + reform** (FR-034, FR-036):
   - **Wirear** `enterprise/tooling/tool_registry.py:get_docs(name)`:
     - Cargar `long_description` desde `infra.prompts.loader.load_prompt(f"tools/{name}")` con try/except FileNotFoundError → string vacío.
     - Mantener cache LRU (ya lo tiene `load_prompt`).
   - Tests: `test_tool_registry_loads_long_description.py` — verifica que `get_docs("tavily").long_description` contiene `<function_signature>` esperado.
   - Verificar `prompts/branches/`, `prompts/evaluation/`, `prompts/orchestration/` SIN modificar (FR-036 — 2.0 preservado).

5. **`_roadmap/` aislamiento** (FR-023, FR-024):
   - Mover paquetes uno a uno con `git mv`. Update imports relativos via `sed` o búsqueda manual:
     - `enterprise.artifacts` → `enterprise._roadmap.artifacts`
     - `enterprise.orchestration.app_development` → `enterprise.orchestration._roadmap.app_development`
     - `enterprise.orchestration.goal_pursuit` → `enterprise.orchestration._roadmap.goal_pursuit`
     - `enterprise.dreaming.loops` → `enterprise.dreaming._roadmap_loops`
     - 8 phases F5b → `enterprise.dreaming.phases._roadmap`
   - Mover tests correspondientes.
   - Update `pytest.ini`: `addopts = --ignore=tests/enterprise/_roadmap --ignore=tests/enterprise/orchestration/_roadmap --ignore=tests/enterprise/dreaming/_roadmap_loops --ignore=tests/enterprise/dreaming/phases/_roadmap`.
   - Update `scripts/check-layer-imports.py` para skip esos paths.
6. Tests: `test_turbovec_concurrent.py` (5 connectors paralelos, count exacto), `test_pool_config.py` (env override), `test_mcp_cache_eviction.py`, `test_audit_flush_shutdown.py`.
7. Gate sagrado FULL. Measure SC-008 (tests <30s post-_roadmap).
8. Generar `docs/release-notes-022.md` con resumen completo.

**Output**: 4 archivos modificados (correctness/config), 7 eliminados (3 dead code + minimax_client + minimax test + 4 minimax prompts + claude_local_adapter), ~30 movidos a `_roadmap/`, 14 archivos `prompts/tools/*.txt` wireados en `get_docs()` (FR-034) + 1 nuevo google-workspace-mcp.txt, 131 directorios/files skills movidos a `_cold/`. 5 nuevos test files. Suite default <30s, total capabilities ≥45 (MVP + 25 Workspace), LOC reducido ≥5%.

**Rollback**: por categoría. Locks: revert `turbovec_index.py`. Cleanup: `git revert <commit>`. Mover roadmap: `git mv` reverso.

---

## Rollout Strategy

**Coexistencia 2.0/3.0**: ningún cambio toca código 2.0. `BranchCoordinator` y `ws_*` se usan vía `plugins/technology-watch/coordinator_wrapper.py` sin modificación.

**Backward compatibility**:
- API pública `from vigilancia_multiagente.api.dependencies import X` preservada via re-exports (FR-030).
- Tools tienen mismo Tool contract (Protocol). Migración de SDK o BaseHTTPProvider es transparente para callers.
- `_roadmap/` paths son importables explícitamente (no eliminados).

**Feature flags**: ninguno. Cada cambio es backward-compatible o rollback determinista (R-14).

**Deployment** (cuando aplique):
- numpy debe instalarse en el environment (verify pre-deploy).
- `npm install -g @taylorwilsdon/google-workspace-mcp` (o equivalent) en host MCP.
- DB pool size requiere DB conf compatible.
- Cache directory `~/.vigilador/cache/embeddings/` writable.

**Validación de cada ola**:
1. Pre-cambios: snapshot LOC, run gate sagrada (debe ser verde).
2. Aplicar cambios de la ola.
3. Run tests de la ola + gate sagrada (debe seguir verde).
4. Si falla: revert por archivo, retry.
5. Si pasa: medir SC correspondiente, documentar en release notes.

---

## Success Criteria

- **SC-001**: Cold start <5s. Verificado con script `time python -c "from vigilancia_multiagente.api.app import create_app; create_app()"`.
- **SC-002**: discover() p95 <200ms over 100 invocaciones. `pytest tests/enterprise/tooling/test_discover_latency.py::test_p95`.
- **SC-003**: skill discover() p95 <300ms. Análogo.
- **SC-004**: ≥25 capabilities en domain `productivity` post-onboarding Google Workspace. `curl /api/v2/enterprise/tools?domain=productivity | jq 'length'`.
- **SC-005**: Tavily 99% success rate con 30% 503 inyectado. `pytest tests/enterprise/tooling/test_tavily_retry.py`.
- **SC-006**: 5 ingestion concurrent = 5000 chunks exactos. `pytest tests/infra/persistence/test_turbovec_concurrent.py`.
- **SC-007**: 100 events post-SIGKILL = 100 entries en JSONL. Manual smoke test.
- **SC-008**: pytest tests/ < 30s. `time pytest tests/ -q`.
- **SC-009**: 0 archivos >400 LOC modificados/nuevos. `find src -name '*.py' | xargs wc -l | awk '$1>400'` retorna empty.
- **SC-010**: 0 cambios en 2.0 preservado. `git diff --stat application/execution/ application/evaluation/`.
- **SC-011**: -5% LOC src + tests. `tokei` antes/después.
- **SC-012**: 0 layer-import violations. `python scripts/check-layer-imports.py`.
- **SC-013**: 14 tools satisfy Protocol contract. `pytest tests/enterprise/tooling/test_provider_contract.py`.
- **SC-014**: ≥45 total capabilities. Suma del catalog post-MCP wire.
- **SC-015**: -3MB RSS post-boot. Profile con psutil pre/post.

---

## Constitution Check (Post-Design)

- **Status**: PASS
- **Justification**:
  - Cada principio respetado y trazable a FRs concretos:
    - **#1 Pensar Antes**: 14 assumptions + 9 decisiones cerradas + Phase 0 research.
    - **#2 Simplicidad**: KISS reafirmado (R-14 sin feature flags), YAGNI (sin Redis/event bus), SDK > re-implementación.
    - **#3 Modularidad**: split `dependencies/`, `_base/` por responsabilidad, `_roadmap/` aislamiento.
    - **#4 Errores Estrictos**: retry policy explícita, lock timeout explícito, ProviderUnconfiguredError, EC-XX cubren edge cases.
    - **#5 Quirúrgicos**: matriz FR↔archivo en este plan; rollback por archivo; NO touch 2.0 (FR-027/028/029 + SC-010).
    - **#6 Verificable**: 15 SCs cuantitativos con scripts.
  - **Diseño**: SRP, DIP, DRY, KISS, YAGNI, Bajo Acoplamiento, POLA, CQS — todos aplicados con ejemplos.
  - 0 violaciones a principios. 0 NEEDS CLARIFICATION. 0 deviations spec 021 D1-D5.
  - Plan listo para `/speckit.tasks` (descomposición en T001..TNNN).
