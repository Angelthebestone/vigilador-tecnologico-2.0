"""Port WS-D: constructor de redes de colaboracion (co-autores, co-inventores)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from vigilancia_multiagente.domain.evaluation_entities import CollaborationNetwork
from vigilancia_multiagente.domain.models import SourceRef


@runtime_checkable
class CollaborationNetworkBuilder(Protocol):
    async def build(self, sources: list[SourceRef]) -> CollaborationNetwork: ...

    def detect_bubbles(
        self,
        network: CollaborationNetwork,
        max_bubble_size: int = 8,
    ) -> list[list[str]]: ...
