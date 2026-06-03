"""Serper tool — native WRAP-SDK over Serper's Google-search-as-a-service API.

Spec 021 FR-053/054: native-first, universal Tool abstraction.
Catalog: ``serper`` / domain ``research`` / capabilities
``[google_search, scholar_search, patent_search, news_search]``.

Strategy: WRAP-SDK using ``httpx``. Serper exposes a uniform body schema
across endpoints; we route by ``tool_name`` to the right endpoint.

The same backend powers the ``serper_patents`` alias entry in the catalog.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import httpx

from vigilancia_multiagente.enterprise.tooling.tool_wrapper import HealthcheckResult

_SERPER_BASE_URL = "https://google.serper.dev"
_DEFAULT_TIMEOUT_S = 30.0

_TOOL_TO_PATH: dict[str, str] = {
    "google_search": "/search",
    "news_search": "/news",
    "scholar_search": "/scholar",
    "patent_search": "/patents",
}


@dataclass(frozen=True)
class SerperTool:
    """Native tool for Serper's google.serper.dev API."""

    name: str = "serper"
    domain: str = "research"
    is_external_mcp: bool = False
    requires_auth: bool = True

    def _api_key(self) -> str | None:
        return os.getenv("VT_SERPER_API_KEY") or None

    async def healthcheck(self) -> HealthcheckResult:
        if not self._api_key():
            return HealthcheckResult(
                status="UNCONFIGURED",
                error="VT_SERPER_API_KEY not set",
            )
        return HealthcheckResult(status="UP")

    async def execute(
        self, tool_name: str, args: dict[str, object]
    ) -> dict[str, object]:
        """Dispatch to the requested capability.

        Supported ``tool_name`` values map directly to Serper endpoints:
        * ``google_search`` → ``/search``
        * ``news_search`` → ``/news``
        * ``scholar_search`` → ``/scholar``
        * ``patent_search`` → ``/patents``

        All take ``query`` (str, required) and ``num`` (int, default 10).
        """
        api_key = self._api_key()
        if not api_key:
            raise RuntimeError("SerperTool: VT_SERPER_API_KEY not configured")
        path = _TOOL_TO_PATH.get(tool_name)
        if path is None:
            raise ValueError(
                f"SerperTool: unknown tool_name '{tool_name}' "
                f"(supported: {', '.join(_TOOL_TO_PATH)})"
            )
        return await self._post(api_key, path, args, tool_name)

    async def _post(
        self,
        api_key: str,
        path: str,
        args: dict[str, object],
        tool_name: str,
    ) -> dict[str, object]:
        query = args.get("query") or args.get("q")
        if not isinstance(query, str) or not query.strip():
            raise ValueError("SerperTool: 'query' must be a non-empty string")
        num = args.get("num", 10)
        if not isinstance(num, int) or num <= 0:
            num = 10

        headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
        body: dict[str, object] = {"q": query, "num": num}
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT_S) as client:
            response = await client.post(
                f"{_SERPER_BASE_URL}{path}", json=body, headers=headers
            )
            response.raise_for_status()
            payload = response.json()

        return {"query": query, "tool": tool_name, "results": payload}
