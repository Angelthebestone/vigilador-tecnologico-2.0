"""Port WS-B: deduplicacion semantica profunda de fuentes."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from vigilancia_multiagente.domain.evaluation_entities import DedupedSource
from vigilancia_multiagente.domain.models import SourceRef


@runtime_checkable
class SemanticDeduplicator(Protocol):
    async def deduplicate(
        self,
        sources: list[SourceRef],
        threshold: float = 0.92,
    ) -> list[DedupedSource]: ...
