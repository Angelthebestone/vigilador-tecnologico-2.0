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
        schema_registry: object | None = None,
        ws_b_enabled: bool = False,
    ) -> None:
        self._execution_client = execution_client
        self._provider_registry = provider_registry
        self._schema_registry = schema_registry
        self._ws_b_enabled = ws_b_enabled

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
        if self._ws_b_enabled and self._schema_registry is not None:
            try:
                schema = self._schema_registry.get_schema(  # type: ignore[attr-defined]
                    "news", "general"
                )
                validated = self._schema_registry.validate(  # type: ignore[attr-defined]
                    payload, schema
                )
                if isinstance(validated, dict):
                    for key in ("results", "items", "organic", "papers", "data"):
                        value = validated.get(key)
                        if isinstance(value, list):
                            return value
                    return []
            except Exception:
                pass
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
            brave_results = self._extract_results(brave_resp.payload)
        except Exception as exc:
            logger.warning("Brave search failed for session %s: %s", session_id, exc)
        try:
            exa_provider = self._provider_registry.get("exa")
            exa_resp = await self._execution_client.execute_tool(
                exa_provider, "web_search_advanced_exa", {"query": tech}
            )
            exa_results = self._extract_results(exa_resp.payload)
        except Exception as exc:
            logger.warning("Exa search failed for session %s: %s", session_id, exc)
        return brave_results, exa_results

    def _extract_results(self, payload: dict[str, object]) -> list | None:
        for key in ("results", "items", "organic", "papers", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
        return []
