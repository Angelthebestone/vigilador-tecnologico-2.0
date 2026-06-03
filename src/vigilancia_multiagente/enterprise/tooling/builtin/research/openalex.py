"""OpenAlex tool — native WRAP-SDK over the OpenAlex REST API.

Spec 021 FR-053/054: native-first, universal Tool abstraction.
Catalog: ``openalex`` / domain ``research`` / capabilities
``[search_works, get_authors, get_institutions]``.

Strategy: WRAP-SDK using ``httpx``. OpenAlex doesn't require an API key,
but supplying ``mailto`` in the User-Agent moves the request to the
"polite pool" with much higher rate limits. We honor ``VT_OPENALEX_EMAIL``.

Reference: https://docs.openalex.org/
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import httpx

from vigilancia_multiagente.enterprise.tooling.tool_wrapper import HealthcheckResult

_OPENALEX_BASE_URL = "https://api.openalex.org"
_DEFAULT_TIMEOUT_S = 30.0


@dataclass(frozen=True)
class OpenAlexTool:
    """Native tool for OpenAlex's free scholarly metadata API."""

    name: str = "openalex"
    domain: str = "research"
    is_external_mcp: bool = False
    requires_auth: bool = False

    def _user_agent(self) -> str:
        mailto = os.getenv("VT_OPENALEX_EMAIL") or ""
        ua = "vigilador-tecnologico/3.0 (https://github.com/example/vigilador)"
        if mailto:
            return f"{ua} mailto:{mailto}"
        return ua

    async def healthcheck(self) -> HealthcheckResult:
        """Always reports UP — OpenAlex is anonymous-public."""
        return HealthcheckResult(status="UP")

    async def execute(
        self, tool_name: str, args: dict[str, object]
    ) -> dict[str, object]:
        """Dispatch to the requested capability.

        Supported ``tool_name`` values:
        * ``search_works`` — args: ``query`` (str, required),
          ``per_page`` (int, default 25).
        * ``get_authors`` — args: ``query`` (str, required),
          ``per_page`` (int, default 25).
        * ``get_institutions`` — args: ``query`` (str, required),
          ``per_page`` (int, default 25).
        """
        endpoint_map: dict[str, str] = {
            "search_works": "/works",
            "get_authors": "/authors",
            "get_institutions": "/institutions",
        }
        path = endpoint_map.get(tool_name)
        if path is None:
            raise ValueError(
                f"OpenAlexTool: unknown tool_name '{tool_name}' "
                f"(supported: {', '.join(endpoint_map)})"
            )

        query = args.get("query")
        if not isinstance(query, str) or not query.strip():
            raise ValueError("OpenAlexTool: 'query' must be a non-empty string")
        per_page = args.get("per_page", 25)
        if not isinstance(per_page, int) or per_page <= 0:
            per_page = 25

        params: dict[str, str | int] = {
            "search": query,
            "per_page": per_page,
        }
        api_key = os.getenv("VT_OPENALEX_API_KEY") or ""
        if api_key:
            params["api_key"] = api_key

        headers = {"User-Agent": self._user_agent(), "Accept": "application/json"}
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT_S) as client:
            response = await client.get(
                f"{_OPENALEX_BASE_URL}{path}", params=params, headers=headers
            )
            response.raise_for_status()
            payload = response.json()

        return {
            "query": query,
            "tool": tool_name,
            "results": payload.get("results", []),
            "meta": payload.get("meta", {}),
        }
