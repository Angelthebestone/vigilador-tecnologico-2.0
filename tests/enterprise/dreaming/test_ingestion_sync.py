"""Tests for IngestionSyncPhase — T014."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from vigilancia_multiagente.enterprise.dreaming.models import DreamingContext, PhaseStatus
from vigilancia_multiagente.enterprise.dreaming.phases.ingestion_sync import IngestionSyncPhase


class FakeConnector:
    def __init__(
        self, connector_id: str, docs: list[dict[str, Any]], fail: bool = False
    ) -> None:
        self._connector_id = connector_id
        self._docs = docs
        self._fail = fail
        self.indexed_count = 0

    @property
    def connector_id(self) -> str:
        return self._connector_id

    async def fetch_new_documents(self, since: datetime | None) -> list[dict[str, Any]]:
        if self._fail:
            raise ConnectionError("Connector unavailable")
        return self._docs

    async def index_documents(self, documents: list[dict[str, Any]]) -> int:
        self.indexed_count = len(documents)
        return len(documents)


class FakeCheckpointStore:
    def __init__(self) -> None:
        self._checkpoints: dict[str, datetime] = {}

    async def get_last_sync(self, connector_id: str) -> datetime | None:
        return self._checkpoints.get(connector_id)

    async def set_last_sync(self, connector_id: str, ts: datetime) -> None:
        self._checkpoints[connector_id] = ts


def _make_context() -> DreamingContext:
    return DreamingContext(
        cycle_id="test-002",
        started_at=datetime.now(timezone.utc),
        tenant_id="tenant-1",
        llm_available=True,
    )


@pytest.mark.asyncio
async def test_iterates_configured_connectors() -> None:
    c1 = FakeConnector("drive", [{"id": "d1"}])
    c2 = FakeConnector("onedrive", [{"id": "d2"}])
    checkpoint = FakeCheckpointStore()
    phase = IngestionSyncPhase([c1, c2], checkpoint)

    result = await phase.execute(_make_context())

    assert result.status == PhaseStatus.SUCCESS
    assert result.metrics_dict["documents_indexed"] == 2


@pytest.mark.asyncio
async def test_processes_only_new_documents() -> None:
    c1 = FakeConnector("drive", [{"id": "d1"}])
    checkpoint = FakeCheckpointStore()
    phase = IngestionSyncPhase([c1], checkpoint)

    await phase.execute(_make_context())
    # Second run: connector returns empty (simulating no new docs)
    c1._docs = []
    result = await phase.execute(_make_context())

    assert result.metrics_dict["documents_indexed"] == 0


@pytest.mark.asyncio
async def test_updates_checkpoint_after_sync() -> None:
    c1 = FakeConnector("drive", [{"id": "d1"}])
    checkpoint = FakeCheckpointStore()
    phase = IngestionSyncPhase([c1], checkpoint)

    await phase.execute(_make_context())

    assert "drive" in checkpoint._checkpoints


@pytest.mark.asyncio
async def test_connector_failure_does_not_stop_others() -> None:
    c1 = FakeConnector("failing", [], fail=True)
    c2 = FakeConnector("working", [{"id": "d1"}])
    checkpoint = FakeCheckpointStore()
    phase = IngestionSyncPhase([c1, c2], checkpoint)

    result = await phase.execute(_make_context())

    assert result.metrics_dict["connector_errors"] == 1
    assert result.metrics_dict["documents_indexed"] == 1


@pytest.mark.asyncio
async def test_no_changes_zero_documents() -> None:
    c1 = FakeConnector("drive", [])
    checkpoint = FakeCheckpointStore()
    phase = IngestionSyncPhase([c1], checkpoint)

    result = await phase.execute(_make_context())

    assert result.metrics_dict["documents_indexed"] == 0
