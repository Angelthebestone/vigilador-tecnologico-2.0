"""Serper tool — BaseHTTPProvider subclass.

Spec 021 FR-053/054: native-first, universal Tool abstraction.
Catalog: ``serper`` / domain ``research`` / capabilities
``[google_search, scholar_search, patent_search, news_search]``.

Strategy: Subclass ``BaseHTTPProvider``. Override ``_auth_headers()``
with ``X-API-KEY`` header (Serper's custom auth pattern).
"""

from __future__ import annotations

from typing import Any, ClassVar

from vigilancia_multiagente.enterprise.tooling.builtin._base.http_provider import (
    BaseHTTPProvider,
)

_TOOL_TO_PATH: dict[str, str] = {
    "google_search": "/search",
    "news_search": "/news",
    "scholar_search": "/scholar",
    "patent_search": "/patents",
}


class SerperTool(BaseHTTPProvider):
    """Native tool for Serper's google.serper.dev API."""

    name: ClassVar[str] = "serper"
    domain: ClassVar[str] = "research"
    base_url: ClassVar[str] = "https://google.serper.dev"
    auth_env_var: ClassVar[str | None] = "VT_SERPER_API_KEY"
    requires_auth: ClassVar[bool] = True

    def _auth_headers(self, api_key: str) -> dict[str, str]:
        return {"X-API-KEY": api_key, "Content-Type": "application/json"}

    async def execute(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        path = _TOOL_TO_PATH.get(tool_name)
        if path is None:
            raise ValueError(
                f"SerperTool: unknown tool_name '{tool_name}' "
                f"(supported: {', '.join(_TOOL_TO_PATH)})"
            )
        query = args.get("query") or args.get("q")
        if not isinstance(query, str) or not query.strip():
            raise ValueError("SerperTool: 'query' must be a non-empty string")
        num = args.get("num", 10)
        if not isinstance(num, int) or num <= 0:
            num = 10

        payload = await self.post(path, json={"q": query, "num": num})
        return {"query": query, "tool": tool_name, "results": payload}
