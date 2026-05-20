"""Sandbox MCP helpers extracted from BaseBranchAgent."""

from __future__ import annotations

from typing import Any

from vigilancia_multiagente.domain.ports.provider_registry import ProviderRegistry
from vigilancia_multiagente.domain.ports.tool_executor import ToolExecutor


async def execute_code(
    execution_client: ToolExecutor,
    provider_registry: ProviderRegistry,
    code: str,
    timeout: int = 120,
) -> dict[str, Any]:
    provider = provider_registry.get("sandbox")
    execution = await execution_client.execute_tool(
        provider, "execute_code", {"code": code, "timeout": timeout}
    )
    return execution.payload


async def list_sandbox_libraries(
    execution_client: ToolExecutor,
    provider_registry: ProviderRegistry,
) -> dict[str, Any]:
    provider = provider_registry.get("sandbox")
    execution = await execution_client.execute_tool(provider, "list_libraries", {})
    return execution.payload


async def visualize_data(
    execution_client: ToolExecutor,
    provider_registry: ProviderRegistry,
    data: dict[str, Any],
    plot_type: str,
    format: str = "png",
) -> dict[str, Any]:
    provider = provider_registry.get("sandbox")
    execution = await execution_client.execute_tool(
        provider,
        "visualize",
        {"data": data, "plot_type": plot_type, "format": format},
    )
    return execution.payload
