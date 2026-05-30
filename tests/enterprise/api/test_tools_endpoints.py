"""T036 - Tests para endpoints de tools enterprise."""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import UUID

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from vigilancia_multiagente.enterprise.tooling.tool_card import ToolCard
from vigilancia_multiagente.enterprise.tooling.tool_registry import ToolRegistry

TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture
def mock_tool_registry():
    registry = AsyncMock(spec=ToolRegistry)
    registry.list_tools_for_role = AsyncMock(
        return_value=[
            ToolCard(
                id="serper",
                description="Web search via Serper API",
                domains=["search"],
                requires_auth=True,
                cost_tier="low",
                status="UP",
            ),
            ToolCard(
                id="arxiv",
                description="Academic paper search",
                domains=["research"],
                requires_auth=False,
                cost_tier="free",
                status="UP",
            ),
        ]
    )
    return registry


@pytest.fixture
def mock_tool_registry_with_unconfigured():
    registry = AsyncMock(spec=ToolRegistry)
    registry.list_tools_for_role = AsyncMock(
        return_value=[
            ToolCard(
                id="serper",
                description="Web search via Serper API",
                domains=["search"],
                requires_auth=True,
                cost_tier="low",
                status="UNCONFIGURED",
            ),
        ]
    )
    return registry


@pytest.fixture
def mock_tool_registry_with_down():
    """Registry que incluye una tool DOWN — no debe aparecer en listado público."""
    registry = AsyncMock(spec=ToolRegistry)
    registry.list_tools_for_role = AsyncMock(
        return_value=[
            ToolCard(
                id="arxiv",
                description="Academic paper search",
                domains=["research"],
                requires_auth=False,
                cost_tier="free",
                status="UP",
            ),
            # DOWN tool — el endpoint debe filtrarla
            ToolCard(
                id="broken_tool",
                description="This tool is down",
                domains=["misc"],
                requires_auth=False,
                cost_tier="free",
                status="DOWN",
            ),
        ]
    )
    return registry


@pytest.fixture
def app(mock_tool_registry):
    from vigilancia_multiagente.api.app import create_app

    application = create_app()
    application.state.tool_registry = mock_tool_registry
    return application


@pytest_asyncio.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_get_tools_lists_with_detail_card(client, mock_tool_registry):
    """GET /api/v2/enterprise/tools lista tools con detail=card."""
    resp = await client.get("/api/v2/enterprise/tools", params={"detail": "card"})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    # Cada item tiene los campos de ToolCard
    for item in data:
        assert "id" in item
        assert "description" in item
        assert "status" in item


@pytest.mark.asyncio
async def test_tool_requires_key_env_empty_returns_unconfigured(
    mock_tool_registry_with_unconfigured,
):
    """Tool con requires_key y env vacío retorna status=UNCONFIGURED."""
    from vigilancia_multiagente.api.app import create_app

    application = create_app()
    application.state.tool_registry = mock_tool_registry_with_unconfigured

    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get("/api/v2/enterprise/tools", params={"detail": "card"})

    assert resp.status_code == 200
    data = resp.json()
    unconfigured = [t for t in data if t.get("status") == "UNCONFIGURED"]
    assert len(unconfigured) >= 1


@pytest.mark.asyncio
async def test_tool_down_not_in_public_listing(mock_tool_registry_with_down):
    """Tool DOWN no aparece en listado público."""
    from vigilancia_multiagente.api.app import create_app

    application = create_app()
    application.state.tool_registry = mock_tool_registry_with_down

    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get("/api/v2/enterprise/tools", params={"detail": "card"})

    assert resp.status_code == 200
    data = resp.json()
    down_tools = [t for t in data if t.get("status") == "DOWN"]
    assert len(down_tools) == 0
