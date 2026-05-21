"""Port WS-B: motor de busqueda hibrida (BM25 + embeddings)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from vigilancia_multiagente.domain.evaluation_entities import HybridSearchQuery
from vigilancia_multiagente.domain.models import SourceRef


@runtime_checkable
class HybridSearchEngine(Protocol):
    async def search(
        self,
        query: HybridSearchQuery,
        candidates: list[SourceRef],
        top_k: int = 10,
    ) -> list[SourceRef]: ...
