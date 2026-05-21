"""Port WS-C: sintetizador de escenarios contrafactuales sobre el reporte borrador."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from vigilancia_multiagente.domain.evaluation_entities import CounterfactualScenario
from vigilancia_multiagente.domain.models import FinalReport


@runtime_checkable
class CounterfactualSynthesizer(Protocol):
    async def synthesize(
        self,
        report_draft: FinalReport,
        scenarios_n: int = 3,
    ) -> list[CounterfactualScenario]: ...
