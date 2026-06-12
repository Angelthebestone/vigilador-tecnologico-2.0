"""Vector index ports (DIP boundaries).

Two protocols co-located here:

* :class:`VectorIndex` — the original session-scoped surface used by the 2.0
  pipeline (postgres pgvector). Only ``upsert`` / ``list_by_session``.
* :class:`IngestionVectorIndex` — the spec 021 D1-revisada native ingestion
  surface backed by TurboVec (``add``/``query``/``persist``/``rebuild``).

Both are runtime-checkable Protocols so adapters plug in via DIP. They are
intentionally separate because each models a distinct lifecycle: session
vectors are write-mostly with limited reads; ingestion vectors are
write-once-then-read-heavy across the corpus.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable
from uuid import UUID


@runtime_checkable
class VectorIndex(Protocol):
    """Vector similarity search and upsert (session-scoped, 2.0)."""

    async def upsert(self, record: Any) -> None: ...

    async def list_by_session(self, session_id: Any, limit: int = 100) -> list[Any]: ...


@runtime_checkable
class IngestionVectorIndex(Protocol):
    """Native ingestion-side index (Spec 021 D1-revisada — TurboVec).

    Backed by a quantized vector store running in-process. Implementations
    persist per tenant to ``~/.vigilador/turbovec/<tenant>.tq`` so each
    tenant's corpus is isolated on disk.

    The protocol is async to match how ingestion already uses it (the
    actual quantizer is sync; adapters offload to ``asyncio.to_thread``).

    Notation: ``Chunk`` is a domain-side dataclass-like with the fields
    ``chunk_id: int`` (uint64), ``embedding: list[float]``,
    ``metadata: dict[str, object]``. Adapters convert to whatever native
    layout they need.
    """

    async def add(self, tenant_id: UUID, chunks: list[Any]) -> int:
        """Index ``chunks`` for ``tenant_id``; returns the count actually added."""
        ...

    async def query(
        self,
        tenant_id: UUID,
        embedding: list[float],
        k: int,
        allowlist: list[int] | None = None,
    ) -> list[tuple[int, float]]:
        """Top-``k`` neighbors as ``(chunk_id, score)`` tuples (highest first).

        ``allowlist``: optional ACL-precomputed slot ids; the index honors
        the filter at the kernel level (FR-014).
        """
        ...

    async def persist(self, tenant_id: UUID) -> None:
        """Flush in-memory index to disk for ``tenant_id``."""
        ...

    async def rebuild(self, tenant_id: UUID) -> None:
        """Drop the in-memory state and reload from disk."""
        ...

    async def healthcheck(self) -> str:
        """Return ``"UP"`` / ``"DOWN"`` / ``"UNCONFIGURED"`` for monitoring."""
        ...
