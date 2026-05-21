"""Port WS-A: analisis de conflicto de intereses sobre metadatos de la fuente."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from vigilancia_multiagente.domain.evaluation_entities import ConflictOfInterest
from vigilancia_multiagente.domain.models import SourceRef


@runtime_checkable
class ConflictOfInterestAnalyzer(Protocol):
    async def analyze(self, source: SourceRef) -> ConflictOfInterest | None: ...
