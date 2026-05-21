"""Port WS-D: analizador de brechas de patentamiento (ciencia vs patentes)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from vigilancia_multiagente.domain.evaluation_entities import PatentingGap


@runtime_checkable
class PatentingGapAnalyzer(Protocol):
    async def analyze(self, subdomains: list[str]) -> list[PatentingGap]: ...
