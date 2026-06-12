"""Serper Patents tool — BaseHTTPProvider subclass.

Spec 021 FR-053/054: native-first, universal Tool abstraction.
Catalog: ``serper_patents`` / domain ``research`` / capabilities
``[patent_search, patent_details]``.

Focused alias over Serper's patent endpoint. Shares the same REST
backend and API key as ``SerperTool``.
"""

from __future__ import annotations

from typing import Any, ClassVar

from vigilancia_multiagente.enterprise.tooling.builtin._base.http_provider import (
    BaseHTTPProvider,
)


class SerperPatentsTool(BaseHTTPProvider):
    """Native tool exposing Serper's patent endpoint as a focused alias."""

    name: ClassVar[str] = "serper_patents"
    domain: ClassVar[str] = "research"
    base_url: ClassVar[str] = "https://google.serper.dev"
    auth_env_var: ClassVar[str | None] = "VT_SERPER_API_KEY"
    requires_auth: ClassVar[bool] = True

    def _auth_headers(self, api_key: str) -> dict[str, str]:
        return {"X-API-KEY": api_key, "Content-Type": "application/json"}

    async def execute(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        if tool_name == "patent_search":
            query = args.get("query")
            if not isinstance(query, str) or not query.strip():
                raise ValueError("SerperPatentsTool: 'query' must be a non-empty string")
            num = args.get("num", 10)
            if not isinstance(num, int) or num <= 0:
                num = 10
            payload = await self.post("/patents", json={"q": query, "num": num})
            return {"query": query, "results": payload}

        if tool_name == "patent_details":
            patent_id = args.get("patent_id")
            if not isinstance(patent_id, str) or not patent_id.strip():
                raise ValueError("SerperPatentsTool: 'patent_id' must be a non-empty string")
            payload = await self.post(
                "/patents", json={"q": f"patent_id:{patent_id}", "num": 1}
            )
            return {"query": patent_id, "results": payload}

        raise ValueError(
            f"SerperPatentsTool: unknown tool_name '{tool_name}' "
            f"(supported: patent_search, patent_details)"
        )
