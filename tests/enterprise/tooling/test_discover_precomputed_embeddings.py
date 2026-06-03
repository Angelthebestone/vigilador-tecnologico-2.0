"""Tests for ToolRegistry pre-computed embeddings."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from vigilancia_multiagente.enterprise.tooling.tool_registry import ToolRegistry
from vigilancia_multiagente.enterprise.tooling.tool_wrapper import ToolWrapper


class MockTool(ToolWrapper):
    name = "mock_tool"
    domain = "test"
    requires_auth = False

    async def execute(self, tool_name: str, args: dict) -> dict:
        return {"status": "ok"}


@pytest.mark.asyncio
async def test_discover_uses_precomputed_embeddings() -> None:
    """Verify that discover() uses pre-computed embeddings and does not call embedding_gateway.embed for each tool."""
    mock_health_repo = AsyncMock()
    mock_health_repo.get_statuses_batch = AsyncMock(return_value={"mock_tool": "UP"})
    
    mock_embedding_gw = AsyncMock()
    # Only called once for the intent, not for each tool
    mock_embedding_gw.embed = AsyncMock(return_value=[0.5, 0.5])
    
    cache = AsyncMock()
    cache.set = AsyncMock()
    
    registry = ToolRegistry(
        tool_health_repo=mock_health_repo,
        embedding_gateway=mock_embedding_gw,
        embedding_cache=cache,
    )
    
    tool = MockTool()
    await registry.register(tool)
    
    # Reset mock to count calls during discover
    mock_embedding_gw.embed.reset_mock()
    
    tenant_id = uuid.uuid4()
    cards = await registry.discover(role="researcher", intent="test intent", tenant_id=tenant_id)
    
    # embed should only be called for the intent, not for the tool description
    assert mock_embedding_gw.embed.call_count == 1
    assert mock_embedding_gw.embed.call_args[0][0] == "test intent"
    assert len(cards) == 1
    assert cards[0].id == "mock_tool"


@pytest.mark.asyncio
async def test_discover_fallback_if_not_precomputed() -> None:
    """Verify that discover() falls back to computing embedding if not pre-computed."""
    mock_health_repo = AsyncMock()
    mock_health_repo.get_statuses_batch = AsyncMock(return_value={"mock_tool": "UP"})
    
    mock_embedding_gw = AsyncMock()
    mock_embedding_gw.embed = AsyncMock(return_value=[0.5, 0.5])
    
    registry = ToolRegistry(
        tool_health_repo=mock_health_repo,
        embedding_gateway=mock_embedding_gw,
        embedding_cache=None,
    )
    
    tool = MockTool()
    # Manually add to registry without calling register() to simulate missing pre-computation
    registry._tools[tool.name] = tool
    
    tenant_id = uuid.uuid4()
    cards = await registry.discover(role="researcher", intent="test intent", tenant_id=tenant_id)
    
    # embed should be called for intent AND for the tool description (fallback)
    assert mock_embedding_gw.embed.call_count == 2
    assert len(cards) == 1