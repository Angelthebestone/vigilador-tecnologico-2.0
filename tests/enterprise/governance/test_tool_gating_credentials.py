"""Tests de verificación tool-gating por credenciales (T018/T019).

Verifica que `_passes_gating()` en ToolRegistry cumple FR-016/FR-017:
- Tools con requires_auth=True sin API key → excluidas.
- Tools con requires_auth=False → siempre visibles.
- Query pura sin side-effects (CQS).
NO modifica tool_registry.py.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest

from vigilancia_multiagente.enterprise.tooling.tool_registry import ToolRegistry
from vigilancia_multiagente.enterprise.tooling.tool_wrapper import HealthcheckResult

TENANT = UUID("00000000-0000-0000-0000-000000000001")


@dataclass
class FakeToolGating:
    name: str
    domain: str = "research"
    is_external_mcp: bool = False
    requires_auth: bool = False
    auth_env_var: str = ""
    description: str = "Test tool"
    cost_tier: str = "free"

    async def healthcheck(self) -> HealthcheckResult:
        return HealthcheckResult(status="UP")

    async def execute(self, tool_name: str, args: dict[str, object]) -> dict[str, object]:
        return {}


def _make_registry() -> ToolRegistry:
    health_repo = AsyncMock()
    health_repo.read_status = AsyncMock(return_value=None)
    embed_gw = AsyncMock()
    embed_gw.embed = AsyncMock(return_value=[0.0] * 768)
    return ToolRegistry(tool_health_repo=health_repo, embedding_gateway=embed_gw)


@pytest.mark.asyncio
async def test_sc007_only_tools_with_key_visible() -> None:
    """SC-007: 10 tools (5 con key, 5 sin) → solo 5 con key + las sin auth visibles."""
    registry = _make_registry()

    # 5 tools que requieren auth CON key configurada
    for i in range(5):
        tool = FakeToolGating(
            name=f"with_key_{i}",
            requires_auth=True,
            auth_env_var=f"TOOL_KEY_{i}",
        )
        await registry.register(tool)

    # 5 tools que requieren auth SIN key configurada
    for i in range(5):
        tool = FakeToolGating(
            name=f"no_key_{i}",
            requires_auth=True,
            auth_env_var=f"MISSING_KEY_{i}",
        )
        await registry.register(tool)

    # Configurar env vars solo para las primeras 5
    env_patch = {f"TOOL_KEY_{i}": "sk-test-value" for i in range(5)}
    with patch.dict(os.environ, env_patch, clear=False):
        cards = await registry.list_tools_for_role("analyst", TENANT)

    names = {c.id for c in cards}
    # Las 5 con key deben estar
    for i in range(5):
        assert f"with_key_{i}" in names, f"with_key_{i} should be visible"
    # Las 5 sin key NO deben estar
    for i in range(5):
        assert f"no_key_{i}" not in names, f"no_key_{i} should be excluded"


@pytest.mark.asyncio
async def test_tool_without_requires_auth_always_visible() -> None:
    """FR-016: tool con requires_auth=False siempre aparece."""
    registry = _make_registry()
    tool = FakeToolGating(name="free_tool", requires_auth=False)
    await registry.register(tool)

    cards = await registry.list_tools_for_role("analyst", TENANT)
    assert any(c.id == "free_tool" for c in cards)


@pytest.mark.asyncio
async def test_env_change_reflected_immediately() -> None:
    """Cambio de entorno (key añadida) refleja inmediatamente en siguiente query."""
    registry = _make_registry()
    tool = FakeToolGating(name="dynamic_tool", requires_auth=True, auth_env_var="DYNAMIC_KEY")
    await registry.register(tool)

    # Sin key → no visible
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("DYNAMIC_KEY", None)
        cards = await registry.list_tools_for_role("analyst", TENANT)
        assert not any(c.id == "dynamic_tool" for c in cards)

    # Con key → visible
    with patch.dict(os.environ, {"DYNAMIC_KEY": "value"}, clear=False):
        cards = await registry.list_tools_for_role("analyst", TENANT)
        assert any(c.id == "dynamic_tool" for c in cards)


@pytest.mark.asyncio
async def test_gating_is_query_pure_no_side_effects() -> None:
    """FR-017/CQS: _passes_gating es query pura sin side-effects."""
    registry = _make_registry()
    tool = FakeToolGating(name="pure_tool", requires_auth=True, auth_env_var="PURE_KEY")
    await registry.register(tool)

    env_before = dict(os.environ)
    with patch.dict(os.environ, {"PURE_KEY": "val"}, clear=False):
        await registry.list_tools_for_role("analyst", TENANT)
        await registry.list_tools_for_role("analyst", TENANT)
    # Environment unchanged (no side effects from gating)
    assert os.environ.get("PURE_KEY") == env_before.get("PURE_KEY")
