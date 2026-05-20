"""Ad-hoc MCP tool invocations extracted from HTTP routes."""

from __future__ import annotations

import logging
from typing import Any, cast
from uuid import UUID

from vigilancia_multiagente.domain.ports.provider_registry import ProviderRegistry
from vigilancia_multiagente.domain.ports.tool_executor import ToolExecutor

logger = logging.getLogger(__name__)


class AdHocResearchToolsService:
    def __init__(
        self,
        execution_client: ToolExecutor,
        provider_registry: ProviderRegistry,
    ) -> None:
        self._execution_client = execution_client
        self._provider_registry = provider_registry

    async def tool_results(
        self, provider_name: str, tool_name: str, arguments: dict[str, object]
    ) -> list | None:
        try:
            provider = self._provider_registry.get(provider_name)
            response = await self._execution_client.execute_tool(
                provider, tool_name, cast(dict[str, Any], arguments)
            )
        except Exception as exc:
            logger.warning("%s:%s failed: %s", provider_name, tool_name, exc)
            return None
        payload = response.payload
        for key in ("results", "items", "organic", "papers", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
        return []

    async def fetch_obsolescence_signals(
        self, session_id: UUID, tech: str
    ) -> tuple[list | None, list | None]:
        brave_results: list | None = None
        exa_results: list | None = None
        try:
            brave_provider = self._provider_registry.get("brave")
            brave_resp = await self._execution_client.execute_tool(
                brave_provider, "brave_news_search", {"query": tech}
            )
            brave_results = brave_resp.payload.get("results", [])
        except Exception as exc:
            logger.warning("Brave search failed for session %s: %s", session_id, exc)
        try:
            exa_provider = self._provider_registry.get("exa")
            exa_resp = await self._execution_client.execute_tool(
                exa_provider, "web_search_advanced_exa", {"query": tech}
            )
            exa_results = exa_resp.payload.get("results", [])
        except Exception as exc:
            logger.warning("Exa search failed for session %s: %s", session_id, exc)
        return brave_results, exa_results
