from __future__ import annotations

from typing import Any, Protocol

from vigilancia_multiagente.domain.ports.provider_registry import ProviderConfig
from vigilancia_multiagente.shared.mcp_dto import ToolExecutionResult


class ToolExecutor(Protocol):
    """Execute a named MCP tool via configured providers."""

    async def execute_tool(
        self, provider: ProviderConfig, tool_name: str, arguments: dict[str, Any]
    ) -> ToolExecutionResult: ...
