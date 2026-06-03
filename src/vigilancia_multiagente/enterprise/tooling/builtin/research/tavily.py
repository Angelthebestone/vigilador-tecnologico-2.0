"""Tavily search tool — WRAP-SDK over the official tavily-python package.

Spec 021 FR-053/054: native-first, universal Tool abstraction.
Catalog: ``tavily`` / domain ``research`` / capabilities
``[web_search, news_search]``.

Strategy: WRAP-SDK using the official ``tavily-python`` package.
Constitución #2 KISS — minimal client wrapper, no auto-retry magic.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from tavily import TavilyClient

from vigilancia_multiagente.enterprise.tooling.tool_wrapper import HealthcheckResult


@dataclass(frozen=True)
class TavilyTool:
    """Native tool for the Tavily search API."""

    name: str = "tavily"
    domain: str = "research"
    is_external_mcp: bool = False
    requires_auth: bool = True

    def _api_key(self) -> str | None:
        return os.getenv("VT_TAVILY_API_KEY") or None

    def _client(self) -> TavilyClient:
        return TavilyClient(api_key=self._api_key())

    async def healthcheck(self) -> HealthcheckResult:
        """Verify API key is present. Skips a live ping to avoid quota burn."""
        if not self._api_key():
            return HealthcheckResult(
                status="UNCONFIGURED",
                error="VT_TAVILY_API_KEY not set",
            )
        return HealthcheckResult(status="UP")

    async def execute(
        self, tool_name: str, args: dict[str, object]
    ) -> dict[str, object]:
        """Dispatch to the requested capability.

        Supported ``tool_name`` values:
        * ``web_search`` — full web search; args: ``query`` (str, required),
          ``max_results`` (int, default 5).
        * ``news_search`` — news-only search; same args, sets ``topic="news"``.

        Raises:
            ValueError: if ``tool_name`` is not supported.
            RuntimeError: if the API key is missing.
        """
        api_key = self._api_key()
        if not api_key:
            raise RuntimeError(
                "TavilyTool: VT_TAVILY_API_KEY not configured (tool-gating "
                "should have hidden this tool)"
            )

        if tool_name == "web_search":
            return self._search(args, topic=None)
        if tool_name == "news_search":
            return self._search(args, topic="news")
        raise ValueError(
            f"TavilyTool: unknown tool_name '{tool_name}' "
            f"(supported: web_search, news_search)"
        )

    def _search(
        self,
        args: dict[str, object],
        *,
        topic: str | None,
    ) -> dict[str, object]:
        query = args.get("query")
        if not isinstance(query, str) or not query.strip():
            raise ValueError("TavilyTool: 'query' must be a non-empty string")
        max_results = args.get("max_results", 5)
        if not isinstance(max_results, int) or max_results <= 0:
            max_results = 5

        client = self._client()
        response = client.search(
            query=query,
            max_results=max_results,
            topic=topic or "general",
            search_depth="advanced",
            include_answer=True,
        )

        return {
            "query": query,
            "topic": topic or "general",
            "results": response.get("results", []),
            "answer": response.get("answer"),
        }
