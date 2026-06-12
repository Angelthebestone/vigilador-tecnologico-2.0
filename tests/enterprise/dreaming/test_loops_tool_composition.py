"""Tests for ToolCompositionLoop — T054."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from vigilancia_multiagente.enterprise.dreaming.loops.tool_composition import ToolCompositionLoop
from vigilancia_multiagente.enterprise.dreaming.models import DreamingContext


class FakeSequenceDetector:
    def __init__(self, sequences: list[dict[str, Any]]) -> None:
        self._sequences = sequences

    async def find_repeated_sequences(
        self, tenant_id: str, min_occurrences: int, days: int
    ) -> list[dict[str, Any]]:
        return self._sequences


class FakeBuilder:
    async def build(self, sequence: dict[str, Any]) -> dict[str, Any]:
        return {"name": f"composed_{sequence['id']}", "tools": sequence.get("tools", [])}


class FakeSkillStore:
    def __init__(self, existing: set[str] | None = None) -> None:
        self._existing = existing or set()
        self.saved: list[dict[str, Any]] = []
        self.superseded: list[tuple[str, str]] = []

    async def exists(self, skill_name: str) -> bool:
        return skill_name in self._existing

    async def save(self, skill: dict[str, Any]) -> None:
        self.saved.append(skill)

    async def mark_superseded(self, skill_name: str, by: str) -> None:
        self.superseded.append((skill_name, by))


def _ctx() -> DreamingContext:
    return DreamingContext(
        cycle_id="c1", started_at=datetime.now(UTC), tenant_id="t1", llm_available=True
    )


@pytest.mark.asyncio
async def test_detects_repeated_sequences() -> None:
    detector = FakeSequenceDetector([{"id": "seq1", "tools": ["a", "b"]}])
    loop = ToolCompositionLoop(detector, FakeBuilder(), FakeSkillStore())
    result = await loop.run(_ctx())
    assert result["sequences_detected"] == 1


@pytest.mark.asyncio
async def test_generates_composed_skill() -> None:
    detector = FakeSequenceDetector([{"id": "seq1", "tools": ["a", "b"]}])
    store = FakeSkillStore()
    loop = ToolCompositionLoop(detector, FakeBuilder(), store)
    await loop.run(_ctx())
    assert len(store.saved) == 1
    assert store.saved[0]["name"] == "composed_seq1"


@pytest.mark.asyncio
async def test_never_overwrites_existing_skill() -> None:
    detector = FakeSequenceDetector([{"id": "seq1"}])
    store = FakeSkillStore(existing={"composed_seq1"})
    loop = ToolCompositionLoop(detector, FakeBuilder(), store)
    result = await loop.run(_ctx())
    assert result["skipped_conflicts"] == 1
    assert len(store.saved) == 0
