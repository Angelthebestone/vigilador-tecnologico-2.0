"""Port WS-E: simulador de stakeholders criticos (inversor, regulador, etc.)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from vigilancia_multiagente.domain.evaluation_entities import StakeholderSimulation
from vigilancia_multiagente.domain.models import FinalReport


@runtime_checkable
class StakeholderSimulator(Protocol):
    async def simulate(
        self,
        report: FinalReport,
        stakeholder: str,
    ) -> StakeholderSimulation: ...
