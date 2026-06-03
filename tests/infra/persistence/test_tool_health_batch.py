"""Tests for ToolHealthRepository batch operations."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import pytest

from vigilancia_multiagente.infra.persistence.tool_health_repository import (
    ToolHealthRepository,
    ToolHealthRow,
)


class FakeResult:
    def __init__(self, rows: list[dict[str, object]] | None = None) -> None:
        self._rows = rows or []

    def mappings(self) -> "FakeResult":
        return self

    def all(self) -> list[dict[str, object]]:
        return self._rows


class FakeDBSession:
    def __init__(self, results: list[FakeResult] | None = None) -> None:
        self.results = results or []
        self.executed: list[tuple[str, dict[str, object]]] = []

    async def execute(self, statement: object, params: dict[str, object]) -> FakeResult:
        self.executed.append((str(statement), params))
        if self.results:
            return self.results.pop(0)
        return FakeResult()

    async def commit(self) -> None:
        pass


class FakeDatabase:
    def __init__(self, results: list[FakeResult] | None = None) -> None:
        self.session_obj = FakeDBSession(results)

    @asynccontextmanager
    async def session(self):
        yield self.session_obj


@pytest.mark.asyncio
async def test_get_statuses_batch_returns_dict() -> None:
    """Verify get_statuses_batch returns a dict of name -> status in a single query."""
    db = FakeDatabase([
        FakeResult([
            {"name": "tool_a", "status": "UP"},
            {"name": "tool_b", "status": "DOWN"},
        ])
    ])
    repo = ToolHealthRepository(db)
    tenant_id = uuid.uuid4()
    
    # Act
    result = await repo.get_statuses_batch(["tool_a", "tool_b", "tool_c"], tenant_id)
    
    # Assert
    assert result == {"tool_a": "UP", "tool_b": "DOWN"}
    # tool_c is not in DB, so it's correctly omitted from the result


@pytest.mark.asyncio
async def test_get_statuses_batch_empty_list() -> None:
    """Verify get_statuses_batch handles empty list gracefully."""
    db = FakeDatabase()
    repo = ToolHealthRepository(db)
    tenant_id = uuid.uuid4()
    
    result = await repo.get_statuses_batch([], tenant_id)
    assert result == {}
