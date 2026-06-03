# Research: Backend Optimization 022

**Phase 0 output**. Resuelve clarificaciones técnicas y documenta decisiones de implementación con rationale + alternativas evaluadas.

## R-01: Versiones pinneadas de SDKs oficiales

**Decisión**:
- `tavily-python>=0.5.0,<1.0.0` (PyPI oficial Tavily AI, MIT)
- `exa-py>=1.5.0,<2.0.0` (PyPI oficial Exa Labs, MIT)
- `firecrawl-py>=2.0.0,<3.0.0` (PyPI oficial Firecrawl, MIT)
- `pyalex>=0.18.0,<1.0.0` (PyPI MIT, community-maintained con tracción, OpenAlex polite pool)
- `arxiv>=2.1.0,<3.0.0` (PyPI oficial, BSD)

**Rationale**: Versiones major-bumped en últimos 12 meses, releases regulares (≥4/año), >50 stars GitHub o uso documentado en proyectos enterprise.

**Alternatives evaluated**:
- `python-tavily` (community) — abandonado, último release 2024.
- Reimplementar todo con BaseHTTPProvider — viola assumption A-01 (preferir SDK maduro).
- `openalex-api-tools` (community) — menos features que pyalex.

## R-02: Estado del Gemini batchEmbedContents endpoint

**Decisión**: Usar `google-generativeai>=0.5.0` con `embed_content_batch()` cuando `len(texts) > 1`. Si la versión instalada NO soporta batch, fallback a `asyncio.gather(embed_content)` con concurrency limit 16.

**Rationale**: La API REST `models/{model}:batchEmbedContents` está documentada en https://ai.google.dev/api/embeddings#batchembedcontents desde 2024-Q4. El SDK Python `google-generativeai` la expone vía `client.models.embed_content` con parameter `request_options.batch_size`. Verificable post-install.

**Alternatives evaluated**:
- HTTP directo a la URL batch — pierde reuso de auth + retry built-in.
- Concurrent `asyncio.gather` solamente — funcional pero 311 requests vs 4 (batch 100).
- Migrar a un proveedor diferente (OpenAI text-embedding-3-small) — fuera de scope (D1 no aplica pero sí decisión arquitectónica).

**Investigación pendiente**: confirmar API shape exacto en `google-generativeai==0.7.0+` durante implementación de Ola 3. Si no soporta nativo, queda fallback.

## R-03: Pin del Google Workspace MCP

**Decisión**: `taylorwilsdon/google_workspace_mcp` versión `v0.1.0` (tag git pinned). Instalación vía `npx -y @taylorwilsdon/google-workspace-mcp` o `pip install taylorwilsdon-google-workspace-mcp` (verificar disponibilidad en npm vs PyPI).

**Rationale**: Ya está documentado en `config/tools/catalog.yaml:447` como `pinned_version: 0.1.0` y `source_repo: https://github.com/nicholishen/google-workspace-mcp`. El maintainer correcto es Taylor Wilsdon (`taylorwilsdon/google_workspace_mcp`); la URL `nicholishen` parece fork/typo a corregir durante implementación.

**Acción durante implementación**: validar que el repo correcto es Taylor Wilsdon, actualizar `source_repo` en catalog.yaml si necesario. Smoke test del binary `npx -y @taylorwilsdon/google-workspace-mcp --help` antes de declararlo en `external.yaml`.

## R-04: Estrategia BaseHTTPProvider — diseño concreto

**Decisión**: clase abstracta con composition + retry decorator.

```python
class BaseHTTPProvider:
    name: ClassVar[str]
    domain: ClassVar[str]
    base_url: ClassVar[str]
    auth_env_var: ClassVar[str | None]
    requires_auth: ClassVar[bool] = True

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._retry_policy = RetryPolicy(
            max_attempts=3,
            backoff=ExponentialBackoff(initial=1.0, max=8.0),
            retry_on=(503, 502, 504, httpx.ConnectError, httpx.ReadTimeout),
        )

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
                timeout=httpx.Timeout(30.0, connect=5.0),
            )
        return self._client

    async def aclose(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _api_key(self) -> str | None:
        if not self.auth_env_var:
            return None
        return os.environ.get(self.auth_env_var)

    def _auth_headers(self, api_key: str) -> dict[str, str]:
        # Default: Bearer token. Subclasses override for custom patterns.
        return {"Authorization": f"Bearer {api_key}"}

    @retry_with_policy
    async def post(self, path: str, json: dict, **kwargs) -> dict:
        api_key = await self._api_key()
        if self.requires_auth and not api_key:
            raise ProviderUnconfiguredError(...)
        headers = {**(kwargs.pop("headers", {})), **self._auth_headers(api_key)}
        response = await self.client.post(path, json=json, headers=headers, **kwargs)
        response.raise_for_status()
        return response.json()

    async def healthcheck(self) -> HealthcheckResult:
        # Default: api_key gating. Subclasses override for endpoint pings.
        if self.requires_auth and not (await self._api_key()):
            return HealthcheckResult(status="UNCONFIGURED", error=...)
        return HealthcheckResult(status="UP")
```

**Rationale**: SRP (1 base class + retry + connection pool), DIP (subclasses inyectan vía override de `_auth_headers` cuando difiera), KISS (3 métodos públicos: `post`, `get`, `aclose` + 2 hooks). Cada subclase ≤80 LOC (FR-014).

**Alternatives evaluated**:
- Mixin-based composition (RetryMixin + AuthMixin + HTTPMixin) — más LOC, peor inheritance graph.
- Functional approach con closures — perdería type-safety en basedpyright-standard.
- `httpx.HTTPTransport` con retries built-in — solo cubre transport-level retries, no respuestas 5xx parseadas.

## R-05: Estrategia de cache de embeddings

**Decisión**: Two-tier cache.
- **L1 (in-memory LRU)**: `functools.lru_cache(maxsize=1000)` envolviendo método interno; key = SHA-256 del texto truncado a 4KB.
- **L2 (disk)**: JSON único en `~/.vigilador/cache/embeddings/{tools.json,skills.json}` con shape `{content_sha256: [floats], ...}`. Carga en boot, save batch al final del registry build.

**Invalidación**:
- Boot lee disco. Si content-hash de tool/skill cambia (HashTracker compara), regenera ese embedding (no toda la cache).
- L1 invalidación es automática por size limit.

**Rationale**: L1 absorbe queries repetidas mismas description (el caso típico es discover() del mismo agent contra misma tool repetidamente). L2 elimina cold-start cost (100% hit rate en boots subsiguientes si nada cambió).

**Alternatives evaluated**:
- Redis o memcached — overkill para single-process MVP, añade dep externa.
- SQLite — overhead de schema + ACL. JSON es suficiente para 311 entries.
- Sin cache, cómputo each-time — viola SC-001 y SC-002.

## R-06: TurboVecIndex lock granularidad

**Decisión**: `dict[UUID, asyncio.Lock]` keyed por `tenant_id`. Método público `_get_lock(tenant_id)` con creación lazy thread-safe. Lock separado por operación: `_write_lock` (add/remove) ≠ `_persist_lock` (flush a disco).

**Rationale**: Permite concurrent writes a tenants distintos (no bottleneck cross-tenant); within-tenant serialization protege el index file. Locks separados evitan deadlock cuando `add()` triggers `persist()` interno.

**Alternatives evaluated**:
- Single global lock — bloqueo total cross-tenant inaceptable en multi-tenant runtime.
- File-level fcntl/portalocker — adds platform-specific code (Windows soporte parcial), viola KISS.
- `threading.Lock` — incompatible con asyncio event loop.

## R-07: Sync flush AuditLog (decisión usuario E-05)

**Decisión**: `_write` y `flush` en mismo call stack. `with path.open("a", encoding="utf-8") as fh: fh.write(line); fh.flush(); os.fsync(fh.fileno())` para garantía durabilidad.

**Rationale**: Usuario explícitamente rechazó buffer (E-05). `os.fsync` añade ~5-10 ms por evento pero da durability garantizada vs hard crash. El audit log es crítico (FR-020/021).

**Alternatives evaluated**:
- Buffer con flush cada 5s + atexit — rechazado por usuario.
- Buffer write-through pero sync close en shutdown handler — frágil ante SIGKILL.
- Append-only sin fsync — pérdida de últimos eventos si crash entre write() y kernel flush. Inaceptable para audit.

**Trade-off**: ~5-10 ms latencia adicional por tool/llm/complexity event. En sesión típica de 100 events = 0.5-1s overhead total. Aceptable.

## R-08: Migración incremental de providers (orden)

**Decisión**: Orden por riesgo creciente.
1. **Tavily** (PoC, SDK más simple, único endpoint, ya tiene tests sólidos)
2. **OpenAlex** (`pyalex`, sin auth, pública)
3. **Arxiv** (`arxiv` SDK, ya migra de XML manual)
4. **Exa** (`exa-py`, multi-endpoint pero auth simple)
5. **Firecrawl** (`firecrawl-py`, async-ready)
6. **Brave** → BaseHTTPProvider
7. **Serper** → BaseHTTPProvider (auth header custom)
8. **Serper Patents** → BaseHTTPProvider (extends Serper)
9. **Jina** → BaseHTTPProvider (auth simple)
10. **Fetch** → BaseHTTPProvider (sin auth, HTML→text con `markitdown` opcional)
11. **MiniMax Image** → BaseHTTPProvider (deja para final, edge case con multipart)

**Rationale**: PoC con Tavily demuestra el patrón con riesgo bajo. SDKs primero (≤5 archivos a tocar), luego BaseHTTPProvider (cambio aditivo + refactor ya validado).

## R-09: Skills `_cold/` strategy

**Decisión**: Mover los 8 directorios a `src/vigilancia_multiagente/enterprise/skills_marketplace/_vendor/_cold/k_dense/skills/` (mantener estructura interna). `KDenseAdapter.scan()` filtra por path: ignora cualquier path que contenga `/_cold/`. SkillCatalog ignora paths bajo `_cold/`.

**Activación on-demand**: env var `VT_COLD_SKILLS_ENABLED=1` o flag de mode config rehabilita la lectura. NO se carga por default.

**Rationale**: Preserva spec D2 (vendor en src). Reduce disk read en boot ~3-5 MB, embedding compute ~50 calls (~5s en cold-start). Reactivable sin git operations.

## R-10: Splits de archivos >400 LOC

**Decisión**: Splits programados durante el plan:
- `api/dependencies.py` (694 LOC) → `api/dependencies/` (10 submodules ≤100 LOC c/u + `__init__.py` ≤30 LOC re-exports). FR-016.
- `enterprise/governance/audit_log.py` (249 LOC) — bajo límite, NO split.
- `domain/evaluation_entities.py` (496 LOC) — **fuera de scope** (es 2.0 — preservar).
- `enterprise/orchestration/playbook_runner.py` (327 LOC) — bajo límite, NO split.

**Rationale**: SC-009 exige ≤400 LOC en archivos nuevos/modificados. `dependencies.py` es el único en scope que viola.

**Alternatives evaluated**:
- Splittear `domain/evaluation_entities.py` — viola constraint sagrado "NO TOCAR 2.0".
- Mantener `dependencies.py` monolítico — viola SC-009 + Constitución C-2.

## R-11: Numpy fallback strategy

**Decisión**: Import numpy a top-level. Si fail (ImportError), define fallback puro Python con misma signature. Logear WARNING en boot solo si fallback se carga.

```python
try:
    import numpy as np
    def cosine_similarity(a: list[float], b: list[float]) -> float:
        va, vb = np.asarray(a), np.asarray(b)
        denom = np.linalg.norm(va) * np.linalg.norm(vb)
        return 0.0 if denom == 0 else float(np.dot(va, vb) / denom)
except ImportError:
    def cosine_similarity(a, b):
        # pure-Python fallback
        ...
```

**Rationale**: Numpy es deps obligatoria (FR-004 + A-09 + E-09 user decision). Pero el fallback existe como defense-in-depth (EC-05).

## R-12: Tests baseline gate sagrado

**Decisión**: Suite gate-sagrada listada en spec FR-028 + check de `git diff --stat` sobre `application/execution/branch_coordinator.py` + `application/evaluation/ws_*` para garantizar 0 cambios (FR-029, SC-010).

**Pre-cada-ola** + **post-cada-ola**:
```powershell
$gateTests = @(
  "tests/test_orchestrator.py",
  "tests/application/execution/",
  "tests/application/evaluation/",
  "tests/enterprise/governance/test_audit_log",
  "tests/enterprise/orchestration/test_dispatcher.py",
  "tests/api/routes/test_research_"
)
python -m pytest $gateTests -x --tb=short
git diff --stat src/vigilancia_multiagente/application/
```

**Rationale**: Detección temprana de regression. Falla rápido = revert por archivo, no por ola completa.

## R-13: Rollback granularity

**Decisión**: cada FR mapea a 1-3 archivos como máximo. Rollback es `git checkout <archivo>` por FR. Plan de rollback en plan.md por fase.

## R-14: Feature flags para rollout gradual

**Decisión**: NO añadir feature flags. Cada cambio es backward-compatible (re-exports preservan API; opt-in por settings cuando sea necesario):
- LRU embedding cache: siempre ON, sin flag.
- Disk cache: siempre ON; corruption auto-recovery (EC-01).
- BaseHTTPProvider: drop-in replacement (mismo Tool contract).
- Google Workspace MCP: el MCP se levanta solo si `external.yaml` lo declara — su existencia ES el flag.
- numpy cosine: auto-fallback si no instalado (EC-05).

**Rationale**: KISS. Feature flags introducen branches en runtime + más LOC + más bugs. Cada cambio tiene rollback determinista (revert commits).

## R-15: Tests de provider contract (FR-013, SC-013)

**Decisión**: Crear `tests/enterprise/tooling/test_provider_contract.py` que valide los 11 providers + 3 documents tools + computer_use + sandbox + minimax_image satisfacen el `ToolWrapper` Protocol vía `runtime_checkable`. Test parametrizado.

```python
@pytest.mark.parametrize("tool", ALL_BUILTIN_TOOLS)
def test_tool_satisfies_protocol(tool):
    assert isinstance(tool, ToolWrapper)
    assert hasattr(tool, "execute")
    assert hasattr(tool, "healthcheck")
    assert tool.name and tool.domain and tool.requires_auth in (True, False)
```

**Rationale**: SC-013 exige verificación contract uniforme post-migration. Test paramétrico es DRY.

## Conclusiones de Phase 0

- Todas las decisiones técnicas resueltas. **0 NEEDS CLARIFICATION** restantes.
- 9 decisiones del usuario (E-01..E-09) cerradas; mappings explícitos a FRs.
- Fallbacks documentados para cada novedad (numpy, Gemini batch, MCP unavailable).
- Strategy: SDK > BaseHTTPProvider > MCP-EXTERNO (D5 reafirmada).
- Listo para Phase 1 (data-model + contracts + quickstart).



## R-16: Tool docs discovery — deuda técnica preexistente

**Hallazgo (Phase 1 Skills audit)**: `grep "description:|examples:|long_description"` sobre `enterprise/tooling/builtin/` retorna **0 matches** en provider tools concretos. Eso significa que en runtime actual, el LLM solo ve `name` + `domain` + (raramente) `description ≤80 chars` al hacer `discover()`. La rich documentation que el LLM necesita para selección/uso correcto de cada tool **no está expuesta**.

**Lugar correcto de la rich docs**: `src/vigilancia_multiagente/prompts/tools/<name>.txt` ya contiene XML estructurado por tool con:
- `<function_signature>` — firma completa
- `<best_for>` — cuándo usar
- `<usage>` — instrucciones operativas
- `<limits>` — timeout, retries
- `<selection_heuristics>` — cuándo elegir vs otras tools
- `<chaining>` — secuencias multi-step (ej: arxiv search → download → read)
- `<fallback>` — recovery patterns
- `<rules>` — reglas críticas

**Decisión**: NO eliminar `prompts/tools/*.txt`. AL CONTRARIO, **wirearlos** en `ToolRegistry.get_docs(name) -> ToolDocs`:

```python
# enterprise/tooling/tool_registry.py
async def get_docs(self, name: str) -> ToolDocs:
    summary = await self.get_summary(name)
    tool = self._tools[name]

    # FR-034: cargar rich docs desde prompts/tools/<name>.txt
    long_description = ""
    try:
        from vigilancia_multiagente.infra.prompts.loader import load_prompt
        long_description = load_prompt(f"tools/{name}")
    except FileNotFoundError:
        pass  # tool sin docs ricos — no error

    return ToolDocs(
        summary=summary,
        long_description=long_description,
        full_examples=getattr(tool, "full_examples", []),
    )
```

**Rationale**: 
- KISS: 1 punto de cambio (`get_docs`), reuso del loader ya existente con LRU cache.
- DIP preservado: callers consumen `ToolDocs.long_description` sin saber del filesystem.
- Backward-compatible: si archivo no existe, `long_description=""` (no crash).
- Single source of truth: rich docs en `prompts/tools/`, code attributes solo `name`/`domain`.

**Alternatives evaluated**:
- Inline `description`/`examples` en cada tool class → +40 LOC por archivo, viola SRP (mezcla docs y código).
- Auto-generar de docstrings → docstrings actuales son insuficientes (no estructurados).
- Migrar contenido a YAML catalog → fragmentación + parser custom innecesario.

**Migración required**: durante Ola 4, los 11 archivos `prompts/tools/<provider>.txt` deben actualizarse para reflejar las nuevas signaturas tras SDK migration / BaseHTTPProvider. Por ejemplo `tavily.txt` actual menciona `tavily_search(query, search_depth, ...)` que post-SDK migration cambia a `tavily.search(query, search_depth=...)`. El XML structure se preserva.

**Nuevo archivo**: `prompts/tools/google-workspace-mcp.txt` con guidance para las 25+ capabilities post-revert (Gmail flows, Calendar scheduling, Drive browsing, Docs editing, Sheets, Forms).

## R-17: MiniMax LLM — eliminación total

**Decisión revisada (E-01 user decision + audit)**: eliminar completo el MiniMax LLM client en lugar de moverlo a `_legacy/`.

**Justificación**:
- Xiaomimimo es default LLM por D5 (Spec 021).
- MiniMax LLM no tiene caller activo en MVP.
- `MiniMaxClient.complete()` carga `prompts/minimax_examples/*.txt` que solo sirven a este client.
- Mantenerlo como `_legacy/` añade overhead de mantenimiento (tests, deps) sin valor.

**Files eliminados**:
- `src/vigilancia_multiagente/infra/llm/minimax_client.py` (146 LOC)
- `tests/test_minimax_client.py`
- `src/vigilancia_multiagente/prompts/minimax_examples/` (4 archivos)

**Files NO eliminados** (separar productos):
- `src/vigilancia_multiagente/enterprise/tooling/builtin/creative/minimax_image.py` — `MiniMaxImageTool` para image generation, sigue como builtin tool.
- `pyproject.toml` deps que MiniMax Image necesite (`pillow`, etc.) — preservar.

**Total LOC delta de R-17**: -146 (LLM client) + ~50 (test) + ~80 (prompts) = **-276 LOC**.
