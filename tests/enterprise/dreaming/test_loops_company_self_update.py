"""Tests for CompanySelfUpdateLoop — T056."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from vigilancia_multiagente.enterprise.dreaming.loops.company_self_update import (
    CompanySelfUpdateLoop,
)
from vigilancia_multiagente.enterprise.dreaming.models import DreamingContext


class FakeGapDetector:
    def __init__(self, gaps: list[dict[str, Any]]) -> None:
        self._gaps = gaps

    async def detect(self, tenant_id: str) -> list[dict[str, Any]]:
        return self._gaps


class FakeProposalGenerator:
    async def generate(self, gap: dict[str, Any]) -> dict[str, Any]:
        return {"section": gap.get("category", ""), "content": "new info"}


class FakeModifier:
    def __init__(self) -> None:
        self.applied: list[dict[str, Any]] = []

    async def apply(self, proposal: dict[str, Any]) -> None:
        self.applied.append(proposal)


def _ctx() -> DreamingContext:
    return DreamingContext(
        cycle_id="c1", started_at=datetime.now(UTC), tenant_id="t1", llm_available=True
    )


@pytest.mark.asyncio
async def test_detects_gaps() -> None:
    loop = CompanySelfUpdateLoop(
        FakeGapDetector([{"category": "systems"}]), FakeProposalGenerator(), FakeModifier()
    )
    result = await loop.run(_ctx())
    assert result["gaps_detected"] == 1


@pytest.mark.asyncio
async def test_generates_proposal() -> None:
    modifier = FakeModifier()
    loop = CompanySelfUpdateLoop(
        FakeGapDetector([{"category": "processes"}]), FakeProposalGenerator(), modifier
    )
    await loop.run(_ctx())
    assert len(modifier.applied) == 1


@pytest.mark.asyncio
async def test_applies_via_modifier() -> None:
    modifier = FakeModifier()
    loop = CompanySelfUpdateLoop(
        FakeGapDetector([{"category": "org"}, {"category": "sys"}]),
        FakeProposalGenerator(),
        modifier,
    )
    result = await loop.run(_ctx())
    assert result["proposals_applied"] == 2
    assert len(modifier.applied) == 2
