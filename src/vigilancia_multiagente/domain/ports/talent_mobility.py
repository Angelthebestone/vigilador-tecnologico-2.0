"""Port WS-D: analizador de movilidad de talento (academia <-> industria)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from vigilancia_multiagente.domain.evaluation_entities import TalentMobility


@runtime_checkable
class TalentMobilityAnalyzer(Protocol):
    async def analyze(self, author_ids: list[str]) -> list[TalentMobility]: ...
