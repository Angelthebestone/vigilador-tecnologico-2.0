# Data Model: Backend Optimization 022

**Phase 1 output**. Entidades y estructuras introducidas/modificadas por este spec.

## Nuevas entidades

### BaseHTTPProvider (clase base)

**Path**: `src/vigilancia_multiagente/enterprise/tooling/builtin/_base/http_provider.py`

| Atributo | Tipo | Origen | Uso |
|---|---|---|---|
| `name` | `ClassVar[str]` | Subclass override | Identificador en ToolRegistry |
| `domain` | `ClassVar[str]` | Subclass override | "search", "research", "web", etc. |
| `base_url` | `ClassVar[str]` | Subclass override | Root URL del provider |
| `auth_env_var` | `ClassVar[str \| None]` | Subclass override | Env var de la API key |
| `requires_auth` | `ClassVar[bool]` | Default `True` | Gating en healthcheck |
| `_client` | `httpx.AsyncClient \| None` | Lazy init | Connection pool reusable |
| `_retry_policy` | `RetryPolicy` | __init__ | 3 attempts, exponential backoff |

**Estados del cliente**:
- `closed` → `open` (primer request) → `closed` (aclose() en lifespan.shutdown).
- Re-open lazy si tras `aclose()` se llama otro método (defensive).

**Operaciones (CQS)**:
- Commands: `post()`, `get()`, `aclose()`, `_auth_headers()` (override).
- Queries: `_api_key()`, `healthcheck()`.

### EmbeddingCache (two-tier)

**Path**: `src/vigilancia_multiagente/infra/embeddings/embedding_cache.py`

| Componente | Tipo | Tamaño | Persistencia |
|---|---|---|---|
| L1 (memory) | `OrderedDict[str, list[float]]` | `max_entries=1000` | RAM |
| L2 (disk) | `dict[str, list[float]]` JSON | unlimited | `~/.vigilador/cache/embeddings/{tools,skills}.json` |
| Index | `dict[str, str]` (content_hash → vector_key) | en memoria | computado en boot |

**Cache key**: `sha256(content_text[:4096]).hexdigest()[:16]`.

**Estados**:
- `cold` (boot, L1 empty, L2 leído de disk).
- `warm` (operación normal, L1 con hits/misses, L2 read-only).
- `flush_pending` (al finalizar register de tools/skills, L2 batch-saved).

**Operaciones**:
- `get(content: str) -> list[float] | None` (query, no side effects).
- `set(content: str, vector: list[float]) -> None` (command, may evict L1).
- `flush_to_disk()` (command, batch save L2).
- `load_from_disk()` (command, boot init).

### ProviderUnconfiguredError

**Path**: `src/vigilancia_multiagente/enterprise/tooling/builtin/_base/http_provider.py`

```python
class ProviderUnconfiguredError(RuntimeError):
    """Raised when BaseHTTPProvider is invoked without required api_key."""
```

**Uso**: BaseHTTPProvider.post/get verifican api_key. Si falta y `requires_auth=True`, raise. ToolRegistry.execute lo cataloga como "error" en audit_log + propaga.

### MCPSmartCacheLRU (extensión)

**Path**: `src/vigilancia_multiagente/infra/mcp/mcp_cache.py` (modificación)

| Atributo nuevo | Tipo | Default | Origen |
|---|---|---|---|
| `max_entries` | `int` | `int(os.environ.get("VT_MCP_CACHE_MAX_ENTRIES", 1000))` | Env config |
| `ttl_short_s` | `int` | `int(os.environ.get("VT_MCP_CACHE_TTL_SHORT", 1800))` | Env config |
| `ttl_long_s` | `int` | `int(os.environ.get("VT_MCP_CACHE_TTL_LONG", 604800))` | Env config |

**Estado interno**: `OrderedDict[key, _CacheEntry]`. LRU eviction cuando `len > max_entries`.

## Entidades modificadas

### ToolRegistry

**Path**: `src/vigilancia_multiagente/enterprise/tooling/tool_registry.py`

| Atributo | Cambio |
|---|---|
| `_embedding_cache: EmbeddingCache` | NUEVO (inyectado en __init__) |
| `_tool_embeddings: dict[str, list[float]]` | NUEVO (in-memory cache de embeddings ya pre-computados) |

**Cambio comportamiento**:
- `register()`: ahora pre-computa embedding de description vía `embedding_gateway.embed(description)` y guarda en `_tool_embeddings[name]` + `_embedding_cache.set(content_hash, vec)`.
- `discover()`: lee `_tool_embeddings` (no embed) + 1 batch SQL via `tool_health_repo.get_statuses_batch(names)`.

### SubagentRegistry, ComplexityClassifier, AuditLog, PIQuarantineWriter

**Sin cambios estructurales**. Solo la implementación interna de los writers añade `os.fsync()` (FR-020/FR-021) — verificación, ya que el código actual `with open(append) as fh: fh.write(line)` ya delega flush al close del context manager. La adición explícita de `fh.flush(); os.fsync(fh.fileno())` antes del exit garantiza durabilidad anti-SIGKILL.

### TurboVecIndex

**Path**: `src/vigilancia_multiagente/infra/persistence/turbovec_index.py`

| Atributo | Cambio |
|---|---|
| `_tenant_write_locks: dict[UUID, asyncio.Lock]` | NUEVO |
| `_tenant_persist_locks: dict[UUID, asyncio.Lock]` | NUEVO |
| `_locks_master: asyncio.Lock` | NUEVO (protege creation lazy de los dicts) |

**State machine de un tenant_id**:
```
init → idle → write (acquired _write) → idle
                  ↘ persist (acquired _persist) → idle
```

`_write` y `_persist` son locks **independientes**: una operación puede `add()` (write_lock) mientras otra hace `persist()` (persist_lock) — no deadlock.

### Catalog & MCP manifest

**Path**: `config/tools/catalog.yaml`

Entry `google_workspace` cambia:
| Campo | Antes | Después |
|---|---|---|
| `strategy` | `WRAP-SDK` | `MCP-EXTERNO` |
| `runtime` | `python_internal` | `stdio_external` |
| `capabilities` | `[read_docs, write_docs, read_sheets, send_email]` (4) | Listado expandido (~25-30) |
| `source_repo` | `https://github.com/nicholishen/google-workspace-mcp` | `https://github.com/taylorwilsdon/google-workspace-mcp` (verify) |

**Path**: `config/mcp/external.yaml`

```yaml
mcps:
  - name: google-workspace-mcp
    command: npx
    args: ["-y", "@taylorwilsdon/google-workspace-mcp"]
    env:
      GOOGLE_CLIENT_ID: "${VT_GOOGLE_CLIENT_ID}"
      GOOGLE_CLIENT_SECRET: "${VT_GOOGLE_CLIENT_SECRET}"
      GOOGLE_REDIRECT_URI: "${VT_GOOGLE_REDIRECT_URI:-http://localhost:8080/oauth/callback}"
    healthcheck_interval_sec: 60
    restart_policy: on-failure
    log_file: ~/.vigilador/mcp-logs/google-workspace.jsonl
    pinned_version: 0.1.0
```

## Path conventions

### `_roadmap/` (nuevo)

Convención de naming para paquetes que están en árbol pero **NO en runtime activo**.

**Aplicado a**:
- `src/.../enterprise/_roadmap/artifacts/`
- `src/.../enterprise/orchestration/_roadmap/{app_development,goal_pursuit}/`
- `src/.../enterprise/dreaming/_roadmap_loops/`
- `src/.../enterprise/dreaming/phases/_roadmap/`
- `tests/enterprise/_roadmap/`
- `tests/enterprise/orchestration/_roadmap/`
- `tests/enterprise/dreaming/_roadmap/`

**Reglas**:
- Excluido de `pytest.ini::addopts --ignore=...`.
- Excluido de `scripts/check-layer-imports.py`.
- Importable explícitamente desde tests específicos (no automático).
- Cada archivo conserva su header `# ROADMAP F5b/F4b — fuera de MVP 021`.

### `_cold/` (nuevo)

Convención para skills que el SkillCatalog NO carga por default.

**Aplicado a**:
- `src/.../enterprise/skills_marketplace/_vendor/_cold/k_dense/skills/{8 directorios clínicos}`

**Reglas**:
- `KDenseAdapter.scan()` filtra cualquier path con `/_cold/`.
- `SkillCatalog` ignora paths bajo `_cold/`.
- Activación opcional: env `VT_COLD_SKILLS_ENABLED=1` o flag de mode config (futuro).

### `_singletons.py` (nuevo)

**Path**: `src/.../api/dependencies/_singletons.py`

Patrón `@lru_cache` para servicios cross-composition (2.0 + 3.0):

```python
@lru_cache(maxsize=1)
def get_embedding_gateway() -> GeminiEmbeddingGateway:
    return GeminiEmbeddingGateway()

@lru_cache(maxsize=1)
def get_tool_health_repo(database: Database) -> ToolHealthRepository:
    return ToolHealthRepository(database)

@lru_cache(maxsize=1)
def get_knowledge_graph_service() -> KnowledgeGraphService:
    return KnowledgeGraphService()
```

**Estado**: instancias persisten durante lifespan completo del app (sin reset entre requests).

## Estructura de directorio post-spec

```
src/vigilancia_multiagente/
├── api/
│   ├── app.py                                      ← modificado (lifespan shutdown wires)
│   ├── enterprise_composition.py                   ← modificado (singleton wire)
│   ├── router.py                                   ← sin cambios
│   ├── dependencies/                               ← NUEVO PAQUETE (era 1 archivo)
│   │   ├── __init__.py
│   │   ├── orchestration.py
│   │   ├── agents.py
│   │   ├── execution.py
│   │   ├── strategic_signals.py
│   │   ├── deep_analysis.py
│   │   ├── data_intelligence.py
│   │   ├── source_quality.py
│   │   ├── assurance.py
│   │   ├── governance.py
│   │   ├── session.py
│   │   └── _singletons.py
│   └── routes/                                     ← sin cambios
├── application/                                    ← INTOCADO (2.0)
├── enterprise/
│   ├── _roadmap/                                   ← NUEVO PATH
│   │   └── artifacts/                              ← MOVIDO
│   ├── orchestration/
│   │   ├── _roadmap/                               ← NUEVO PATH
│   │   │   ├── app_development/                    ← MOVIDO
│   │   │   └── goal_pursuit/                       ← MOVIDO
│   │   ├── (active modules)
│   ├── dreaming/
│   │   ├── _roadmap_loops/                         ← MOVIDO desde dreaming/loops/
│   │   ├── phases/
│   │   │   ├── _roadmap/                           ← NUEVO PATH (8 phases F5b)
│   │   │   ├── memory_consolidation.py             ← activo
│   │   │   └── ingestion_sync.py                   ← activo
│   │   ├── scheduler.py
│   │   ├── reporter.py
│   │   └── orchestrator.py
│   ├── tooling/
│   │   ├── builtin/
│   │   │   ├── _base/                              ← NUEVO PAQUETE
│   │   │   │   ├── __init__.py
│   │   │   │   ├── http_provider.py
│   │   │   │   └── retry_policy.py
│   │   │   ├── productivity/                       ← google_workspace.py REMOVIDO
│   │   │   ├── research/                           ← 10 providers REFACTORIZADOS
│   │   │   ├── web/                                ← 2 providers REFACTORIZADOS
│   │   │   ├── creative/                           ← MiniMax REFACTORIZADO
│   │   │   └── (otros sin cambios)
│   │   ├── tool_registry.py                        ← modificado (precompute + batch)
│   │   └── (resto sin cambios)
│   ├── skills_marketplace/
│   │   ├── _vendor/
│   │   │   ├── _cold/                              ← NUEVO PATH
│   │   │   │   └── k_dense/skills/{8 clinical}     ← MOVIDOS
│   │   │   ├── k_dense/                            ← restante sin cambios
│   │   │   └── agency_agents/                      ← sin cambios
│   │   ├── claude_local_adapter.py                 ← REMOVIDO
│   │   ├── skill_loader.py                         ← modificado (frontmatter-only)
│   │   ├── skill_registry.py                       ← modificado (cache wire)
│   │   ├── hash_tracker.py                         ← modificado (batch save)
│   │   └── (resto sin cambios)
│   └── governance/
│       ├── audit_log.py                            ← modificado (fsync verify)
│       ├── pi_quarantine_writer.py                 ← modificado (fsync verify)
│       └── (resto sin cambios)
└── infra/
    ├── db/connection.py                            ← modificado (env pool)
    ├── embeddings/
    │   ├── gemini_gateway.py                       ← modificado (batch + LRU)
    │   └── embedding_cache.py                      ← NUEVO
    ├── mcp/
    │   ├── playwright_mcp.py                       ← REMOVIDO
    │   ├── minimax_image_mcp.py                    ← REMOVIDO
    │   ├── mcp_cache.py                            ← modificado (LRU)
    │   └── (resto sin cambios)
    └── persistence/
        └── turbovec_index.py                       ← modificado (per-tenant locks)
```



---

## Skills `_cold/` — lista exhaustiva (FR-036)

### K-Dense skills a mover (62 directorios)

```
_vendor/k_dense/skills/
├── (skills relevantes MVP — preservar; ver lista en spec.md)
└── _cold/k_dense/skills/    ← NUEVO PATH
    ├── adaptyv/
    ├── aeon/
    ├── anndata/
    ├── astropy/
    ├── biopython/
    ├── bioservices/
    ├── bulk-rnaseq/
    ├── cellxgene-census/
    ├── cirq/
    ├── clinical-decision-support/
    ├── clinical-reports/
    ├── cobrapy/
    ├── datamol/
    ├── deepchem/
    ├── deeptools/
    ├── depmap/
    ├── dhdna-profiler/
    ├── diffdock/
    ├── dnanexus-integration/
    ├── esm/
    ├── fluidsim/
    ├── geniml/
    ├── geomaster/
    ├── geopandas/
    ├── gget/
    ├── ginkgo-cloud-lab/
    ├── glycoengineering/
    ├── gtars/
    ├── histolab/
    ├── imaging-data-commons/
    ├── labarchive-integration/
    ├── lamindb/
    ├── latchbio-integration/
    ├── matchms/
    ├── molecular-dynamics/
    ├── molfeat/
    ├── neurokit2/
    ├── neuropixels-analysis/
    ├── omero-integration/
    ├── opentrons-integration/
    ├── optimize-for-gpu/
    ├── pacsomatic/
    ├── pathml/
    ├── pathway-enrichment/
    ├── pennylane/
    ├── primekg/
    ├── protocolsio-integration/
    ├── pydeseq2/
    ├── pydicom/
    ├── pyhealth/
    ├── pylabrobot/
    ├── pyopenms/
    ├── pysam/
    ├── pytdc/
    ├── qiskit/
    ├── qutip/
    ├── scanpy/
    ├── scikit-bio/
    ├── scikit-survival/
    ├── scvelo/
    ├── scvi-tools/
    ├── tiledbvcf/
    └── torchdrug/
```

### agency_agents divisions a mover (2 divisions completas + 13 archivos individuales)

```
_vendor/agency_agents/
├── (preservar: academic, design, engineering, finance, integrations, marketing,
│    paid-media, product, project-management, sales, support, testing,
│    examples, scripts, .github, strategy, specialized [28 de 41 archivos])
└── _cold/agency_agents/    ← NUEVO PATH
    ├── game-development/    ← división completa (~50 archivos)
    │   ├── game-feel-engineer.md
    │   ├── game-monetization-designer.md
    │   ├── game-publishing-coordinator.md
    │   └── ... (resto)
    ├── spatial-computing/   ← división completa (6 archivos)
    │   ├── arcraft-developer.md
    │   ├── meta-quest-developer.md
    │   ├── mobile-ar-developer.md
    │   ├── unity-vr-developer.md
    │   ├── unreal-engine-developer.md
    │   └── webxr-developer.md
    └── specialized/         ← 13 archivos individuales (audit-positive non-MVP)
        ├── specialized-civil-engineer.md           ← no aplica B2B tech surveillance
        ├── specialized-french-consulting-market.md ← foco Colombia ≠ Francia
        ├── specialized-korean-business-navigator.md ← foco Colombia ≠ Corea
        ├── study-abroad-advisor.md                 ← no MVP
        ├── zk-steward.md                           ← niche zero-knowledge crypto
        ├── real-estate-buyer-seller.md             ← no MVP B2B
        ├── lsp-index-engineer.md                   ← super niche dev tooling
        ├── healthcare-customer-service.md          ← sector específico (existe support/)
        ├── healthcare-marketing-compliance.md      ← sector específico
        ├── hospitality-guest-services.md           ← industria específica
        ├── retail-customer-returns.md              ← industria específica
        ├── loan-officer-assistant.md               ← banca específica
        └── identity-graph-operator.md              ← niche identity graph
```

**NOTA crítica**: `consciousness-council` (K-Dense skill) **NO se mueve a `_cold/`**. Se preserva en `_vendor/k_dense/skills/consciousness-council/` porque es la base del modo `decision-debate` F4b roadmap (CrewAI debate orchestration).

### Skills MVP-relevant que SE PRESERVAN (sin cambio)

**K-Dense (~80 skills)**:

| Categoría | Skills | Justificación MVP |
|---|---|---|
| **Documents/reports** | docx, pdf, pptx, pptx-posters, latex-posters, markdown-mermaid-writing, markitdown, infographics, scientific-slides, scientific-visualization, scientific-writing, venue-templates, scientific-schematics, generate-image | Generación de informes de vigilancia tecnológica |
| **Literature/citations** | citation-management, literature-review, paper-lookup, paperzilla, peer-review, scholar-evaluation, scientific-brainstorming, scientific-critical-thinking, hypothesis-generation, hypogenic, research-grants, research-lookup, what-if-oracle, market-research-reports, exa-search, bgpt-paper-search, consciousness-council | Core: búsqueda académica + razonamiento crítico para technology-watch |
| **Generic ML/data** | autoskill, dask, modal, networkx, polars, polars-bio, pymc, pymoo, pufferlib, rdkit, scikit-learn, seaborn, shap, simpy, stable-baselines3, statistical-analysis, statsmodels, timesfm-forecasting, torch-geometric, transformers, umap-learn, vaex, xlsx, zarr-python, hugging-science, matplotlib, matlab, parallel-web, sympy | Análisis de datos en informes de tendencia |
| **Standards/utilities** | iso-13485-certification, database-lookup, get-available-resources, liteparse, pdf, bids | Estándares industria + utilidades genéricas |

**agency_agents (~167 archivos)**:

| División | Files | Justificación MVP |
|---|---:|---|
| `engineering/` | 29 | Backend, frontend, mobile, embedded, devops, sre, security, blockchain — directamente aplicables |
| `strategy/` | 16 | Trend analysis, competitive intelligence — core de vigilancia |
| `marketing/` | 30 | SEO, content, lifecycle, social — relevante para B2B |
| `specialized/` | 41 | Mixed cross-cutting roles — preservar todo |
| `finance/` | 5 | Para CFO mode roadmap |
| `product/` | 5 | Para product strategy |
| `sales/` | 8 | Para vendedor-b2b roadmap |
| `project-management/` | 6 | General business |
| `academic/` | 5 | Research-related |
| `support/` | 6 | Customer support |
| `testing/` | 8 | QA |
| `design/` | 8 | UI/UX |
| `paid-media/` | 7 | Paid advertising |
| `integrations/` | 15 (12 subdirs) | MCP/API integrations — preservar |
| `examples/`, `scripts/`, `.github/` | 17 | Estructura, no son skills |

---

## prompts/ — Estructura post-reforma (FR-033/034/035/036)

```
src/vigilancia_multiagente/prompts/
├── branches/                       ← 6 archivos, NO TOCAR (2.0 ACTIVO)
│   ├── avances.txt
│   ├── comercial.txt
│   ├── competitivo.txt
│   ├── oportunidades.txt
│   ├── pi_normativa.txt
│   └── riesgo.txt
├── evaluation/                     ← 24 archivos, NO TOCAR (2.0 ACTIVO)
│   └── (8 templates × 3 ejemplos cada uno)
├── orchestration/                  ← 3 archivos, NO TOCAR (2.0 ACTIVO)
│   ├── clarify.txt
│   ├── planning.txt
│   └── synthesis.txt
└── tools/                          ← 14 archivos PRESERVADOS + WIREADOS (FR-034)
    ├── arxiv.txt        ← actualizado durante Ola 4 (SDK arxiv)
    ├── brave.txt        ← actualizado durante Ola 4 (BaseHTTPProvider)
    ├── exa.txt          ← actualizado durante Ola 4 (SDK exa-py)
    ├── fetch.txt        ← actualizado durante Ola 4 (BaseHTTPProvider)
    ├── firecrawl.txt    ← actualizado durante Ola 4 (SDK firecrawl-py)
    ├── jina.txt         ← actualizado durante Ola 4 (BaseHTTPProvider)
    ├── markitdown.txt   ← preservar como está
    ├── minimax_image.txt ← actualizado durante Ola 4 (BaseHTTPProvider)
    ├── openalex.txt     ← actualizado durante Ola 4 (SDK pyalex)
    ├── playwright.txt   ← preservar como está
    ├── sandbox.txt      ← preservar como está
    ├── scholar.txt      ← preservar como está
    ├── serper.txt       ← actualizado durante Ola 4 (BaseHTTPProvider)
    ├── tavily.txt       ← actualizado durante Ola 4 (SDK tavily-python)
    └── google-workspace-mcp.txt ← NUEVO archivo Ola 4 (FR-035, 25+ capabilities)
```

**ELIMINADOS** (FR-033 revisada):
- `prompts/minimax_examples/` (4 archivos `.txt`)
- `infra/llm/minimax_client.py` (146 LOC)
- `tests/test_minimax_client.py`

**Análisis del cambio**:

| Path | Antes | Después | Razón |
|---|---|---|---|
| `branches/` | 6 archivos activos | 6 archivos activos | 2.0 preservado |
| `evaluation/` | 24 archivos activos | 24 archivos activos | 2.0 preservado |
| `orchestration/` | 3 archivos activos | 3 archivos activos | 2.0 preservado |
| `minimax_examples/` | 4 archivos | **eliminados** | FR-033 revisada — full delete (no `_legacy/`) |
| `tools/` | 14 archivos huérfanos (no wireados) | 14 archivos + 1 nuevo, **wireados via FR-034** | Deuda técnica preexistente: rich docs nunca cargadas en runtime → ahora `ToolRegistry.get_docs()` los carga |

**Total**: 4 archivos eliminados (minimax_examples), 14 wireados + 1 nuevo (tools), 33 preservados sin cambio. Net delta: 4 archivos `.txt` menos, 1 archivo nuevo, 14 archivos wireados al runtime.

**Wiring (FR-034)**:
```python
# enterprise/tooling/tool_registry.py
async def get_docs(self, name: str) -> ToolDocs:
    summary = await self.get_summary(name)
    tool = self._tools[name]
    long_description = ""
    try:
        from vigilancia_multiagente.infra.prompts.loader import load_prompt
        long_description = load_prompt(f"tools/{name}")
    except FileNotFoundError:
        pass
    return ToolDocs(
        summary=summary,
        long_description=long_description,
        full_examples=getattr(tool, "full_examples", []),
    )
```

---

## Settings.py — env vars nuevas

| Var | Default | Spec FR | Uso |
|---|---|---|---|
| `VT_DB_POOL_SIZE` | `10` | FR-007 | SQLAlchemy pool_size |
| `VT_DB_POOL_OVERFLOW` | `20` | FR-007 | SQLAlchemy max_overflow |
| `VT_MCP_CACHE_MAX_ENTRIES` | `1000` | FR-008 | LRU eviction threshold |
| `VT_MCP_CACHE_TTL_SHORT` | `1800` (30 min) | FR-008 | Short TTL para queries volátiles |
| `VT_MCP_CACHE_TTL_LONG` | `604800` (7 días) | FR-008 | Long TTL para queries estables |
| `VT_COLD_SKILLS_ENABLED` | `0` | FR-036 | Si `1`, SkillCatalog incluye `_cold/` |
| `VT_GOOGLE_CLIENT_ID` | (existente) | FR-009 | OAuth Google Workspace MCP |
| `VT_GOOGLE_CLIENT_SECRET` | (existente) | FR-009 | OAuth Google Workspace MCP |
| `VT_GOOGLE_REDIRECT_URI` | `http://localhost:8080/oauth/callback` | FR-009 | OAuth callback URL |
