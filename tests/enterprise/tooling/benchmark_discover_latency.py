"""Benchmark for ToolRegistry discover latency."""

from __future__ import annotations

import time
import uuid
from unittest.mock import AsyncMock

import pytest

from vigilancia_multiagente.enterprise.tooling.tool_registry import ToolRegistry
from vigilancia_multiagente.enterprise.tooling.tool_wrapper import ToolWrapper


class MockTool(ToolWrapper):
    def __init__(self, name: str):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    domain = "test"
    requires_auth = False

    async def execute(self, tool_name: str, args: dict) -> dict:
        return {"status": "ok"}


@pytest.mark.asyncio
async def test_discover_latency_under_200ms() -> None:
    """SC-002: discover() p95 latency should be < 200ms for warm cache."""
    mock_health_repo = AsyncMock()
    mock_health_repo.get_statuses_batch = AsyncMock(
        return_value={f"tool_{i}": "UP" for i in range(21)}
    )

    mock_embedding_gw = AsyncMock()
    mock_embedding_gw.embed = AsyncMock(return_value=[0.5] * 8)

    cache = AsyncMock()
    cache.set = AsyncMock()

    registry = ToolRegistry(
        tool_health_repo=mock_health_repo,
        embedding_gateway=mock_embedding_gw,
        embedding_cache=cache,
    )

    # Register 21 tools (simulating the current builtin tools count)
    for i in range(21):
        tool = MockTool(name=f"tool_{i}")
        await registry.register(tool)

    tenant_id = uuid.uuid4()
    latencies = []

    # Warm up
    await registry.discover(role="researcher", intent="test intent", tenant_id=tenant_id)

    # Measure 100 invocations
    for _ in range(100):
        start = time.perf_counter()
        await registry.discover(role="researcher", intent="test intent", tenant_id=tenant_id)
        end = time.perf_counter()
        latencies.append((end - start) * 1000)  # ms

    # Calculate p95
    latencies.sort()
    p95_index = int(len(latencies) * 0.95)
    p95_latency = latencies[p95_index]

    # Assert p95 latency is under 200ms (SC-002)
    # Note: In a real environment with async overhead, this might be slightly higher,
    # but with mocks it should be well under 200ms.
    assert p95_latency < 200.0, f"p95 latency {p95_latency:.2f}ms is >= 200ms"
