"""Port WS-A: metrica de reproducibilidad para hallazgos tecnicos."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from vigilancia_multiagente.domain.evaluation_entities import ReproducibilityScore
from vigilancia_multiagente.domain.models import Finding


@runtime_checkable
class ReproducibilityChecker(Protocol):
    async def score(self, finding: Finding) -> ReproducibilityScore: ...
