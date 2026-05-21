"""Port WS-D: rastreo de linaje de ideas hasta la publicacion seminal."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from vigilancia_multiagente.domain.evaluation_entities import IdeaLineage
from vigilancia_multiagente.domain.models import SourceRef


@runtime_checkable
class IdeaLineageTracer(Protocol):
    async def trace(
        self,
        idea: str,
        sources: list[SourceRef],
    ) -> IdeaLineage: ...
