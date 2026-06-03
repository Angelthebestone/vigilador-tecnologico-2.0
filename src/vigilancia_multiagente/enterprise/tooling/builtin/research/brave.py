"""Brave Search tool — native WRAP-SDK over Brave's REST API.

Spec 021 FR-053/054: native-first, universal Tool abstraction.
Catalog: ``brave`` / domain ``research`` / capabilities
``[web_search, local_search]``.

Strategy: WRAP-SDK using ``httpx``. Brave's API uses an
``X-Subscription-Token`` header — no SDK package needed.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import httpx

from vigilancia_multiagente.enterprise.tooling.tool_wrapper import HealthcheckResult

_BRAVE_BASE_URL = "https://api.search.brave.com/res/v1"
_DEFAULT_TIMEOUT_S = 30.0


@dataclass(frozen=True)
class BraveTool:
    """Native tool for the Brave Search API."""

    name: str = "brave"
    domain: str = "research"
    is_external_mcp: bool = False
    requires_auth: bool = True

    def _api_key(self) -> str | None:
        return os.getenv("VT_BRAVE_API_KEY") or None

    async def healthcheck(self) -> HealthcheckResult:
        if not self._api_key():
            return HealthcheckResult(
                status="UNCONFIGURED",
                error="VT_BRAVE_API_KEY not set",
            )
        return HealthcheckResult(status="UP")

    async def execute(
        self, tool_name: str, args: dict[str, object]
    ) -> dict[str, object]:
        """Dispatch to the requested capability.

        Supported ``tool_name`` values:
        * ``web_search`` — args: ``query`` (str, required), ``count`` (int, default 10).
        * ``local_search`` — args: ``query`` + ``location`` (optional str),
          ``count`` (default 5). Local results require Pro tier.

        Raises:
            ValueError: unsupported tool_name or invalid args.
            RuntimeError: missing API key.
            httpx.HTTPStatusError: non-2xx HTTP responses.
        """
        api_key = self._api_key()
        if not api_key:
            raise RuntimeError(
                "BraveTool: VT_BRAVE_API_KEY not configured (tool-gating "
                "should have hidden this tool)"
            )

        query = args.get("query")
        if not isinstance(query, str) or not query.strip():
            raise ValueError("BraveTool: 'query' must be a non-empty string")

        if tool_name == "web_search":
            return await self._web_search(api_key, query, args)
        if tool_name == "local_search":
            return await self._local_search(api_key, query, args)
        raise ValueError(
            f"BraveTool: unknown tool_name '{tool_name}' "
            f"(supported: web_search, local_search)"
        )

    async def _web_search(
        self, api_key: str, query: str, args: dict[str, object]
    ) -> dict[str, object]:
        count = args.get("count", 10)
        if not isinstance(count, int) or count <= 0:
            count = 10

        params: dict[str, str | int] = {"q": query, "count": count}
        headers = {
            "X-Subscription-Token": api_key,
            "Accept": "application/json",
        }
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT_S) as client:
            response = await client.get(
                f"{_BRAVE_BASE_URL}/web/search", params=params, headers=headers
            )
            response.raise_for_status()
            payload = response.json()

        web_results = (payload.get("web") or {}).get("results", [])
        return {"query": query, "results": web_results}

    async def _local_search(
        self, api_key: str, query: str, args: dict[str, object]
    ) -> dict[str, object]:
        count = args.get("count", 5)
        if not isinstance(count, int) or count <= 0:
            count = 5
        params: dict[str, str | int] = {"q": query, "count": count}
        location = args.get("location")
        if isinstance(location, str) and location.strip():
            params["search_lang"] = location.strip()

        headers = {
            "X-Subscription-Token": api_key,
            "Accept": "application/json",
        }
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT_S) as client:
            response = await client.get(
                f"{_BRAVE_BASE_URL}/local/search", params=params, headers=headers
            )
            response.raise_for_status()
            payload = response.json()

        return {"query": query, "results": payload.get("results", [])}
