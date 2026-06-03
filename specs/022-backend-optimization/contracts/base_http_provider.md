# Contract: BaseHTTPProvider

**Phase 1 contract output**. Define la interface pública y semántica del `BaseHTTPProvider` que consolida 6 providers HTTP en spec 022.

## Public surface

```python
class BaseHTTPProvider:
    name: ClassVar[str]
    domain: ClassVar[str]
    base_url: ClassVar[str]
    auth_env_var: ClassVar[str | None]
    requires_auth: ClassVar[bool] = True
    is_external_mcp: ClassVar[bool] = False

    def __init__(self) -> None: ...

    @property
    def client(self) -> httpx.AsyncClient: ...

    async def aclose(self) -> None: ...

    async def post(self, path: str, *, json: dict, headers: dict | None = None, timeout: float | None = None) -> dict: ...

    async def get(self, path: str, *, params: dict | None = None, headers: dict | None = None, timeout: float | None = None) -> dict: ...

    async def healthcheck(self) -> HealthcheckResult: ...

    async def execute(self, tool_name: str, args: dict[str, Any]) -> dict[str, object]:
        """Subclass MUST override. Maps tool_name to internal method."""
        raise NotImplementedError
```

## Override hooks (subclass extends)

| Hook | Default | Cuándo override |
|------|---------|-----------------|
| `_auth_headers(api_key: str) -> dict[str, str]` | `{"Authorization": f"Bearer {api_key}"}` | Brave (`X-Subscription-Token`), Serper (`X-API-KEY`) |
| `_api_key() -> str \| None` | Lee `os.environ[auth_env_var]` | Si custom resolution lógica (ej. tenant-scoped) |
| `healthcheck()` | api_key gating only | Si endpoint específico de ping (ej. `/health`) |
| `execute()` | NotImplementedError | Subclass mapping de capabilities a `post()`/`get()` |

## Semántica de retry

**Politica**: 3 attempts, exponential backoff `(1s, 2s, 4s)`, retry_on:
- HTTP status codes: 503, 502, 504, 429 (rate limit)
- Exceptions: `httpx.ConnectError`, `httpx.ReadTimeout`, `httpx.RemoteProtocolError`

**NO retry**:
- 4xx (excepto 429): error de client, retry no ayuda
- `httpx.HTTPStatusError(401)`: auth invalida, retry no resuelve
- `ProviderUnconfiguredError`: env var falta, retry no resuelve

**Retry max time**: total ≤8s (1+2+4+1 jitter).

**Idempotencia**: `post()` y `get()` se asumen idempotentes a nivel del provider externo. Si el provider tiene endpoint NON-idempotent (ej. send_email), la subclase debe **deshabilitar** retry para ese endpoint via `@no_retry` decorator (futuro). MVP: retry siempre activo.

## Error mapping

| Origen | Tipo expuesto |
|--------|---------------|
| `httpx.ConnectError` post-retries | `ProviderTimeoutError` |
| `httpx.ReadTimeout` post-retries | `ProviderTimeoutError` |
| HTTP 401, 403 | `ProviderAuthError` |
| HTTP 404 | `ProviderNotFoundError` |
| HTTP 429 post-retries | `ProviderRateLimitError` |
| HTTP 5xx post-retries | `ProviderServerError` |
| Missing api_key | `ProviderUnconfiguredError` |
| JSON decode failure | `ProviderResponseError` |

Todos heredan de `ProviderError(RuntimeError)`. Caller (ToolRegistry.execute) cataloga en audit_log + propaga.

## Connection pooling

- 1 `httpx.AsyncClient` por instancia de provider (1 instancia por tipo en composition).
- `Limits(max_connections=100, max_keepalive_connections=20)`.
- `Timeout(30.0, connect=5.0)` defaults.
- Lazy creation en primer access vía `client` property.
- `aclose()` libera el pool.

**Lifecycle**:
```
provider_instance → first request → client created → kept-alive → ...
                                                                  ↓
                                                    aclose() en lifespan.shutdown
```

## Healthcheck contract

**Default behavior**:
- Si `requires_auth=True` y `_api_key() is None`: return `HealthcheckResult(status="UNCONFIGURED", error="API key missing in env <auth_env_var>")`.
- Sino: return `HealthcheckResult(status="UP")`.

**Override pattern** (e.g., Brave):
```python
async def healthcheck(self) -> HealthcheckResult:
    base = await super().healthcheck()
    if base.status == "UNCONFIGURED":
        return base
    try:
        await self.get("/api/health")
        return HealthcheckResult(status="UP")
    except ProviderError as e:
        return HealthcheckResult(status="DOWN", error=str(e))
```

## Test contract

Cada subclase MUST tener test que verifique:
1. Sin `auth_env_var` set → healthcheck retorna `UNCONFIGURED`.
2. Con env var falsa → primera request retorna `ProviderAuthError`.
3. Con respx mock 503 → retry 3 attempts → 4ta como 200 → retorna OK.
4. Con respx mock 503 persistente → retorna `ProviderServerError` post-3 attempts.
5. `aclose()` cierra `_client.is_closed = True`.

## Subclass concretas en spec 022

| Subclass | LOC esperado | Override |
|----------|-------------:|----------|
| `BraveTool(BaseHTTPProvider)` | ≤80 | `_auth_headers` (X-Subscription-Token) |
| `SerperTool(BaseHTTPProvider)` | ≤80 | `_auth_headers` (X-API-KEY) |
| `SerperPatentsTool(SerperTool)` | ≤40 | path/method only |
| `JinaTool(BaseHTTPProvider)` | ≤80 | bearer (default) |
| `FetchTool(BaseHTTPProvider)` | ≤90 | sin auth, opcional markitdown |
| `MiniMaxImageTool(BaseHTTPProvider)` | ≤100 | multipart support |

## Migración drop-in

Cada subclase **MUST** preservar:
- `name` (string ID en ToolRegistry)
- `domain` (catalog category)
- `execute(tool_name, args)` signature y shape de respuesta
- `healthcheck()` retornando `HealthcheckResult`

Tests existentes de cada provider deben pasar SIN modificación post-migration. Si un test rompe, indica cambio de comportamiento → revisar.
