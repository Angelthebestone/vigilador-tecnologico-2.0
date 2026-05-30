"""Tests for RegulatoryWatcherLoop — T058."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from vigilancia_multiagente.enterprise.dreaming.loops.regulatory_watcher import (
    RegulatoryWatcherLoop,
)
from vigilancia_multiagente.enterprise.dreaming.models import DreamingContext


class FakeSearchEngine:
    def __init__(self, results: list[dict[str, Any]]) -> None:
        self._results = results

    async def search_by_geo(
        self, country: str, department: str, municipality: str, sector: str
    ) -> list[dict[str, Any]]:
        return self._results


class FakeProposalWriter:
    def __init__(self) -> None:
        self.proposals: list[dict[str, Any]] = []
        self.uncertainties: list[tuple[str, str]] = []

    async def write_proposal(self, finding: dict[str, Any]) -> None:
        self.proposals.append(finding)

    async def write_uncertainty(self, topic: str, reason: str) -> None:
        self.uncertainties.append((topic, reason))


def _ctx() -> DreamingContext:
    return DreamingContext(
        cycle_id="c1", started_at=datetime.now(timezone.utc), tenant_id="t1", llm_available=True
    )


@pytest.mark.asyncio
async def test_searches_by_geo() -> None:
    engine = FakeSearchEngine([{"topic": "tax", "citation": "Decreto 1"}])
    writer = FakeProposalWriter()
    loop = RegulatoryWatcherLoop(engine, writer, "CO", "Santander", "Bga", "tech")
    result = await loop.run(_ctx())
    assert result["proposals"] == 1


@pytest.mark.asyncio
async def test_proposal_with_citations() -> None:
    engine = FakeSearchEngine([{"topic": "labor", "citation": "Ley 100"}])
    writer = FakeProposalWriter()
    loop = RegulatoryWatcherLoop(engine, writer, "CO", "Santander", "Bga", "tech")
    await loop.run(_ctx())
    assert writer.proposals[0]["citation"] == "Ley 100"


@pytest.mark.asyncio
async def test_marks_uncertainty_when_no_source() -> None:
    engine = FakeSearchEngine([])
    writer = FakeProposalWriter()
    loop = RegulatoryWatcherLoop(engine, writer, "CO", "Santander", "Bga", "tech")
    result = await loop.run(_ctx())
    assert result["uncertainties"] == 1
    assert len(writer.uncertainties) == 1
