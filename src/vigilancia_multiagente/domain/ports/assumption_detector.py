"""Port WS-C: detector de asunciones implicitas en textos fuente."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from vigilancia_multiagente.domain.evaluation_entities import ImplicitAssumption
from vigilancia_multiagente.domain.models import Finding


@runtime_checkable
class AssumptionDetector(Protocol):
    async def detect(
        self,
        finding: Finding,
        source_text: str,
    ) -> list[ImplicitAssumption]: ...
