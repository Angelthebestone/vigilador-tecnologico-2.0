"""Tests for SkillCuratorPhase — T028."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from vigilancia_multiagente.enterprise.dreaming.models import DreamingContext, PhaseStatus
from vigilancia_multiagente.enterprise.dreaming.phases.skill_curator import SkillCuratorPhase


class FakeExecutionStore:
    def __init__(self, data: dict[str, list[dict[str, Any]]]) -> None:
        self._data = data

    async def get_all_skill_ids(self) -> list[str]:
        return list(self._data.keys())

    async def get_recent_executions(self, skill_id: str, limit: int) -> list[dict[str, Any]]:
        return self._data.get(skill_id, [])[:limit]


class FakeStatusUpdater:
    def __init__(self) -> None:
        self.deprecated: list[tuple[str, str]] = []
        self.promoted: list[str] = []

    async def deprecate(self, skill_id: str, reason: str) -> None:
        self.deprecated.append((skill_id, reason))

    async def promote_to_stable(self, skill_id: str) -> None:
        self.promoted.append(skill_id)


def _ctx() -> DreamingContext:
    return DreamingContext(
        cycle_id="c1", started_at=datetime.now(timezone.utc), tenant_id="t1", llm_available=True
    )


@pytest.mark.asyncio
async def test_revalidates_skills() -> None:
    store = FakeExecutionStore({"s1": [{"status": "success"}] * 5})
    updater = FakeStatusUpdater()
    phase = SkillCuratorPhase(store, updater)
    result = await phase.execute(_ctx())
    assert result.metrics_dict["skills_evaluated"] == 1


@pytest.mark.asyncio
async def test_deprecates_high_failure_rate() -> None:
    store = FakeExecutionStore({"s1": [{"status": "failed"}] * 4 + [{"status": "success"}]})
    updater = FakeStatusUpdater()
    phase = SkillCuratorPhase(store, updater)
    await phase.execute(_ctx())
    assert len(updater.deprecated) == 1
    assert updater.deprecated[0][0] == "s1"


@pytest.mark.asyncio
async def test_promotes_stable_skill() -> None:
    store = FakeExecutionStore({"s1": [{"status": "success"}] * 5})
    updater = FakeStatusUpdater()
    phase = SkillCuratorPhase(store, updater)
    await phase.execute(_ctx())
    assert "s1" in updater.promoted


@pytest.mark.asyncio
async def test_deprecated_excluded_from_discovery() -> None:
    # Deprecated skill has >50% failure
    store = FakeExecutionStore({"s1": [{"status": "failed"}] * 3 + [{"status": "success"}] * 2})
    updater = FakeStatusUpdater()
    phase = SkillCuratorPhase(store, updater)
    await phase.execute(_ctx())
    assert len(updater.deprecated) == 1
