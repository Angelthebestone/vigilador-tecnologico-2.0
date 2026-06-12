"""Brave Search tool — BaseHTTPProvider subclass.

Spec 021 FR-053/054: native-first, universal Tool abstraction.
Catalog: ``brave`` / domain ``research`` / capabilities
``[web_search, local_search]``.

Strategy: Subclass ``BaseHTTPProvider``. Override ``_auth_headers()``
with ``X-Subscription-Token`` header.
"""

from __future__ import annotations

from typing import Any, ClassVar

from vigilancia_multiagente.enterprise.tooling.builtin._base.http_provider import (
    BaseHTTPProvider,
)


class BraveTool(BaseHTTPProvider):
    """Native tool for the Brave Search API via BaseHTTPProvider."""

    name: ClassVar[str] = "brave"
    domain: ClassVar[str] = "research"
    base_url: ClassVar[str] = "https://api.search.brave.com/res/v1"
    auth_env_var: ClassVar[str | None] = "VT_BRAVE_API_KEY"
    requires_auth: ClassVar[bool] = True

    def _auth_headers(self, api_key: str) -> dict[str, str]:
        """Override: Brave uses X-Subscription-Token instead of Bearer."""
        return {"X-Subscription-Token": api_key, "Accept": "application/json"}

    async def execute(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        """Dispatch to the requested capability.

        Supported ``tool_name`` values:
        * ``web_search`` — args: ``query`` (str, required), ``count`` (int, default 10).
        * ``local_search`` — args: ``query`` + ``location`` (optional str),
          ``count`` (default 5). Local results require Pro tier.
        """
        query = args.get("query")
        if not isinstance(query, str) or not query.strip():
            raise ValueError("BraveTool: 'query' must be a non-empty string")

        if tool_name == "web_search":
            return await self._web_search(query, args)
        if tool_name == "local_search":
            return await self._local_search(query, args)
        raise ValueError(
            f"BraveTool: unknown tool_name '{tool_name}' (supported: web_search, local_search)"
        )

    async def _web_search(self, query: str, args: dict[str, Any]) -> dict[str, Any]:
        count = args.get("count", 10)
        if not isinstance(count, int) or count <= 0:
            count = 10

        params: dict[str, str | int] = {"q": query, "count": count}
        payload = await self.get("/web/search", params=params)

        web_results = (payload.get("web") or {}).get("results", [])
        return {"query": query, "results": web_results}

    async def _local_search(self, query: str, args: dict[str, Any]) -> dict[str, Any]:
        count = args.get("count", 5)
        if not isinstance(count, int) or count <= 0:
            count = 5
        params: dict[str, str | int] = {"q": query, "count": count}
        location = args.get("location")
        if isinstance(location, str) and location.strip():
            params["search_lang"] = location.strip()

        payload = await self.get("/local/search", params=params)
        return {"query": query, "results": payload.get("results", [])}
