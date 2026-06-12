"""Tests for MemoryConsolidationPhase — T011."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from vigilancia_multiagente.enterprise.dreaming.models import DreamingContext, PhaseStatus
from vigilancia_multiagente.enterprise.dreaming.phases.memory_consolidation import (
    MemoryConsolidationPhase,
)


class FakeSessionStore:
    def __init__(self, sessions: list[dict[str, Any]]) -> None:
        self._sessions = sessions
        self.consolidated_ids: list[str] = []

    async def get_unconsolidated_sessions(self, tenant_id: str) -> list[dict[str, Any]]:
        return self._sessions

    async def mark_consolidated(self, session_ids: list[str]) -> None:
        self.consolidated_ids.extend(session_ids)


class FakeMemoryStore:
    def __init__(self) -> None:
        self.entries: list[dict[str, Any]] = []
        self._existing: set[str] = set()

    async def append(self, entry: dict[str, Any]) -> None:
        self.entries.append(entry)
        self._existing.add(entry.get("session_id", ""))

    async def exists(self, session_id: str) -> bool:
        return session_id in self._existing


class FakeSummarizer:
    async def summarize_session(self, session: dict[str, Any]) -> dict[str, Any]:
        return {"summary": f"Summary of {session['id']}", "entities": [], "decisions": []}


class FailingSummarizer:
    async def summarize_session(self, session: dict[str, Any]) -> dict[str, Any]:
        raise ValueError("Corrupt session data")


def _make_context() -> DreamingContext:
    return DreamingContext(
        cycle_id="test-001",
        started_at=datetime.now(UTC),
        tenant_id="tenant-1",
        llm_available=True,
    )


@pytest.mark.asyncio
async def test_collects_unconsolidated_sessions() -> None:
    sessions = [{"id": "s1", "data": "x"}, {"id": "s2", "data": "y"}]
    store = FakeSessionStore(sessions)
    memory = FakeMemoryStore()
    phase = MemoryConsolidationPhase(store, memory, FakeSummarizer())

    result = await phase.execute(_make_context())

    assert result.status == PhaseStatus.SUCCESS
    assert result.metrics_dict["sessions_found"] == 2
    assert result.metrics_dict["processed"] == 2


@pytest.mark.asyncio
async def test_compresses_via_llm() -> None:
    sessions = [{"id": "s1", "data": "content"}]
    store = FakeSessionStore(sessions)
    memory = FakeMemoryStore()
    phase = MemoryConsolidationPhase(store, memory, FakeSummarizer())

    await phase.execute(_make_context())

    assert len(memory.entries) == 1
    assert "Summary of s1" in memory.entries[0]["summary"]


@pytest.mark.asyncio
async def test_marks_sessions_consolidated() -> None:
    sessions = [{"id": "s1"}, {"id": "s2"}]
    store = FakeSessionStore(sessions)
    memory = FakeMemoryStore()
    phase = MemoryConsolidationPhase(store, memory, FakeSummarizer())

    await phase.execute(_make_context())

    assert set(store.consolidated_ids) == {"s1", "s2"}


@pytest.mark.asyncio
async def test_idempotent_no_duplicates() -> None:
    sessions = [{"id": "s1"}]
    store = FakeSessionStore(sessions)
    memory = FakeMemoryStore()
    phase = MemoryConsolidationPhase(store, memory, FakeSummarizer())

    await phase.execute(_make_context())
    # Second run: s1 already exists in memory
    store.consolidated_ids.clear()
    result = await phase.execute(_make_context())

    assert len(memory.entries) == 1  # no duplicate
    assert result.metrics_dict["skipped_duplicates"] == 1


@pytest.mark.asyncio
async def test_corrupt_sessions_skipped_with_error() -> None:
    sessions = [{"id": "s1"}, {"id": "s2"}]
    store = FakeSessionStore(sessions)
    memory = FakeMemoryStore()
    phase = MemoryConsolidationPhase(store, memory, FailingSummarizer())

    result = await phase.execute(_make_context())

    assert result.status == PhaseStatus.SUCCESS
    assert result.metrics_dict["errors"] == 2
    assert len(memory.entries) == 0
