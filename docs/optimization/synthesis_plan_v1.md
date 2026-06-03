# Síntesis de Optimización — Plan Ejecutable v1.0

**Fecha**: 2026-06-01  
**Scope**: Backend Vigilador 3.0 — Spec 021 MVP  
**Constraints**: Constitución v1.2.0 · 2.0 PRESERVADO · D1-D4 · basedpyright-standard

---

## A. Plan de Olas (6 olas → reemplaza W1-W4 original)

### Ola 1 — Infraestructura Base (sin cambio de comportamiento)

**Objetivo**: Crear `BaseHTTPProvider` + `BufferedJSONLWriter` + embedding LRU cache. Cero cambio en providers existentes.

| Atributo | Valor |
|----------|-------|
| Dependencias | Ninguna (ola raíz) |
| LOC añadido | +280 (3 archivos nuevos) |
| LOC quitado | 0 |
| Archivos nuevos | `enterprise/tooling/builtin/_base_http.py` (~180), `enterprise/governance/_buffered_writer.py` (~60), `infra/embeddings/_lru_cache.py` (~40) |
| Tests al final | `pytest tests/enterprise/tooling/ tests/enterprise/governance/ -x` + nuevos unit tests para BaseHTTPProvider (respx mock 503→200, retry, timeout) + test BufferedJSONLWriter (flush on threshold) + test LRU cache (hit/miss/eviction) |
| Rollback | Borrar 3 archivos. Nada depende de ellos aún. |
| Riesgo | **Bajo** — código aditivo, sin tocar existente |

---

### Ola 2 — Eliminar N+1 en ToolRegistry.discover()

**Objetivo**: Pre-computar embeddings de tool descriptions en `register()` y batch `_get_status()` en una sola query. Latencia discover() de ~2-7s → <200ms.

| Atributo | Valor |
|----------|-------|
| Dependencias | Ola 1 (usa `_lru_cache.py`) |
| LOC añadido | +50 |
| LOC quitado | -15 (loop de embed en discover) |
| Archivos tocados | `enterprise/tooling/tool_registry.py` (~30 LOC delta), `enterprise/tooling/tool_health_repository.py` (+20 LOC método `get_statuses_batch`) |
| Tests al final | `pytest tests/enterprise/tooling/test_tool_registry.py tests/enterprise/tooling/test_f1_native_first_runtime.py tests/enterprise/governance/test_tool_gating_credentials.py` + nuevo benchmark: `test_discover_latency_under_500ms` |
| Rollback | Revert 2 archivos. `_tool_embeddings` dict es backward-compatible (discover() fallback a embed on-the-fly si dict vacío). |
| Riesgo | **Medio** — cambia hot path de discover(). Si embeddings pre-computados difieren en orden de resultados, puede afectar tool selection. Mitigación: test de golden output con intent fijo. |

---

### Ola 3 — Skills Boot Optimization

**Objetivo**: Reducir boot de skills de ~30-90s a ~3-5s. Embedding disk-cache + HashTracker batch-save + frontmatter-only read.

| Atributo | Valor |
|----------|-------|
| Dependencias | Ola 1 (usa `_lru_cache.py` para embed gateway) |
| LOC añadido | +90 |
| LOC quitado | -20 (eliminar save() por skill en HashTracker) |
| Archivos tocados | `enterprise/skills_marketplace/skill_registry.py` (+40 LOC disk cache logic), `enterprise/skills_marketplace/hash_tracker.py` (+10 LOC `save_all()`, -20 LOC per-skill save), `enterprise/skills_marketplace/adapters/k_dense_adapter.py` (+25 LOC frontmatter-only read), `enterprise/skills_marketplace/adapters/agency_agents_adapter.py` (+15 LOC ídem) |
| Tests al final | `pytest tests/enterprise/skills_marketplace/` completo (6+10+8+catalog+validator = ~30 tests) + nuevo: `test_boot_uses_cached_embeddings`, `test_hash_tracker_batch_save` |
| Rollback | Revert 4 archivos. Si cache corrupto → boot recalcula todo (fallback implícito). |
| Riesgo | **Medio** — cambio en adapters afecta parsing de frontmatter. Si regex falla en edge case (frontmatter con `---` en body), skill no se carga. Mitigación: test con skill real de 2MB (timesfm). |

---

### Ola 4 — Provider Migration a BaseHTTPProvider

**Objetivo**: Migrar 11 providers httpx a BaseHTTPProvider. Ganan: connection pooling, retries, error unificado. ~46% reducción LOC promedio.

| Atributo | Valor |
|----------|-------|
| Dependencias | Ola 1 (BaseHTTPProvider existe) |
| LOC añadido | +130 (11 subclases ~12 LOC c/u) |
| LOC quitado | -520 (eliminar httpx boilerplate de 11 providers) |
| Archivos tocados | `enterprise/tooling/builtin/research/{tavily,brave,exa,jina,firecrawl,serper,serper_patents,openalex,arxiv,google_scholar}.py` + `enterprise/tooling/builtin/web/fetch.py` |
| Tests al final | `pytest tests/enterprise/tooling/` + contract test (13 tools satisfy ToolWrapper Protocol) + nuevo: `test_base_http_retry_on_503`, `test_connection_reuse` (respx) |
| Rollback | Revert individual por provider. Orden: Tavily primero (PoC), luego batch. Cada provider es independiente. |
| Riesgo | **Medio** — 11 archivos tocados. Riesgo principal: providers con auth patterns no-estándar (Tavily=body key, Brave=custom header, OpenAlex=User-Agent). Mitigación: cada provider tiene `_auth_headers()` override. Test por provider con respx mock. |

---

### Ola 5 — Composition Root Split + Singleton Dedup

**Objetivo**: Split `dependencies.py` → paquete `api/dependencies/`. Eliminar 3 duplicaciones de servicios. Cero cambio de imports externos.

| Atributo | Valor |
|----------|-------|
| Dependencias | Ninguna técnica (puede ejecutarse en paralelo con Ola 4), pero lógicamente después para reducir conflictos de merge |
| LOC añadido | +625 (11 archivos del paquete) |
| LOC quitado | -580 (dependencies.py original) |
| Archivos tocados | `api/dependencies.py` → `api/dependencies/__init__.py` + 10 submodules. `enterprise_composition.py` (-5 LOC, recibe embedding_gateway como param). `app.py` (-3 LOC, pasa embedding_gateway). |
| Tests al final | `pytest tests/` COMPLETO (full suite). Verificar que 12 archivos consumidores + `tests/test_orchestrator.py` siguen importando sin error. |
| Rollback | Revert: renombrar `api/dependencies/` back a `api/dependencies.py` (el __init__.py ES el archivo original con re-exports). |
| Riesgo | **Bajo** — Python trata file→package como transparente. Único riesgo: si algún import hace `importlib.import_module("vigilancia_multiagente.api.dependencies")` con expectativa de `.py` file. Verificar con grep. |

---

### Ola 6 — Caching, Pooling & Correctness Fixes

**Objetivo**: Integrar cache en ToolRegistry.execute(), configurar DB pool, añadir lock a TurboVecIndex, buffer AuditLog/PIQuarantine.

| Atributo | Valor |
|----------|-------|
| Dependencias | Ola 1 (BufferedJSONLWriter), Ola 4 (providers ya usan BaseHTTPProvider para que cache sea efectivo) |
| LOC añadido | +85 |
| LOC quitado | -30 (inline writes en audit_log/pi_quarantine) |
| Archivos tocados | `enterprise/tooling/tool_registry.py` (+15 LOC cache check en execute), `infra/db/connection.py` (+5 LOC pool params), `infra/persistence/turbovec_index.py` (+10 LOC asyncio.Lock), `enterprise/governance/audit_log.py` (+20 LOC usar BufferedJSONLWriter), `enterprise/governance/pi_quarantine_writer.py` (+15 LOC ídem), `infra/mcp/mcp_cache.py` (+20 LOC max_entries LRU) |
| Tests al final | `pytest tests/` COMPLETO + nuevo: `test_tool_execute_cache_hit`, `test_turbovec_concurrent_add_safe`, `test_audit_log_flush_on_shutdown`, `test_mcp_cache_eviction` |
| Rollback | Cada fix es independiente. Revert por archivo. Cache en execute() tiene flag `cache_enabled` en Settings para disable rápido. |
| Riesgo | **Medio** — TurboVecIndex lock puede introducir deadlock si `persist()` se llama dentro de `add()` context. Mitigación: lock granular (separate lock for add vs persist). AuditLog buffer: si crash antes de flush, se pierden últimos eventos. Mitigación: flush cada 5s + atexit handler. |

---

### Resumen de Olas

```
Ola 1 ──────┐
             ├──→ Ola 2 (tool discover N+1)
             ├──→ Ola 3 (skills boot)
             └──→ Ola 4 (provider migration)
                          │
Ola 5 (split DI) ────────┤  (paralela a Ola 4)
                          │
                          └──→ Ola 6 (cache + correctness)
```

**Timeline estimado**: Ola 1 (1 día) → Olas 2,3,4 paralelas (2-3 días) → Ola 5 (1 día) → Ola 6 (1 día). **Total: 5-6 días de trabajo.**

---

## B. Tabla Integrada de Oportunidades

| ID | Título | Track | Impacto Esperado | Esfuerzo | Prerequisito | Ola |
|----|--------|-------|------------------|----------|--------------|-----|
| O-01 | BaseHTTPProvider (connection pooling + retries) | providers | -520 LOC, -150ms/call TLS overhead, +resiliencia 5xx | M | — | 1+4 |
| O-02 | ToolRegistry.discover() pre-compute embeddings | perf | -2-7s latencia/query → <200ms | S | O-03 | 2 |
| O-03 | Embedding LRU cache en GeminiEmbeddingGateway | perf | -100-300ms por embed repetido, ~12MB RAM | S | — | 1 |
| O-04 | Batch `_get_status()` → single SQL query | perf | -21 DB round-trips/discover → 1 | S | — | 2 |
| O-05 | Skill embedding disk-cache | skills | -30-90s boot → ~3-5s | M | O-03 | 3 |
| O-06 | HashTracker batch-save | skills | -500ms boot (311 writes → 1) | S | — | 3 |
| O-07 | Frontmatter-only read en adapters | skills | -15MB peak RAM, -200-400ms boot | S | — | 3 |
| O-08 | Mover skills non-MVP a `_cold/` | skills | -100-200ms boot, -3-5MB RAM | S | Decisión usuario (E-03) | 3 |
| O-09 | dependencies.py → paquete split | wiring | +ergonomía (≤70 LOC/file), -0 runtime | M | — | 5 |
| O-10 | Eliminar 3 duplicaciones (EmbeddingGW, KnowledgeGraph, ToolHealthRepo) | wiring | -3 instancias innecesarias, ~-2MB RAM | S | O-09 | 5 |
| O-11 | BufferedJSONLWriter (AuditLog + PIQuarantine) | perf | -20-200ms IO blocking/session | S | — | 1+6 |
| O-12 | TurboVecIndex per-tenant asyncio.Lock | perf | Correctness fix (no perf gain) | S | — | 6 |
| O-13 | DB pool configurable via env | perf | +headroom bajo carga (5→10 conns) | S | — | 6 |
| O-14 | MCP cache max_entries + env TTL config | perf | Previene OOM en sesiones largas | S | — | 6 |
| O-15 | Cache en ToolRegistry.execute() (reuse MCPSmartCache) | providers+perf | -latencia queries repetidos (TTL-based) | S | O-01 | 6 |
| O-16 | Pass skip-set a adapters (filter before read) | skills | Future-proof (0 impacto hoy, disabled=[]) | S | O-08 | 3 |
| O-17 | `@lru_cache` singletons (EmbeddingGW, KnowledgeGraph, PromptLoader) | wiring | -instancias duplicadas cross-composition | S | — | 5 |
| O-18 | Lazy imports en dependencies (WS factories) | wiring | -boot time si WS flags disabled | S | O-09 | 5 |
| O-19 | Wire BaseHTTPProvider.close() en FastAPI lifespan | providers | Graceful shutdown, no leaked connections | S | O-01 | 4 |
| O-20 | Gemini batchEmbedContents endpoint | perf | -N requests → 1 request (batch 100 texts) | M | Investigar API | Futura |

---

## C. Riesgos Consolidados

### Riesgos por Track

| ID | Riesgo | Track(s) | Probabilidad | Impacto | Mitigación |
|----|--------|----------|--------------|---------|------------|
| R-01 | Provider refactor cambia response shape → downstream breakage | providers | Baja | Alto | Contract tests por provider. Golden output fixtures. |
| R-02 | BaseHTTPProvider singleton client leak en tests (client no se cierra entre tests) | providers+perf | Media | Medio | `@pytest.fixture(autouse=True)` que llama `close()` after each test module. |
| R-03 | Embedding cache stale → discover() retorna tools/skills incorrectos | perf+skills | Baja | Alto | Cache key incluye content hash. Invalidación automática si hash cambia. |
| R-04 | dependencies.py split rompe import circular | wiring | Baja | Alto | Topological order ya verificado. Lazy imports en WS factories. |
| R-05 | TurboVecIndex lock introduce deadlock | perf | Baja | Alto | Lock granular: `_write_lock` separado de `_persist_lock`. No nested acquisition. |
| R-06 | AuditLog buffer pierde eventos en crash | perf | Media | Medio | Flush cada 5s + `atexit` handler + flush en FastAPI shutdown. Aceptable para MVP. |
| R-07 | Frontmatter-only read falla en skills con `---` en body antes del cierre | skills | Baja | Bajo | Regex busca `^---$` (line-start). Test con edge cases. |
| R-08 | Mover skills a `_cold/` rompe `test_load_real_kdense_marketplace` | skills | Media | Bajo | Dejar ≥1 skill en path activo. Test ya tiene `>= 1` assertion. |
| R-09 | DB pool size increase causa memory pressure en entornos limitados | perf | Baja | Bajo | Configurable via env. Default conservador (10). |
| R-10 | arxiv global lock sigue serializando queries concurrentes post-refactor | perf | Alta | Medio | Fuera de scope MVP (arXiv policy). Documentar como known limitation. |

### Riesgos Cruzados (inter-track)

| Riesgo Cruzado | Tracks Involucrados | Descripción |
|----------------|--------------------|----|
| **RC-01** | providers × perf | Si BaseHTTPProvider introduce retry delays (backoff), el cache TTL en execute() puede servir respuestas stale mientras el provider está en retry. Mitigación: cache solo en success, no en timeout. |
| **RC-02** | wiring × providers | Split de dependencies.py ocurre mientras providers se refactorizan → merge conflicts. Mitigación: Ola 5 después de Ola 4, o en paralelo con archivos disjuntos. |
| **RC-03** | skills × perf | Embedding disk-cache (skills) + LRU cache (gateway) = doble capa de cache. Si gateway LRU tiene el embedding, disk-cache nunca se consulta → disk-cache se vuelve write-only overhead. Mitigación: disk-cache es cold-start only; LRU es hot-path. Complementarios, no redundantes. |
| **RC-04** | providers × wiring | Eliminar duplicación de EmbeddingGateway (wiring) mientras providers la usan para healthcheck → timing de cambio importa. Mitigación: singleton `@lru_cache` es transparente para consumidores. |

---

## D. Plan de Testing por Ola

### Tests Baseline (NUNCA deben romperse — gate obligatorio pre/post cada ola)

```bash
# GATE SAGRADO — ejecutar antes Y después de cada ola
pytest tests/test_orchestrator.py                           # 2.0 core
pytest tests/application/execution/                         # branch_coordinator (NO TOCAR)
pytest tests/application/evaluation/                        # ws_* evaluators (NO TOCAR)
pytest tests/enterprise/governance/test_audit_log*.py       # audit_log core
pytest tests/enterprise/dispatch/                           # dispatcher
pytest tests/api/routes/test_research_*.py                  # /api/v2/research/* (NO TOCAR)
```

### Tests por Ola

| Ola | Tests PRE (baseline) | Tests POST (baseline + nuevos) | Tests Nuevos a Crear |
|-----|---------------------|-------------------------------|---------------------|
| 1 | Gate sagrado | Gate sagrado + unit tests nuevos | `test_base_http_provider.py` (retry, timeout, pooling), `test_buffered_writer.py` (flush triggers), `test_embedding_lru.py` (hit/miss/evict) |
| 2 | Gate sagrado + `tests/enterprise/tooling/` | Ídem + benchmark | `test_discover_precomputed_embeddings.py`, `test_get_statuses_batch.py` |
| 3 | Gate sagrado + `tests/enterprise/skills_marketplace/` | Ídem + boot timing | `test_skill_embedding_disk_cache.py`, `test_hash_tracker_batch.py`, `test_frontmatter_only_read.py` |
| 4 | Gate sagrado + `tests/enterprise/tooling/` + `tests/enterprise/governance/test_tool_gating*` | Ídem + contract | `test_provider_contract.py` (13 tools × ToolWrapper Protocol), `test_tavily_refactored.py`, `test_brave_refactored.py` (etc.) |
| 5 | Gate sagrado + FULL `pytest tests/` | Ídem (no tests nuevos, solo verificar imports) | `test_dependencies_reexports.py` (verify all 40 symbols importable from package) |
| 6 | Gate sagrado + FULL `pytest tests/` | Ídem + correctness | `test_turbovec_concurrent.py`, `test_execute_cache.py`, `test_mcp_cache_eviction.py`, `test_audit_flush_shutdown.py` |

### Comando de Gate Sagrado (copiar/pegar)

```bash
pytest tests/test_orchestrator.py tests/application/execution/ tests/application/evaluation/ tests/enterprise/governance/test_audit_log*.py tests/enterprise/dispatch/ tests/api/routes/test_research_*.py -x --tb=short
```

---

## E. Decisiones que Requieren Input del Usuario

| # | Decisión | Contexto | Opciones | Impacto si no se decide |
|---|----------|----------|----------|------------------------|
| **E-01** | ¿Migrar Tavily/Exa/Firecrawl a SDK oficial? | Track 1 recomienda keep_httpx. SDKs son thin wrappers. | A) keep_httpx (recomendado) B) migrar a SDK | Bloqueante para Ola 4 si se elige B (cambia approach completo) |
| **E-02** | ¿TTL del MCP cache configurable via env? ¿Valores default? | Actualmente hardcoded 30min-7d. | A) Mantener hardcoded B) Env vars `VT_MCP_CACHE_TTL_DEFAULT=1800` | No bloqueante. Default actual funciona. |
| **E-03** | ¿Qué skills mover a `_cold/`? ¿Lista exacta de 15 non-MVP? | 15 candidatos identificados (clinical, neuro, chemistry). | A) Mover los 15 listados B) Solo clinical (8) C) No mover ninguno | Afecta boot time ~100-200ms. No crítico pero limpia vendor. |
| **E-04** | ¿Embedding disk-cache path? `~/.vigilador/` vs project-local | Skills usa `~/.vigilador/skills/`. Consistente sería `~/.vigilador/cache/embeddings/`. | A) `~/.vigilador/cache/embeddings/` B) `.cache/` en project root | Afecta portabilidad y gitignore. |
| **E-05** | ¿AuditLog buffer: aceptable perder últimos ~5s de eventos en crash? | Buffer flush cada 5s. Hard crash = pérdida. | A) Aceptable para MVP B) Flush síncrono cada evento (status quo) C) Flush cada 1s | Trade-off: performance vs durabilidad de audit trail. |
| **E-06** | ¿DB pool size default? | Actual: 5 (SQLAlchemy default). Propuesto: 10. | A) 10 pool + 20 overflow B) 15 pool + 30 overflow C) Mantener 5 | Afecta memory footprint (~5MB por conexión extra). |
| **E-07** | ¿Usar Gemini `batchEmbedContents` endpoint? | Reduciría 311 calls → ~4 calls (batch de 100). Requiere verificar API compatibility. | A) Implementar batch real B) Mantener `asyncio.gather` con batches de 16 | Diferencia: 4 requests vs 20 requests en boot. Ambos mejoran sobre 311. |
| **E-08** | ¿Orden de ejecución Ola 4 vs Ola 5? ¿Paralelo o secuencial? | Archivos disjuntos pero merge conflicts posibles si se trabaja en paralelo. | A) Secuencial (4→5) B) Paralelo (ramas separadas) | Riesgo de conflictos en `enterprise_composition.py` si paralelo. |
| **E-09** | ¿Añadir `numpy` como dependencia para cosine similarity vectorizado? | Actualmente pure-Python. 311 skills × 768-dim = ~720K float ops por discover(). | A) Añadir numpy B) Mantener pure-Python (suficiente para 311 skills) | <5ms diferencia con 311 skills. Solo relevante si skills > 1000. |

---

## F. Anti-patterns Identificados (NO arreglar)

| # | Parece optimización pero... | Por qué NO hacerlo |
|---|----------------------------|-------------------|
| **F-01** | Reemplazar `scholarly` por scraping directo de Google Scholar | Viola KISS. `scholarly` maneja captchas, proxies, parsing. Reimplementar = meses de mantenimiento. |
| **F-02** | Hacer `dependencies.py` lazy con `__getattr__` module-level | Rompe basedpyright type-checking. Los 12 consumidores perderían autocompletado. Viola Constitución (explicit > implicit). |
| **F-03** | Cachear resultados de `branch_coordinator` entre sesiones | Viola spec: cada research session es independiente. Cross-session memory es explícita via `global_knowledge_repository`, no cache implícito. |
| **F-04** | Eliminar `MCPSmartCache` y usar solo el cache de `ToolRegistry.execute()` | Son capas distintas: MCPSmartCache es para MCP external tools (stdio), ToolRegistry cache es para builtin tools. Unificar perdería granularidad de TTL. |
| **F-05** | Mover `_vendor/` fuera del source tree a un package instalable | Viola D2/D3: vendor DEBE estar en `src/...skills_marketplace/_vendor/`. Spec explícito. |
| **F-06** | Hacer SkillRegistry.discover() sync (eliminar await) | El embed() call es async (network). Forzar sync bloquearía event loop. |
| **F-07** | Eliminar `arxiv._request_lock` para permitir queries paralelas | arXiv rate-limita agresivamente (ban IP). El lock es protección intencional. Relajar = ban en producción. |
| **F-08** | Reemplazar `threading.Lock` por `asyncio.Lock` en MCPSmartCache | El Lock actual es correcto: operaciones son O(1) dict lookups, GIL protege, y el cache se usa desde contextos mixtos (sync callers en WS evaluators). Cambiar a asyncio.Lock rompería callers sync. |
| **F-09** | Pre-cargar TODOS los skill bodies en RAM para discover() más rápido | discover() no usa body (solo embeddings). Cargar 42MB de markdown en RAM sin uso = waste. El body se carga on-demand via `get_body()`. |
| **F-10** | Consolidar los 6 agentes de rama en un agente genérico parametrizado | Viola constraint sagrado: NO tocar los 6 agentes de rama. Además viola SRP (cada agente tiene lógica de dominio distinta). |

---

## Apéndice: Métricas de Éxito por Ola

| Ola | Métrica Clave | Valor Actual (estimado) | Target |
|-----|---------------|------------------------|--------|
| 1 | Tests nuevos passing | 0 | ≥12 tests green |
| 2 | Latencia discover() | 2-7s | <200ms |
| 3 | Boot time (skills) | 30-90s | <5s |
| 4 | LOC total providers | ~1,350 | ~830 (-39%) |
| 5 | Max LOC/file en dependencies | ~580 | ≤70 |
| 6 | Concurrent ingestion correctness | Bug (no lock) | 0 data corruption |

---

## Apéndice: Datos Insuficientes

| Dato Faltante | Track | Cómo Obtener |
|---------------|-------|--------------|
| Latencia real de embed() a Gemini API en entorno de producción | perf | `time.perf_counter()` wrapper + 10 calls reales. `VT_EMBED_LATENCY_LOG=1` env flag. |
| Número exacto de discover() calls por sesión de research típica | perf | Añadir counter en ToolRegistry. Correr 1 sesión completa de technology-watch. |
| Tamaño real del MCP cache después de 1 semana de uso | perf | `mcp_cache.size` endpoint o log periódico. |
| ¿`embed_documents()` ya usa `batchEmbedContents` internamente? | perf | Leer `infra/embeddings/gemini_gateway.py` método `embed_documents()` — track 4 indica que NO, pero verificar con Gemini API docs. |
| ¿Hay tests de integración con API keys reales en CI? | providers | Revisar CI config (`.github/workflows/` o equivalente). Si no existen, los smoke tests de Ola 4 serían los primeros. |
