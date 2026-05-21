"""Port WS-E: prober de falsificacion sobre conclusiones del reporte."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from vigilancia_multiagente.domain.evaluation_entities import FalsificationScenario


@runtime_checkable
class FalsificationProber(Protocol):
    async def probe(self, conclusion: str) -> list[FalsificationScenario]:
        """Lista vacia marca la conclusion como no falsable (advertencia)."""
        ...
