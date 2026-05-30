"""Phase 7 — Index maintenance: vacuum/compact vector index."""

from __future__ import annotations

import time
from typing import Any, Protocol

from vigilancia_multiagente.enterprise.dreaming.models import (
    DreamingContext,
    PhaseResult,
    PhaseStatus,
)


class VectorIndexMaintainer(Protocol):
    """Port for vector index maintenance operations."""

    async def get_stats(self) -> dict[str, Any]: ...

    async def vacuum_compact(self) -> dict[str, Any]: ...


class IndexMaintenancePhase:
    """Executes vacuum/compact on vector index and records pre/post metrics."""

    def __init__(self, maintainer: VectorIndexMaintainer) -> None:
        self._maintainer = maintainer

    @property
    def name(self) -> str:
        return "index_maintenance"

    async def execute(self, context: DreamingContext) -> PhaseResult:
        t0 = time.perf_counter()
        pre_stats = await self._maintainer.get_stats()
        post_stats = await self._maintainer.vacuum_compact()
        duration_ms = (time.perf_counter() - t0) * 1000
        return PhaseResult(
            phase_name=self.name,
            status=PhaseStatus.SUCCESS,
            duration_ms=duration_ms,
            metrics_dict={"pre": pre_stats, "post": post_stats},
        )
