"""Performance test para ToolRegistry (F1.2)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from vigilancia_multiagente.enterprise.tooling.tool_registry import ToolRegistry
from vigilancia_multiagente.enterprise.tooling.tool_wrapper import HealthcheckResult

TENANT = UUID("00000000-0000-0000-0000-000000000001")


@dataclass
class SyntheticTool:
    name: str
    domain: str = "research"
    is_external_mcp: bool = False
    requires_auth: bool = False
    auth_env_var: str = ""
    description: str = "Synthetic tool for perf testing"
    cost_tier: str = "free"

    async def healthcheck(self) -> HealthcheckResult:
        return HealthcheckResult(status="UP")

    async def execute(self, tool_name: str, args: dict) -> dict:
        return {}


@pytest.mark.asyncio
async def test_list_tools_200_under_200ms():
    """Registrar 200 tools y medir list_tools_for_role ≤ 200 ms."""
    health_repo = AsyncMock()
    health_repo.read_status = AsyncMock(return_value=None)
    embed_gw = AsyncMock()
    registry = ToolRegistry(tool_health_repo=health_repo, embedding_gateway=embed_gw)

    for i in range(200):
        await registry.register(SyntheticTool(name=f"synth_{i:03d}"))

    start = time.perf_counter()
    cards = await registry.list_tools_for_role("research", TENANT)
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert len(cards) == 200
    assert elapsed_ms <= 200, f"list_tools_for_role took {elapsed_ms:.1f}ms (limit: 200ms)"
