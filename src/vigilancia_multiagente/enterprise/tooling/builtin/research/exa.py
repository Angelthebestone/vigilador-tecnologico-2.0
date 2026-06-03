"""Exa search tool — native WRAP-SDK over the Exa REST API.

Spec 021 FR-053/054: native-first, universal Tool abstraction.
Catalog: ``exa`` / domain ``research`` / capabilities
``[semantic_search, find_similar]``.

Strategy: WRAP-SDK using ``httpx`` (no ``exa-py`` dependency). Auth via the
``x-api-key`` header.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import httpx

from vigilancia_multiagente.enterprise.tooling.tool_wrapper import HealthcheckResult

_EXA_BASE_URL = "https://api.exa.ai"
_DEFAULT_TIMEOUT_S = 30.0


@dataclass(frozen=True)
class ExaTool:
    """Native tool for the Exa search API."""

    name: str = "exa"
    domain: str = "research"
    is_external_mcp: bool = False
    requires_auth: bool = True

    def _api_key(self) -> str | None:
        return os.getenv("VT_EXA_API_KEY") or None

    async def healthcheck(self) -> HealthcheckResult:
        if not self._api_key():
            return HealthcheckResult(
                status="UNCONFIGURED",
                error="VT_EXA_API_KEY not set",
            )
        return HealthcheckResult(status="UP")

    async def execute(
        self, tool_name: str, args: dict[str, object]
    ) -> dict[str, object]:
        """Dispatch to the requested capability.

        Supported ``tool_name`` values:
        * ``semantic_search`` — args: ``query`` (str, required),
          ``num_results`` (int, default 10).
        * ``find_similar`` — args: ``url`` (str, required),
          ``num_results`` (int, default 10).
        """
        api_key = self._api_key()
        if not api_key:
            raise RuntimeError(
                "ExaTool: VT_EXA_API_KEY not configured (tool-gating "
                "should have hidden this tool)"
            )

        headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        if tool_name == "semantic_search":
            return await self._search(headers, args)
        if tool_name == "find_similar":
            return await self._find_similar(headers, args)
        raise ValueError(
            f"ExaTool: unknown tool_name '{tool_name}' "
            f"(supported: semantic_search, find_similar)"
        )

    async def _search(
        self, headers: dict[str, str], args: dict[str, object]
    ) -> dict[str, object]:
        query = args.get("query")
        if not isinstance(query, str) or not query.strip():
            raise ValueError("ExaTool: 'query' must be a non-empty string")
        num_results = args.get("num_results", 10)
        if not isinstance(num_results, int) or num_results <= 0:
            num_results = 10

        body = {"query": query, "numResults": num_results}
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT_S) as client:
            response = await client.post(
                f"{_EXA_BASE_URL}/search", json=body, headers=headers
            )
            response.raise_for_status()
            payload = response.json()

        return {"query": query, "results": payload.get("results", [])}

    async def _find_similar(
        self, headers: dict[str, str], args: dict[str, object]
    ) -> dict[str, object]:
        url = args.get("url")
        if not isinstance(url, str) or not url.strip():
            raise ValueError("ExaTool: 'url' must be a non-empty string")
        num_results = args.get("num_results", 10)
        if not isinstance(num_results, int) or num_results <= 0:
            num_results = 10

        body = {"url": url, "numResults": num_results}
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT_S) as client:
            response = await client.post(
                f"{_EXA_BASE_URL}/findSimilar", json=body, headers=headers
            )
            response.raise_for_status()
            payload = response.json()

        return {"url": url, "results": payload.get("results", [])}
