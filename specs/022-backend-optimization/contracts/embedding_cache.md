# Contract: EmbeddingCache

**Phase 1 contract output**. Two-tier cache para embeddings de tool/skill descriptions.

## Public surface

```python
class EmbeddingCachePort(Protocol):
    """DIP: callers depend on this; tests inject fakes."""
    async def get(self, content: str) -> list[float] | None: ...
    async def set(self, content: str, vector: list[float]) -> None: ...
    async def get_many(self, contents: list[str]) -> dict[str, list[float] | None]: ...
    async def flush_to_disk(self) -> None: ...
    async def load_from_disk(self) -> int: ...  # returns count loaded


class EmbeddingCache:
    """Two-tier (LRU memory + JSON disk) cache."""

    def __init__(
        self,
        cache_dir: Path = Path.home() / ".vigilador" / "cache" / "embeddings",
        max_memory_entries: int = 1000,
        cache_namespace: str = "default",  # e.g. "tools" or "skills"
    ) -> None: ...
```

## Cache key

`key = sha256(content[:4096].encode()).hexdigest()[:16]`

- 16-char prefix de SHA-256 evita colisiones para <10^9 entries.
- Truncate a 4096 chars: descripciones MVP no deberían exceder; si exceden, key sigue determinista.

## Lifecycle

```
boot:
  cache = EmbeddingCache(namespace="tools")
  await cache.load_from_disk()  # populate L2 → L1 (top 1000)
  
register_tool(tool):
  hash = key(tool.description)
  vec = await embedding_gw.embed(tool.description)
  await cache.set(hash, vec)  # L1 add (may evict)
  
discover():
  hashes = [key(t.description) for t in tools]
  hits = await cache.get_many(hashes)  # batch L1 lookup
  # hits[h] is None si no en L1 (re-embed if needed; raro post-register)
  
shutdown:
  await cache.flush_to_disk()  # L1 → L2 atomic write
```

## Disk format

`~/.vigilador/cache/embeddings/{namespace}.json`:

```json
{
  "version": "022.1",
  "created_at": "2026-06-01T01:00:00Z",
  "embeddings": {
    "a3f1b2c4d5e6f7a8": [0.123, -0.456, ...],
    "b4f2c3d4e5f6a7b8": [0.234, -0.567, ...]
  }
}
```

**Atomic write**: write to `{namespace}.json.tmp` + `os.rename` para garantizar no-corrupción ante crash mid-write.

## Invalidación

- **Por size**: L1 LRU evicta el menos-recientemente-usado cuando size > `max_memory_entries`.
- **Por content-hash change**: si `tool.description` cambia, su hash key cambia → cache miss natural → re-embed → set bajo nuevo key. El key viejo queda huérfano hasta el próximo `flush_to_disk()` (que NO incluye keys no accesados desde load).
- **Por corruption**: si JSON parse falla en `load_from_disk()`, log WARNING + arranca con cache vacío + flush sobreescribe (EC-01).

## Concurrencia

- L1 protegido por `asyncio.Lock` (single writer at a time).
- L2 disk read/write único (boot + shutdown). NO concurrent disk access durante runtime.

## Observability

- `get/set` logean a DEBUG con namespace + hit/miss.
- `load_from_disk` logea INFO con count de entries cargadas + warning si version mismatch.
- `flush_to_disk` logea INFO con count flushed.

## Edge cases

- **EC-01**: JSON corrupto → log WARNING, arranca empty, sobreescribe en flush.
- **EC-02**: Disk lleno en flush → raise `EmbeddingCacheError("disk full")` propagado al caller.
- **EC-03**: Entry vector size 0 (corrupto) → skip + log WARNING.
- **EC-04**: Concurrent `set()` durante `flush_to_disk()` → flush snapshot del estado pre-flush; nuevos sets quedan para próximo flush.

## Test contract

```python
async def test_set_get_roundtrip():
    cache = EmbeddingCache(cache_dir=tmp_path, max_memory_entries=10)
    await cache.set("hello", [0.1, 0.2, 0.3])
    assert await cache.get("hello") == [0.1, 0.2, 0.3]

async def test_lru_evict():
    cache = EmbeddingCache(max_memory_entries=2)
    await cache.set("a", [0.1])
    await cache.set("b", [0.2])
    await cache.set("c", [0.3])  # evicts "a"
    assert await cache.get("a") is None
    assert await cache.get("b") == [0.2]
    assert await cache.get("c") == [0.3]

async def test_disk_persist():
    cache1 = EmbeddingCache(cache_dir=tmp_path, namespace="t")
    await cache1.set("x", [0.5])
    await cache1.flush_to_disk()
    
    cache2 = EmbeddingCache(cache_dir=tmp_path, namespace="t")
    await cache2.load_from_disk()
    assert await cache2.get("x") == [0.5]

async def test_corrupt_json_recovery():
    (tmp_path / "tools.json").write_text("not json")
    cache = EmbeddingCache(cache_dir=tmp_path, namespace="tools")
    count = await cache.load_from_disk()
    assert count == 0  # graceful empty start, NO exception
```
