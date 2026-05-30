"""Tests para ToolRegistry (F1.2)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest

from vigilancia_multiagente.enterprise.tooling.tool_card import ToolDocs, ToolSummary
from vigilancia_multiagente.enterprise.tooling.tool_registry import ToolRegistry
from vigilancia_multiagente.enterprise.tooling.tool_wrapper import HealthcheckResult

TENANT = UUID("00000000-0000-0000-0000-000000000001")


@dataclass
class FakeTool:
    name: str
    domain: str = "research"
    is_external_mcp: bool = False
    requires_auth: bool = False
    auth_env_var: str = ""
    description: str = "Short desc"
    cost_tier: str = "free"
    input_schema: dict = None
    output_schema: dict = None
    examples: list = None
    long_description: str = ""
    full_examples: list = None

    def __post_init__(self):
        self.input_schema = self.input_schema or {}
        self.output_schema = self.output_schema or {}
        self.examples = self.examples or []
        self.full_examples = self.full_examples or []

    async def healthcheck(self) -> HealthcheckResult:
        return HealthcheckResult(status="UP")

    async def execute(self, tool_name: str, args: dict) -> dict:
        return {}


def _make_registry() -> tuple[ToolRegistry, AsyncMock, AsyncMock]:
    health_repo = AsyncMock()
    health_repo.list_all = AsyncMock(return_value=[])
    health_repo.read_status = AsyncMock(return_value=None)
    embed_gw = AsyncMock()
    embed_gw.embed = AsyncMock(return_value=[0.0] * 768)
    registry = ToolRegistry(tool_health_repo=health_repo, embedding_gateway=embed_gw)
    return registry, health_repo, embed_gw


@pytest.mark.asyncio
async def test_register_5_tools():
    """Registro normal de 5 tools fake."""
    registry, _, _ = _make_registry()
    for i in range(5):
        await registry.register(FakeTool(name=f"tool_{i}"))
    cards = await registry.list_tools_for_role("research", TENANT)
    assert len(cards) == 5


@pytest.mark.asyncio
async def test_duplicate_name_raises():
    """Duplicado por name falla con ValueError."""
    registry, _, _ = _make_registry()
    await registry.register(FakeTool(name="dup"))
    with pytest.raises(ValueError, match="already registered"):
        await registry.register(FakeTool(name="dup"))


@pytest.mark.asyncio
async def test_list_tools_for_role_description_max_80():
    """list_tools_for_role retorna ToolCards con descripción ≤80 chars."""
    registry, _, _ = _make_registry()
    await registry.register(FakeTool(name="t1", description="A" * 80))
    cards = await registry.list_tools_for_role("research", TENANT)
    assert len(cards) == 1
    assert len(cards[0].description) <= 80


@pytest.mark.asyncio
async def test_get_summary():
    """get_summary retorna ficha resumida."""
    registry, _, _ = _make_registry()
    await registry.register(FakeTool(name="sum_tool", examples=["ex1", "ex2"]))
    summary = await registry.get_summary("sum_tool")
    assert isinstance(summary, ToolSummary)
    assert summary.card.id == "sum_tool"
    assert summary.examples == ["ex1", "ex2"]


@pytest.mark.asyncio
async def test_get_docs():
    """get_docs retorna contenido completo."""
    registry, _, _ = _make_registry()
    await registry.register(
        FakeTool(name="doc_tool", long_description="Full docs here", full_examples=["full_ex"])
    )
    docs = await registry.get_docs("doc_tool")
    assert isinstance(docs, ToolDocs)
    assert docs.long_description == "Full docs here"
    assert docs.full_examples == ["full_ex"]


@pytest.mark.asyncio
async def test_discover_orders_by_similarity():
    """discover('research') ordena por similitud usando embedding mock."""
    registry, _, embed_gw = _make_registry()

    # Tool A: embedding cercano al intent
    await registry.register(FakeTool(name="close_tool", description="research papers"))
    # Tool B: embedding lejano
    await registry.register(FakeTool(name="far_tool", description="cooking recipes"))

    call_count = [0]

    async def mock_embed(text, task_type=None):
        call_count[0] += 1
        if "research" in text:
            return [1.0] * 768
        return [0.0] * 768

    embed_gw.embed = mock_embed

    results = await registry.discover("research", "find research papers", TENANT)
    assert len(results) >= 2
    # El más similar debe estar primero
    assert results[0].id == "close_tool"


@pytest.mark.asyncio
async def test_gating_hides_tool_without_api_key():
    """Gating por API key faltante oculta tool."""
    registry, _, _ = _make_registry()
    await registry.register(
        FakeTool(name="gated", requires_auth=True, auth_env_var="FAKE_API_KEY_XYZ")
    )
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("FAKE_API_KEY_XYZ", None)
        cards = await registry.list_tools_for_role("research", TENANT)
    assert all(c.id != "gated" for c in cards)
