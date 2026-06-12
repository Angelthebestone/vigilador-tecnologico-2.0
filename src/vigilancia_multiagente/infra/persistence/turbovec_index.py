"""TurboVec adapter — native in-process vector index (Spec 021 D1-revisada).

Implements :class:`IngestionVectorIndex` from
``domain/ports/vector_index.py``. Uses the ``turbovec`` PyPI package
(Rust + Python bindings, MIT). Persists per tenant to
``~/.vigilador/turbovec/<tenant>.tq``.

Constitución:
* SRP: this file is an adapter over ``turbovec``; it does NOT do
  embedding generation, ACL filtering, or chunking — those live elsewhere.
* #4 explicit errors: missing optional dependency surfaces as
  ``healthcheck() == DOWN`` and ``add/query/persist/rebuild`` raise
  ``RuntimeError`` with install instructions.
* DIP: depends on the protocol, not on the consumer.

The adapter is sync inside (turbovec is sync); we offload via
``asyncio.to_thread`` to keep the async surface honest.
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)

_DEFAULT_BIT_WIDTH = 4
_TURBOVEC_HOME_ENV = "VT_TURBOVEC_HOME"
_DEFAULT_HOME = "~/.vigilador/turbovec"


@dataclass
class _IndexHandle:
    """Per-tenant in-memory state."""

    tenant_id: UUID
    index: Any  # turbovec.TurboQuantIndex | None until first add()
    dim: int = 0
    bit_width: int = _DEFAULT_BIT_WIDTH
    pending_writes: int = 0
    metadata_by_chunk: dict[int, dict[str, object]] = field(default_factory=dict)


class TurboVecIndex:
    """``IngestionVectorIndex`` adapter over the ``turbovec`` package.

    The adapter is **lazy**: ``turbovec`` is imported on first use, and
    the per-tenant index is constructed on first ``add()`` (when we know
    the embedding dimension). ``healthcheck()`` is the only entry that
    surfaces a missing-package state without raising.
    """

    def __init__(
        self,
        *,
        bit_width: int = _DEFAULT_BIT_WIDTH,
        home_dir: Path | None = None,
    ) -> None:
        self._bit_width = bit_width
        env_home = os.getenv(_TURBOVEC_HOME_ENV)
        base = home_dir or (Path(env_home) if env_home else Path(_DEFAULT_HOME))
        self._home = base.expanduser()
        self._home.mkdir(parents=True, exist_ok=True)
        self._handles: dict[UUID, _IndexHandle] = {}
        # FR-007: Per-tenant locks for concurrent write safety
        self._tenant_write_locks: dict[UUID, asyncio.Lock] = {}
        self._tenant_persist_locks: dict[UUID, asyncio.Lock] = {}
        self._master_lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Healthcheck
    # ------------------------------------------------------------------

    async def healthcheck(self) -> str:
        try:
            import turbovec  # noqa: F401  # presence-only import probe
        except ImportError as exc:
            logger.warning("TurboVecIndex: turbovec not installed (%s)", exc)
            return "DOWN"
        return "UP"

    # ------------------------------------------------------------------
    # IngestionVectorIndex contract
    # ------------------------------------------------------------------

    def _get_write_lock(self, tenant_id: UUID) -> asyncio.Lock:
        """Get or create a write lock for a tenant (lazy with master lock)."""
        if tenant_id not in self._tenant_write_locks:
            self._tenant_write_locks[tenant_id] = asyncio.Lock()
        return self._tenant_write_locks[tenant_id]

    def _get_persist_lock(self, tenant_id: UUID) -> asyncio.Lock:
        """Get or create a persist lock for a tenant (lazy with master lock)."""
        if tenant_id not in self._tenant_persist_locks:
            self._tenant_persist_locks[tenant_id] = asyncio.Lock()
        return self._tenant_persist_locks[tenant_id]

    async def add(self, tenant_id: UUID, chunks: list[Any]) -> int:
        """Index ``chunks`` (each must expose ``chunk_id``, ``embedding``)."""
        if not chunks:
            return 0
        async with self._get_write_lock(tenant_id):
            return await asyncio.to_thread(self._add_sync, tenant_id, chunks)

    async def query(
        self,
        tenant_id: UUID,
        embedding: list[float],
        k: int,
        allowlist: list[int] | None = None,
    ) -> list[tuple[int, float]]:
        if k <= 0:
            raise ValueError("TurboVecIndex.query: k must be positive")
        return await asyncio.to_thread(self._query_sync, tenant_id, embedding, k, allowlist)

    async def persist(self, tenant_id: UUID) -> None:
        async with self._get_persist_lock(tenant_id):
            await asyncio.to_thread(self._persist_sync, tenant_id)

    async def rebuild(self, tenant_id: UUID) -> None:
        await asyncio.to_thread(self._rebuild_sync, tenant_id)

    # ------------------------------------------------------------------
    # Sync implementation (offloaded via to_thread)
    # ------------------------------------------------------------------

    def _require_turbovec(self) -> Any:
        try:
            import turbovec
        except ImportError as exc:
            raise RuntimeError(
                "TurboVecIndex: 'turbovec' package not installed. "
                "Install with `pip install turbovec`. See "
                "https://pypi.org/project/turbovec/"
            ) from exc
        return turbovec

    def _index_path(self, tenant_id: UUID) -> Path:
        return self._home / f"{tenant_id}.tq"

    def _add_sync(self, tenant_id: UUID, chunks: list[Any]) -> int:
        turbovec = self._require_turbovec()
        try:
            import numpy as np
        except ImportError as exc:
            raise RuntimeError(
                "TurboVecIndex: numpy required (transitive dep of turbovec)"
            ) from exc

        first = chunks[0]
        dim = len(first.embedding)
        handle = self._handles.get(tenant_id)
        if handle is None:
            handle = self._ensure_handle(tenant_id, dim, turbovec)
        elif handle.dim and handle.dim != dim:
            raise ValueError(
                f"TurboVecIndex: dim mismatch for tenant {tenant_id}: "
                f"index has dim={handle.dim}, chunks have dim={dim}"
            )

        vectors = np.array([chunk.embedding for chunk in chunks], dtype=np.float32)
        handle.index.add(vectors)
        # Stash chunk-id → array-slot in metadata for downstream resolution.
        # turbovec assigns sequential internal slot ids; we record them.
        next_slot = handle.pending_writes
        for offset, chunk in enumerate(chunks):
            slot = next_slot + offset
            handle.metadata_by_chunk[slot] = {
                "chunk_id": int(chunk.chunk_id),
                **dict(getattr(chunk, "metadata", {})),
            }
        handle.pending_writes += len(chunks)
        return len(chunks)

    def _ensure_handle(self, tenant_id: UUID, dim: int, turbovec: Any) -> _IndexHandle:
        path = self._index_path(tenant_id)
        if path.exists():
            index = turbovec.TurboQuantIndex.load(str(path))
            handle = _IndexHandle(
                tenant_id=tenant_id,
                index=index,
                dim=dim,
                bit_width=self._bit_width,
            )
        else:
            index = turbovec.TurboQuantIndex(dim=dim, bit_width=self._bit_width)
            handle = _IndexHandle(
                tenant_id=tenant_id,
                index=index,
                dim=dim,
                bit_width=self._bit_width,
            )
        self._handles[tenant_id] = handle
        return handle

    def _query_sync(
        self,
        tenant_id: UUID,
        embedding: list[float],
        k: int,
        allowlist: list[int] | None,
    ) -> list[tuple[int, float]]:
        try:
            import numpy as np
        except ImportError as exc:
            raise RuntimeError("TurboVecIndex: numpy required") from exc
        handle = self._handles.get(tenant_id)
        if handle is None or handle.index is None:
            return []
        query = np.array(embedding, dtype=np.float32)
        # turbovec's basic TurboQuantIndex.search returns (scores, indices).
        scores, indices = handle.index.search(query, k=k)
        # Allowlist filtering is post-hoc here; native kernel allowlist is
        # in IdMapIndex. For MVP TurboQuantIndex we filter in Python.
        out: list[tuple[int, float]] = []
        allowed = set(allowlist) if allowlist else None
        for slot, score in zip(indices, scores, strict=False):
            slot_int = int(slot)
            meta = handle.metadata_by_chunk.get(slot_int)
            if meta is None:
                continue
            chunk_id = int(str(meta.get("chunk_id", slot_int)))
            if allowed is not None and chunk_id not in allowed:
                continue
            out.append((chunk_id, float(score)))
            if len(out) >= k:
                break
        return out

    def _persist_sync(self, tenant_id: UUID) -> None:
        handle = self._handles.get(tenant_id)
        if handle is None or handle.index is None:
            return
        path = self._index_path(tenant_id)
        handle.index.write(str(path))
        # Persist metadata sidecar (JSON next to .tq)
        import json

        sidecar = path.with_suffix(".tq.meta.json")
        sidecar.write_text(
            json.dumps(handle.metadata_by_chunk, default=str),
            encoding="utf-8",
        )

    def _rebuild_sync(self, tenant_id: UUID) -> None:
        turbovec = self._require_turbovec()
        path = self._index_path(tenant_id)
        if not path.exists():
            self._handles.pop(tenant_id, None)
            return
        index = turbovec.TurboQuantIndex.load(str(path))
        sidecar = path.with_suffix(".tq.meta.json")
        metadata: dict[int, dict[str, object]] = {}
        if sidecar.exists():
            import json

            raw = json.loads(sidecar.read_text(encoding="utf-8"))
            metadata = {int(k): v for k, v in raw.items()}
        # We don't know dim post-load without inspecting the index;
        # turbovec exposes index.dim — defensive default to 0 if missing.
        dim = getattr(index, "dim", 0)
        self._handles[tenant_id] = _IndexHandle(
            tenant_id=tenant_id,
            index=index,
            dim=dim,
            bit_width=self._bit_width,
            metadata_by_chunk=metadata,
        )
