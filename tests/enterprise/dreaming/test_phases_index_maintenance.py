"""Tests for IndexMaintenancePhase — T038."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from vigilancia_multiagente.enterprise.dreaming.models import DreamingContext, PhaseStatus
from vigilancia_multiagente.enterprise.dreaming.phases.index_maintenance import (
    IndexMaintenancePhase,
)


class FakeMaintainer:
    async def get_stats(self) -> dict[str, Any]:
        return {"size": 1000, "vectors": 500, "fragmentation": 0.2}

    async def vacuum_compact(self) -> dict[str, Any]:
        return {"size": 800, "vectors": 480, "fragmentation": 0.05}


def _ctx() -> DreamingContext:
    return DreamingContext(
        cycle_id="c1", started_at=datetime.now(UTC), tenant_id="t1", llm_available=True
    )


@pytest.mark.asyncio
async def test_vacuum_compact_executes() -> None:
    phase = IndexMaintenancePhase(FakeMaintainer())
    result = await phase.execute(_ctx())
    assert result.status == PhaseStatus.SUCCESS


@pytest.mark.asyncio
async def test_records_pre_post_metrics() -> None:
    phase = IndexMaintenancePhase(FakeMaintainer())
    result = await phase.execute(_ctx())
    assert result.metrics_dict["pre"]["size"] == 1000
    assert result.metrics_dict["post"]["size"] == 800
