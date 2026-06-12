"""Tests for SkillLearningLoop — T048."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from vigilancia_multiagente.enterprise.dreaming.loops.skill_learning import SkillLearningLoop
from vigilancia_multiagente.enterprise.dreaming.models import DreamingContext


class FakeDetector:
    def __init__(self, demos: list[dict[str, Any]]) -> None:
        self._demos = demos

    async def find_demonstrations(self, tenant_id: str) -> list[dict[str, Any]]:
        return self._demos


class FakeGenerator:
    async def generate_skill(self, demonstration: dict[str, Any]) -> dict[str, Any]:
        return {"name": f"skill_from_{demonstration['id']}", "steps": []}


class FakeRegistrar:
    def __init__(self) -> None:
        self.registered: list[dict[str, Any]] = []

    async def register(self, skill: dict[str, Any]) -> None:
        self.registered.append(skill)


def _ctx() -> DreamingContext:
    return DreamingContext(
        cycle_id="c1", started_at=datetime.now(UTC), tenant_id="t1", llm_available=True
    )


@pytest.mark.asyncio
async def test_detects_demonstrations() -> None:
    loop = SkillLearningLoop(FakeDetector([{"id": "d1"}]), FakeGenerator(), FakeRegistrar())
    result = await loop.run(_ctx())
    assert result["demonstrations_found"] == 1


@pytest.mark.asyncio
async def test_generates_skill() -> None:
    registrar = FakeRegistrar()
    loop = SkillLearningLoop(FakeDetector([{"id": "d1"}]), FakeGenerator(), registrar)
    await loop.run(_ctx())
    assert len(registrar.registered) == 1
    assert "skill_from_d1" in registrar.registered[0]["name"]


@pytest.mark.asyncio
async def test_registers_via_modifier() -> None:
    registrar = FakeRegistrar()
    loop = SkillLearningLoop(FakeDetector([{"id": "d1"}, {"id": "d2"}]), FakeGenerator(), registrar)
    result = await loop.run(_ctx())
    assert result["skills_created"] == 2
    assert len(registrar.registered) == 2
