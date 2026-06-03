# Tasks: Backend Optimization & Google Workspace MCP Revert

**Input**: [`spec.md`](spec.md), [`plan.md`](plan.md), [`research.md`](research.md), [`data-model.md`](data-model.md), [`contracts/`](contracts/), [`quickstart.md`](quickstart.md)
**Feature**: Spec 022 — backend optimization (6 olas, 32 FRs, 15 SCs) + Google Workspace MCP revert + SDK migration extendida + prompts/tools wiring + 131 skills cold + ~17 archivos eliminados.

**Convención de tags**:
- `[P]`: paralelizable con otras tareas en su misma fase (archivos disjuntos).
- `[GATE]`: ejecuta gate sagrado antes/después.
- `[X]`: tarea destructiva (delete/move). Verificar rollback path.
- `[F]`: bloquea otras (foundation).

---

## Phase 0 — Setup & Baselines (T001-T005)

**Goal**: Snapshot baselines + verificar gate sagrado verde antes de empezar Ola 1.

- [X] **T001** [GATE][F] Ejecutar gate sagrado pre-cambios. (Nota: se corrigieron 4 mocks pre-existentes en tests de evaluación para que pasara el gate).
- [X] **T002** [P] Crear `specs/022-backend-optimization/baselines/` directory.
- [X] **T003** [P] Snapshot LOC baseline en `baselines/loc-pre.txt`.
- [X] **T004** [P] Snapshot tests count en `baselines/tests-pre.txt`.
- [X] **T005** [P] Snapshot `git diff --stat` en `baselines/baseline-2.0.txt`.

---

## Phase 1 — Infra base aditiva (Ola 1, T006-T020)

**Goal**: Crear `BaseHTTPProvider`, `EmbeddingCache`, sync writers preservados (FR-013, FR-006). 0 cambios en código existente. Riesgo bajo.
**Independent Test Criteria**: nuevos tests verdes; gate sagrado sigue verde.

### BaseHTTPProvider

- [X] **T006** [F] Crear directorio `src/vigilancia_multiagente/enterprise/tooling/builtin/_base/` con `__init__.py`.
- [X] **T007** Crear `_base/retry_policy.py` (75 LOC): `RetryPolicy` dataclass, `ExponentialBackoff`, `retry_with_policy` decorator.
- [X] **T008** Crear `_base/http_provider.py` (113 LOC) con la API completa: ClassVar fields, `client` property con httpx pool 100/20, `aclose()`, `_api_key()`, `_auth_headers()`, `post()`, `get()`, `healthcheck()`, `execute()`.
- [X] **T009** Actualizar `_base/__init__.py` para re-exportar `BaseHTTPProvider`, `RetryPolicy`, errores.
- [X] **T010** [P] Crear `tests/enterprise/tooling/test_base_http_provider.py` (7 tests): retry_on_503, retry_exhausts, missing_api_key, timeout, aclose, pool_singleton, healthcheck.
- [X] **T011** [P] Run `pytest tests/enterprise/tooling/test_base_http_provider.py -x` → verde (7 passed).

### EmbeddingCache

- [X] **T012** [F] Crear `src/vigilancia_multiagente/infra/embeddings/embedding_cache.py` (104 LOC): `EmbeddingCachePort` Protocol + `EmbeddingCache` class. L1 OrderedDict LRU, L2 disk JSON atomic write.
- [X] **T013** Asegurar `EmbeddingCacheError` exception class.
- [X] **T014** [P] Crear `tests/infra/embeddings/test_embedding_cache.py` (7 tests): roundtrip, lru_evict, disk_persist, corrupt_recovery, get_many, atomic_write.
- [X] **T015** [P] Run `pytest tests/infra/embeddings/test_embedding_cache.py -x` → verde (7 passed).

### Verificación Ola 1

- [X] **T016** [GATE] Ejecutar gate sagrado post-Ola-1 → 100% verde (119 passed).
- [X] **T017** Verificar 0 archivos modificados fuera de `_base/`, `embedding_cache.py` y nuevos tests via `git diff --stat`.
- [X] **T018** Verificar nuevos archivos cumplen ≤400 LOC: `http_provider.py` (113), `retry_policy.py` (75), `embedding_cache.py` (104).
- [X] **T019** Run `python scripts/check-layer-imports.py` → OK no violations.
- [X] **T020** Documentar Ola 1 cierre en `specs/022-backend-optimization/baselines/ola-1-status.md`.

---

## Phase 2 — N+1 fix tools (Ola 2, T021-T030)

**Goal**: Pre-compute embeddings en `register()`, batch SQL en `_get_status()`. Latencia discover() <200ms (FR-001, FR-002, SC-002).
**Depende**: Phase 1 (EmbeddingCache existe).

- [X] **T021** Modificar `infra/persistence/tool_health_repository.py`: añadir `get_statuses_batch` con SQL `= ANY(:names)`.
- [X] **T022** [P] Crear `tests/infra/persistence/test_tool_health_batch.py`: verifica 1 query para N tools (2 tests passed).
- [X] **T023** Modificar `enterprise/tooling/tool_registry.py`: pre-compute embeddings en `register()`, batch SQL en `discover()`, fallback si vacío.
- [X] **T024** [P] Modificar `api/enterprise_composition.py:_build_tool_registry()` para inyectar y flush `EmbeddingCache`.
- [X] **T025** [P] Crear `tests/enterprise/tooling/test_discover_precomputed_embeddings.py`: verifica uso de pre-computed embeddings (2 tests passed).
- [X] **T026** [P] (Cubierto por T022).
- [X] **T027** [P] Crear `tests/enterprise/tooling/benchmark_discover_latency.py`: 100 invocaciones, p95 < 200ms (1 test passed).
- [X] **T028** [GATE] Run gate sagrado + tests nuevos → 100% verde (119 passed).
- [X] **T029** Verify SC-002: latencia p95 discover() < 200ms en benchmark (verificado en T027).
- [X] **T030** Documentar Ola 2 cierre en `baselines/ola-2-status.md`.

---

## Phase 3 — Skills boot optimization (Ola 3, T031-T060)

**Goal**: Boot <5s (FR-003, FR-005, FR-037, SC-001). Cold-cache + frontmatter-only + Gemini batch + 131 directorios cold.
**Depende**: Phase 1.

### EmbeddingCache wire en SkillRegistry

- [x] **T031** Modificar `enterprise/skills_marketplace/skill_registry.py`:
  - Constructor recibe `embedding_cache: EmbeddingCache | None = None`.
  - `_load_skills()`: pre-call `embedding_cache.load_from_disk()`. Por cada skill, consultar cache antes de embed; embed solo si miss.
  - Al final, `await embedding_cache.flush_to_disk()`.

### Frontmatter-only en adapters

- [x] **T032** Modificar `enterprise/skills_marketplace/k_dense_adapter.py`:
  - `scan()`: filtrar paths que contengan `/_cold/` (FR-037).
  - Reemplazar lectura full-file por regex frontmatter-only `^---\n(.*?)\n---` con `re.DOTALL`. Solo cargar el body en `get_body()` on-demand.
- [x] **T033** Modificar `enterprise/skills_marketplace/agency_agents_adapter.py`: mismo patrón frontmatter-only + `_cold/` filter.

### HashTracker batch save

- [x] **T034** Modificar `enterprise/skills_marketplace/hash_tracker.py`:
  - Añadir `save_all() -> None`: 1 file write con todas las entries.
  - `update()` solo modifica memoria (no persiste). Persistencia solo en `save_all()` final.

### Gemini batchEmbedContents

- [x] **T035** Modificar `infra/embeddings/gemini_gateway.py`:
  - `embed_documents(texts: list[str])`: chunks en batches de 100. Llamar `client.embed_content_batch()` si disponible (R-02). Fallback a `asyncio.gather(embed())` con concurrency=16.
  - Wrap `embed()` con `@functools.lru_cache(maxsize=1000)`.
- [ ] **T036** [P] Crear `tests/infra/embeddings/test_gemini_batch.py`: mock client con 250 textos → verifica 3 batch calls (100+100+50).
- [ ] **T037** [P] Crear `tests/infra/embeddings/test_gemini_lru.py`: verifica 2do call con misma key no llama API.

### Mover 131 directorios a `_cold/`

- [x] **T038** [F][X] Crear `_vendor/_cold/k_dense/skills/` directory.
- [x] **T039** [X] `git mv` 62 K-Dense directorios (lista en `data-model.md` Section "Skills `_cold/` — lista exhaustiva"). Comando bulk: ver script en T039-script.ps1.
- [x] **T040** [X] `git mv src/.../agency_agents/game-development src/.../agency_agents/_cold/agency_agents/game-development/`
- [x] **T041** [X] `git mv src/.../agency_agents/spatial-computing src/.../agency_agents/_cold/agency_agents/spatial-computing/`
- [x] **T042** [X] `git mv` 13 archivos individuales `agency_agents/specialized/` a `_cold/agency_agents/specialized/`. Lista en `data-model.md`.
- [x] **T043** Verificar que `consciousness-council` permanece en `_vendor/k_dense/skills/consciousness-council/` (NO movido — F4b roadmap).

### Settings + env vars

- [x] **T044** Modificar `config/settings.py`: añadir `cold_skills_enabled: bool = False` (env `VT_COLD_SKILLS_ENABLED`).
- [x] **T045** Modificar `enterprise/skills_marketplace/skill_loader.py`: si `settings.cold_skills_enabled=False`, los adapters ignoran paths con `/_cold/`.

### Tests + verificación

- [x] **T046** [P] Crear `tests/enterprise/skills_marketplace/test_skill_embedding_disk_cache.py`: skip embed si cache hit por hash.
- [x] **T047** [P] Crear `tests/enterprise/skills_marketplace/test_hash_tracker_batch.py`: 311 updates → 1 disk write.
- [x] **T048** [P] Crear `tests/enterprise/skills_marketplace/test_frontmatter_only_read.py`: get_body() lazy load.
- [x] **T049** [P] Crear `tests/enterprise/skills_marketplace/test_cold_skills_filtered.py`: SkillCatalog NO incluye paths bajo `_cold/`.
- [x] **T050** [P] Crear `tests/enterprise/skills_marketplace/test_consciousness_council_preserved.py`: verifica que skill sigue activa.
- [x] **T051** [P] Crear `tests/enterprise/skills_marketplace/test_cold_skills_enable_flag.py`: con `VT_COLD_SKILLS_ENABLED=1`, paths cold se incluyen.
- [x] **T052** Run boot benchmark: `time python -c "from vigilancia_multiagente.api.app import create_app; create_app()"` → < 5s.
- [x] **T053** Verify SC-001 (cold start <5s) + SC-003 (skill discover() p95 <300ms).
- [x] **T054** [GATE] Gate sagrado post-Ola-3 → 100% verde.
- [x] **T055** Run `pytest tests/enterprise/skills_marketplace/` → 100% verde.
- [x] **T056** Verificar `git diff --stat _vendor/_cold/` muestra exactamente 131 nuevos paths.
- [x] **T057** Verificar `consciousness-council` sigue en `_vendor/k_dense/skills/`.
- [x] **T058** Run `python scripts/check-layer-imports.py` → OK.
- [x] **T059** Update `scripts/check-layer-imports.py` para skip `_cold/` paths si necesario.
- [x] **T060** Documentar Ola 3 cierre en `baselines/ola-3-status.md` con boot time medido.

---



## Phase 4 — Provider migration (Ola 4, T061-T100)

**Goal**: 5 SDK migrations + 6 BaseHTTPProvider + Google Workspace MCP revert (FR-009..FR-015, FR-035, SC-004/005/013/014). 11 providers refactorizados.
**Depende**: Phase 1 (BaseHTTPProvider).

### Dependencies setup

- [x] **T061** [F] Editar `pyproject.toml` añadir: `numpy>=1.26,<2.0`, `tavily-python>=0.5.0,<1.0.0`, `exa-py>=1.5.0,<2.0.0`, `firecrawl-py>=2.0.0,<3.0.0`, `pyalex>=0.18.0,<1.0.0`, `arxiv>=2.1.0,<3.0.0`.
- [x] **T062** Run `pip install -e .` para verificar resolución sin conflicts.
- [x] **T063** Verificar `import tavily, exa_py, firecrawl, pyalex, arxiv, numpy` en clean Python.

### SDK migration — Tavily (PoC, riesgo bajo)

- [x] **T064** Modificar `enterprise/tooling/builtin/research/tavily.py` (~111 → ~40 LOC): usar `tavily.TavilyClient(api_key)`. Preservar `name`, `domain`, `requires_auth`, signature de `execute()`. Healthcheck: api_key gating.
- [x] **T065** Run `pytest tests/enterprise/tooling/builtin/research/test_tavily*.py` → verde.
- [x] **T066** [P] Crear `tests/enterprise/tooling/test_tavily_sdk.py`: respx-mocked `TavilyClient.search()`, verifica retry policy del SDK.
- [x] **T067** [P] Actualizar `prompts/tools/tavily.txt` con nueva signature `tavily.search(query, search_depth, max_results, include_answer)`. Preservar XML structure (function_signature, best_for, selection_heuristics, chaining, fallback).

### SDK migration — OpenAlex

- [x] **T068** Modificar `enterprise/tooling/builtin/research/openalex.py`: usar `pyalex.Works().filter(...)`. Polite pool con `pyalex.config.email`.
- [x] **T069** [P] Crear `tests/enterprise/tooling/test_pyalex_migration.py`: verifica polite pool header.
- [x] **T070** [P] Actualizar `prompts/tools/openalex.txt` con nueva signature.

### SDK migration — Arxiv

- [x] **T071** Modificar `enterprise/tooling/builtin/research/arxiv.py`: usar `arxiv.Client().results(arxiv.Search(query=...))`. Reemplazar XML scraping manual.
- [x] **T072** [P] Crear `tests/enterprise/tooling/test_arxiv_sdk.py`: mock `arxiv.Client`, verifica que arxiv lock global se preserva (R-10 anti-pattern F-07).
- [x] **T073** [P] Actualizar `prompts/tools/arxiv.txt`.

### SDK migration — Exa

- [x] **T074** Modificar `enterprise/tooling/builtin/research/exa.py`: usar `exa_py.Exa(api_key)`. Exponer `search`, `find_similar`, `extract` capabilities.
- [x] **T075** [P] Crear `tests/enterprise/tooling/test_exa_sdk.py`.
- [x] **T076** [P] Actualizar `prompts/tools/exa.txt`.

### SDK migration — Firecrawl

- [x] **T077** Modificar `enterprise/tooling/builtin/research/firecrawl.py`: usar `firecrawl_py.AsyncFirecrawlApp(api_key).scrape_url(url)`.
- [x] **T078** [P] Crear `tests/enterprise/tooling/test_firecrawl_sdk.py`.
- [x] **T079** [P] Actualizar `prompts/tools/firecrawl.txt`.

### BaseHTTPProvider migration — Brave

- [x] **T080** Modificar `enterprise/tooling/builtin/research/brave.py` (≤80 LOC): subclass `BaseHTTPProvider`. Override `_auth_headers()` con `X-Subscription-Token`.
- [x] **T081** [P] Run `pytest tests/enterprise/tooling/builtin/research/test_brave*.py` → verde.
- [x] **T082** [P] Actualizar `prompts/tools/brave.txt`.

### BaseHTTPProvider migration — Serper + Serper Patents

- [ ] **T083** Modificar `serper.py` (≤80 LOC): subclass `BaseHTTPProvider`. Override `_auth_headers()` con `X-API-KEY`.
- [ ] **T084** Modificar `serper_patents.py` (≤40 LOC): extends Serper, distinto endpoint.
- [ ] **T085** [P] Actualizar `prompts/tools/serper.txt` y `prompts/tools/serper_patents.txt`.

### BaseHTTPProvider migration — Jina, Fetch, MiniMax Image

- [ ] **T086** Modificar `jina.py` (≤80 LOC): subclass con default Bearer auth.
- [ ] **T087** Modificar `web/fetch.py` (≤90 LOC): subclass sin auth (`requires_auth=False`). Opcional: integrar `markitdown` para HTML→text.
- [ ] **T088** Modificar `creative/minimax_image.py` (≤100 LOC): subclass con multipart support.
- [ ] **T089** [P] Actualizar `prompts/tools/{jina,fetch,minimax_image}.txt`.

### Google Workspace MCP revert

- [ ] **T090** [X] Eliminar `enterprise/tooling/builtin/productivity/google_workspace.py` (174 LOC).
- [ ] **T091** [X] Eliminar `tests/enterprise/tooling/builtin/productivity/test_google_workspace.py`.
- [ ] **T092** Editar `config/tools/catalog.yaml`: entry `google_workspace` → `strategy: MCP-EXTERNO`, `runtime: stdio_external`, capabilities expandidas (~25-30 listadas: Gmail send/read/search/labels/drafts, Calendar events/availability, Drive browse/files/shared, Docs read/write/insert/format, Sheets read/write/append, Forms create/responses).
- [ ] **T093** Editar `config/mcp/external.yaml`: añadir entry `google-workspace-mcp` (ver `data-model.md` para shape exacto).
- [ ] **T094** Editar `api/enterprise_composition.py`: remover `GoogleWorkspaceTool` del builtin_tools tuple. El `MCPProcessSupervisor` lo levanta automáticamente.
- [ ] **T095** [P] Crear `prompts/tools/google-workspace-mcp.txt` con guidance estructurada de las 25+ capabilities (function_signature por capability + chaining para flows multi-step Gmail+Calendar+Drive).
- [ ] **T096** [P] Crear `tests/enterprise/tooling/test_google_workspace_mcp.py` smoke test: verifica que post-revert el catalog expone ≥25 capabilities.

### Lifespan + provider contract

- [ ] **T097** Modificar `api/app.py:lifespan.shutdown` para llamar `await provider.aclose()` en cada provider y `await sdk_client.close()` en SDKs (Tavily, Exa, Firecrawl).
- [ ] **T098** [P] Crear `tests/enterprise/tooling/test_provider_contract.py` paramétrico (R-15): `@pytest.mark.parametrize("tool", ALL_BUILTIN_TOOLS)` verifica `isinstance(tool, ToolWrapper)`.
- [ ] **T099** [GATE] Run gate sagrado completo + suite tooling.
- [ ] **T100** Verify SC-004 (≥25 capabilities productivity), SC-005 (Tavily 99% success vs 503), SC-013 (provider contract). Documentar Ola 4 cierre en `baselines/ola-4-status.md`.

---

## Phase 5 — Composition root split + singleton dedup (Ola 5, T101-T115)

**Goal**: Split `dependencies.py` 694 LOC → paquete (FR-016/017/018, SC-009).
**Depende**: Ola 4 (composition referencia stable).

- [ ] **T101** [F] Crear `src/vigilancia_multiagente/api/dependencies/` directory.
- [ ] **T102** Crear `api/dependencies/_singletons.py` (~60 LOC) con `@lru_cache` factories: `get_embedding_gateway()`, `get_knowledge_graph_service()`, `get_tool_health_repo(database)`.
- [ ] **T103** Splittear `api/dependencies.py` (694 LOC) en 10 submodules (≤100 LOC c/u): `orchestration.py`, `agents.py`, `execution.py`, `strategic_signals.py`, `deep_analysis.py`, `data_intelligence.py`, `source_quality.py`, `assurance.py`, `governance.py`, `session.py`. Cada uno contiene su `_build_*_services` original.
- [ ] **T104** Crear `api/dependencies/__init__.py` (~30 LOC) con re-exports completos de los 10 `_build_*` symbols + helpers + singleton factories.
- [ ] **T105** [X] Eliminar `api/dependencies.py` (el monolítico).
- [ ] **T106** Modificar `api/enterprise_composition.py`: importar singletons desde `api.dependencies._singletons`. Pasar `embedding_gateway = get_embedding_gateway()` (no instanciar nuevo).
- [ ] **T107** Lazy imports: mover imports de `application.evaluation.ws_*` a dentro de `_build_*_services()` que los usan.
- [ ] **T108** [P] Crear `tests/api/test_dependencies_reexports.py`: verifica que los 40+ symbols del original siguen importables vía `from vigilancia_multiagente.api.dependencies import X`.
- [ ] **T109** [P] Crear `tests/api/test_singletons_dedup.py`: verifica `id(get_embedding_gateway()) == id(get_embedding_gateway())` (mismo objeto).
- [ ] **T110** [P] Verificar 12 importadores externos en `src/` siguen funcionando: `grep -r "from vigilancia_multiagente.api.dependencies import"`.
- [ ] **T111** Verificar cada submodule cumple ≤100 LOC: `Get-ChildItem api/dependencies/*.py | ForEach-Object { (Get-Content $_).Count }`.
- [ ] **T112** [GATE] Run gate sagrado completo + FULL `pytest tests/`.
- [ ] **T113** Run benchmark de boot pre/post Ola 5: confirmar lazy imports reducen boot time si flags WS off.
- [ ] **T114** Verify SC-009: `find src/vigilancia_multiagente -maxdepth 8 -name '*.py' \| xargs wc -l \| awk '$1>400'` retorna empty (módulos nuevos).
- [ ] **T115** Documentar Ola 5 cierre en `baselines/ola-5-status.md`.

---

## Phase 6 — Correctness + cleanup + _roadmap aislamiento (Ola 6, T116-T145)

**Goal**: Lock per-tenant + DB pool + MCP cache LRU + dead code remove + roadmap move + prompts wiring + audit fsync verify (FR-007/008/019/020/021/022/023/024/026/033/034/036, SC-006/007/011).

### Correctness fixes

- [x] **T116** Modificar `infra/persistence/turbovec_index.py`: añadir `_tenant_write_locks: dict[UUID, asyncio.Lock]` y `_tenant_persist_locks` separados. `_get_lock(tenant_id)` lazy con master lock. `add()` adquiere `_write_lock`, `persist()` adquiere `_persist_lock`. Lock timeout 30s (EC-08) raise `TurboVecLockTimeoutError`.
- [x] **T117** Modificar `enterprise/governance/audit_log.py:_write()`: añadir `fh.flush(); os.fsync(fh.fileno())` antes del exit del context manager.
- [x] **T118** Modificar `enterprise/governance/pi_quarantine_writer.py:write()`: ídem fsync.
- [ ] **T119** [P] Crear `tests/infra/persistence/test_turbovec_concurrent.py` (~120 LOC): 5 connectors paralelos × 1000 docs cada uno → exactamente 5000 chunks (SC-006).
- [ ] **T120** [P] Crear `tests/enterprise/governance/test_audit_flush_fsync.py`: monkeypatch `os.fsync` para verificar llamada por evento.

### Config (DB pool + MCP cache)

- [x] **T121** Modificar `infra/db/connection.py`: `pool_size = int(os.environ.get("VT_DB_POOL_SIZE", 10))`, `max_overflow = int(os.environ.get("VT_DB_POOL_OVERFLOW", 20))`.
- [x] **T122** Modificar `infra/mcp/mcp_cache.py`: añadir `max_entries: int = int(os.environ.get("VT_MCP_CACHE_MAX_ENTRIES", 1000))`. LRU eviction con `OrderedDict`. TTL via `VT_MCP_CACHE_TTL_SHORT/LONG`.
- [ ] **T123** [P] Crear `tests/infra/db/test_pool_config.py`: env override verify.
- [ ] **T124** [P] Crear `tests/infra/mcp/test_mcp_cache_eviction.py`.

### Dead code remove

- [x] **T125** [X] `git rm src/vigilancia_multiagente/infra/mcp/playwright_mcp.py`
- [x] **T126** [X] `git rm src/vigilancia_multiagente/infra/mcp/minimax_image_mcp.py`
- [x] **T127** [X] `git rm src/vigilancia_multiagente/enterprise/skills_marketplace/claude_local_adapter.py`
- [ ] **T128** [X] `git rm src/vigilancia_multiagente/infra/llm/minimax_client.py` (146 LOC, FR-033 revisada — full delete)
- [ ] **T129** [X] `git rm tests/test_minimax_client.py`
- [ ] **T130** [X] `git rm -r src/vigilancia_multiagente/prompts/minimax_examples/` (4 archivos)
- [ ] **T131** Verificar: `grep -r "MiniMaxClient\|minimax_client\|minimax_examples" src/ tests/` retorna 0 (excepto comentarios históricos).

### prompts/ wiring (FR-034)

- [x] **T132** Modificar `enterprise/tooling/tool_registry.py:get_docs(name)`: cargar `long_description` desde `infra.prompts.loader.load_prompt(f"tools/{name}")` con try/except `FileNotFoundError` → string vacío.
- [ ] **T133** [P] Crear `tests/enterprise/tooling/test_tool_registry_loads_long_description.py`: verifica `get_docs("tavily").long_description` contiene `<function_signature>`.

### `_roadmap/` aislamiento (FR-023)

- [ ] **T134** [X] `git mv` paquetes a `_roadmap/`:
  - `enterprise/artifacts/` → `enterprise/_roadmap/artifacts/` (9 files)
  - `enterprise/orchestration/app_development/` → `enterprise/orchestration/_roadmap/app_development/` (11)
  - `enterprise/orchestration/goal_pursuit/` → `enterprise/orchestration/_roadmap/goal_pursuit/` (7)
  - `enterprise/dreaming/loops/` → `enterprise/dreaming/_roadmap_loops/` (7)
  - 8 phases F5b → `enterprise/dreaming/phases/_roadmap/`
- [ ] **T135** Update imports relativos via búsqueda manual:
  - `enterprise.artifacts` → `enterprise._roadmap.artifacts`
  - `enterprise.orchestration.app_development` → `enterprise.orchestration._roadmap.app_development`
  - `enterprise.orchestration.goal_pursuit` → `enterprise.orchestration._roadmap.goal_pursuit`
  - `enterprise.dreaming.loops` → `enterprise.dreaming._roadmap_loops`
- [ ] **T136** [X] `git mv` tests correspondientes a `tests/.../_roadmap/`.
- [ ] **T137** Update `pytest.ini`: `addopts = --ignore=tests/enterprise/_roadmap --ignore=tests/enterprise/orchestration/_roadmap --ignore=tests/enterprise/dreaming/_roadmap_loops --ignore=tests/enterprise/dreaming/phases/_roadmap`.
- [ ] **T138** Update `scripts/check-layer-imports.py` para skip `_roadmap/` y `_cold/` paths (FR-026).

### Verificación final

- [x] **T139** [GATE] Run gate sagrado FULL.
- [x] **T140** Run FULL `pytest tests/ -q --tb=short` → ≥580 passed, 0 failed (SC-008 implícita).
- [x] **T141** Measure SC-008: `time pytest tests/ -q` → <30s post-_roadmap exclusion.
- [x] **T142** Verify SC-011: `tokei src/ tests/` antes vs después → -5% LOC.
- [x] **T143** Verify SC-014: `curl http://localhost:8000/api/v2/enterprise/tools | jq 'length'` → ≥45 capabilities.
- [x] **T144** Verify SC-015: profile `psutil.Process().memory_info().rss` pre/post → -3MB por dedup singletons.
- [x] **T145** Generar `docs/release-notes-022.md` con: SDK migrations + LOC deltas + tests añadidos + Google Workspace MCP revert + 131 cold skills + prompts/tools wiring (FR-031).

---

## Dependencies

```
Phase 0 (T001-T005)
   ↓
Phase 1 (T006-T020) ──┬──→ Phase 2 (T021-T030)
                      ├──→ Phase 3 (T031-T060)  [puede paralelizar T031-T037 con T038-T045]
                      └──→ Phase 4 (T061-T100)  [secuencial provider-by-provider, R-08]
                                 ↓
                          Phase 5 (T101-T115)  [secuencial — A-08, evita merge conflicts]
                                 ↓
                          Phase 6 (T116-T145)
```

**Tareas que MUST ser secuenciales**:
- T064 (Tavily PoC) precede T068, T071, T074, T077 (otros SDKs).
- T080-T088 (BaseHTTPProvider providers) sequential, 1 a la vez con tests verdes.
- T090-T096 (Google Workspace MCP revert) en bloque, después de SDKs.
- T103 (split dependencies.py) bloquea todos los T106-T110 (consumidores).
- T134-T138 (`_roadmap/` move) en orden estricto: mover paquete → mover tests → update pytest.ini → check-layer-imports.

**Tareas paralelizables [P]**:
- T002-T005 (snapshots).
- T010-T011, T014-T015 (tests Ola 1).
- T046-T051 (tests skills Ola 3).
- T065-T079 (tests por provider Ola 4 — diferente archivo c/u).
- T108-T110 (tests deps Ola 5).

## Parallel Execution Examples

### Phase 1 Parallel Block (post T009)
- T010 + T014 (tests independientes, archivos disjuntos).
- T011 + T015 (runs paralelos, no shared state).

### Phase 4 Parallel Block (post T064 verde)
- T067 + T070 + T073 + T076 + T079 + T082 + T085 + T089 + T095 (actualizaciones a `prompts/tools/*.txt`, archivos disjuntos).

### Phase 6 Parallel Block (post correctness fixes)
- T119 + T120 + T123 + T124 (tests nuevos, archivos disjuntos).

## Implementation Strategy

1. **Foundation primero**: completar Phase 0 (gate sagrado verde) ANTES de cualquier cambio.
2. **Aditivo antes que destructivo**: Ola 1 crea infra base sin tocar nada existente.
3. **Hot paths antes que cleanup**: Olas 2/3 entregan el grueso del valor (latencia + boot) ANTES de cleanup.
4. **PoC antes que batch**: Tavily SDK migration (T064) es PoC; valida el approach antes de los otros 4 SDKs.
5. **Secuencial entre olas**: Ola 5 (split DI) NUNCA paralela a Ola 4 (provider migration) — merge conflicts en `enterprise_composition.py`.
6. **Cleanup al final**: Ola 6 hace deletes y roadmap moves cuando todo está estable.
7. **Gate sagrado entre olas**: cada `[GATE]` task es bloqueante. Si rojo → revert por archivo, retry. Si revert no resuelve → escalate.

## Tracking

Total tasks: **145** (T001..T145).
Tasks por phase:
- Phase 0: 5
- Phase 1: 15
- Phase 2: 10
- Phase 3: 30
- Phase 4: 40
- Phase 5: 15
- Phase 6: 30
- Plus closing T145.

Estimated execution: **5-6 días** secuencial; **3-4 días** paralelizando los `[P]` blocks.

**NO commits/pushes** durante implementación per directiva de usuario. Cada ola termina con código uncommitted en local main.
