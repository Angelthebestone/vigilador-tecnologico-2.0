"""Port WS-E: ejecutor de golden cases en modo sandbox."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from vigilancia_multiagente.domain.evaluation_entities import (
    GoldenCase,
    GoldenCaseRun,
)


@runtime_checkable
class GoldenCaseRunner(Protocol):
    async def run_case(self, case: GoldenCase) -> GoldenCaseRun: ...

    async def run_all(self) -> list[GoldenCaseRun]: ...
