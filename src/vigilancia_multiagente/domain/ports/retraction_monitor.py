"""Port WS-A: monitor de retractaciones (Retraction Watch, PubMed)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from vigilancia_multiagente.domain.evaluation_entities import RetractionRecord


@runtime_checkable
class RetractionMonitor(Protocol):
    async def is_retracted(self, doi: str) -> RetractionRecord | None: ...

    async def daily_sync(self) -> int:
        """Retorna el numero de nuevos registros sincronizados."""
        ...
