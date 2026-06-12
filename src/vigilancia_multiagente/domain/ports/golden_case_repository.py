"""Port WS-E: repositorio de golden cases y sus ejecuciones."""

from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID

from vigilancia_multiagente.domain.evaluation_entities import (
    GoldenCase,
    GoldenCaseRun,
)


@runtime_checkable
class GoldenCaseRepository(Protocol):
    async def list_active(self) -> list[GoldenCase]: ...

    async def record_run(self, run: GoldenCaseRun) -> None: ...

    async def recent_runs(self, case_id: UUID, limit: int = 20) -> list[GoldenCaseRun]: ...
