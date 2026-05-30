"""Tests for RegulatoryWatchPhase — T035."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from vigilancia_multiagente.enterprise.dreaming.models import DreamingContext, PhaseStatus
from vigilancia_multiagente.enterprise.dreaming.phases.regulatory_watch import (
    RegulatoryWatchPhase,
)


class FakeGeoConfig:
    @property
    def country(self) -> str:
        return "Colombia"

    @property
    def department(self) -> str:
        return "Santander"

    @property
    def municipality(self) -> str:
        return "Barrancabermeja"

    @property
    def sector(self) -> str:
        return "tecnologia"


class FakeSearcher:
    def __init__(self, results: list[dict[str, Any]] | None = None) -> None:
        self._results = results
        self.queries_received: list[str] = []

    async def search(self, query: str) -> list[dict[str, Any]]:
        self.queries_received.append(query)
        return self._results or []


class FakeProposalStore:
    def __init__(self) -> None:
        self.proposals: list[dict[str, Any]] = []
        self.uncertainties: list[tuple[str, str]] = []

    async def store_proposal(self, proposal: dict[str, Any]) -> None:
        self.proposals.append(proposal)

    async def store_uncertainty(self, topic: str, reason: str) -> None:
        self.uncertainties.append((topic, reason))


def _ctx() -> DreamingContext:
    return DreamingContext(
        cycle_id="c1", started_at=datetime.now(timezone.utc), tenant_id="t1", llm_available=True
    )


@pytest.mark.asyncio
async def test_builds_queries_by_geo() -> None:
    searcher = FakeSearcher(results=[])
    store = FakeProposalStore()
    phase = RegulatoryWatchPhase(FakeGeoConfig(), searcher, store)
    await phase.execute(_ctx())
    assert len(searcher.queries_received) == 3
    assert "Colombia" in searcher.queries_received[0]
    assert "Barrancabermeja" in searcher.queries_received[0]


@pytest.mark.asyncio
async def test_searches_official_sources() -> None:
    searcher = FakeSearcher(results=[{"source": "alcaldia", "citation": "Decreto 123", "summary": "x"}])
    store = FakeProposalStore()
    phase = RegulatoryWatchPhase(FakeGeoConfig(), searcher, store)
    await phase.execute(_ctx())
    assert len(store.proposals) == 3  # one per query


@pytest.mark.asyncio
async def test_generates_proposal_with_citations() -> None:
    searcher = FakeSearcher(results=[{"source": "gobernacion", "citation": "Res 456", "summary": "y"}])
    store = FakeProposalStore()
    phase = RegulatoryWatchPhase(FakeGeoConfig(), searcher, store)
    await phase.execute(_ctx())
    assert all(p.get("citation") for p in store.proposals)


@pytest.mark.asyncio
async def test_marks_uncertainty_when_no_source() -> None:
    searcher = FakeSearcher(results=[])
    store = FakeProposalStore()
    phase = RegulatoryWatchPhase(FakeGeoConfig(), searcher, store)
    result = await phase.execute(_ctx())
    assert result.metrics_dict["uncertainties"] == 3
    assert len(store.uncertainties) == 3
