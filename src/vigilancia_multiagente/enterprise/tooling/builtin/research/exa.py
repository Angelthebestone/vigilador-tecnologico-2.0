"""Exa search tool — WRAP-SDK over the official exa-py package.

Spec 021 FR-053/054: native-first, universal Tool abstraction.
Catalog: ``exa`` / domain ``research`` / capabilities
``[semantic_search, find_similar, extract]``.

Strategy: WRAP-SDK using the official ``exa_py`` package.
Constitución #2 KISS — minimal client wrapper.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from exa_py import Exa

from vigilancia_multiagente.enterprise.tooling.tool_wrapper import HealthcheckResult


@dataclass(frozen=True)
class ExaTool:
    """Native tool for the Exa search API."""

    name: str = "exa"
    domain: str = "research"
    is_external_mcp: bool = False
    requires_auth: bool = True

    def _api_key(self) -> str | None:
        return os.getenv("VT_EXA_API_KEY") or None

    def _client(self) -> Exa:
        return Exa(api_key=self._api_key())

    async def healthcheck(self) -> HealthcheckResult:
        if not self._api_key():
            return HealthcheckResult(
                status="UNCONFIGURED",
                error="VT_EXA_API_KEY not set",
            )
        return HealthcheckResult(status="UP")

    async def execute(self, tool_name: str, args: dict[str, object]) -> dict[str, object]:
        """Dispatch to the requested capability.

        Supported ``tool_name`` values:
        * ``semantic_search`` — args: ``query`` (str, required),
          ``num_results`` (int, default 10).
        * ``find_similar`` — args: ``url`` (str, required),
          ``num_results`` (int, default 10).
        * ``extract`` — args: ``urls`` (list[str], required).

        Raises:
            ValueError: unsupported tool_name or invalid args.
            RuntimeError: missing API key.
        """
        api_key = self._api_key()
        if not api_key:
            raise RuntimeError(
                "ExaTool: VT_EXA_API_KEY not configured (tool-gating should have hidden this tool)"
            )

        client = self._client()

        if tool_name == "semantic_search":
            return self._search(client, args)
        if tool_name == "find_similar":
            return self._find_similar(client, args)
        if tool_name == "extract":
            return self._extract(client, args)
        raise ValueError(
            f"ExaTool: unknown tool_name '{tool_name}' "
            f"(supported: semantic_search, find_similar, extract)"
        )

    def _search(self, client: Exa, args: dict[str, object]) -> dict[str, object]:
        query = args.get("query")
        if not isinstance(query, str) or not query.strip():
            raise ValueError("ExaTool: 'query' must be a non-empty string")
        num_results = args.get("num_results", 10)
        if not isinstance(num_results, int) or num_results <= 0:
            num_results = 10

        response = client.search(query, num_results=num_results)
        results = [
            {"url": r.url, "title": r.title, "text": getattr(r, "text", "")}
            for r in response.results
        ]
        return {"query": query, "results": results}

    def _find_similar(self, client: Exa, args: dict[str, object]) -> dict[str, object]:
        url = args.get("url")
        if not isinstance(url, str) or not url.strip():
            raise ValueError("ExaTool: 'url' must be a non-empty string")
        num_results = args.get("num_results", 10)
        if not isinstance(num_results, int) or num_results <= 0:
            num_results = 10

        response = client.find_similar(url, num_results=num_results)
        results = [
            {"url": r.url, "title": r.title, "text": getattr(r, "text", "")}
            for r in response.results
        ]
        return {"url": url, "results": results}

    def _extract(self, client: Exa, args: dict[str, object]) -> dict[str, object]:
        urls = args.get("urls")
        if not isinstance(urls, list) or not urls:
            raise ValueError("ExaTool: 'urls' must be a non-empty list")
        response = client.get_contents(urls)
        results = [{"url": r.url, "text": r.text} for r in response.results if r.text]
        return {"urls": urls, "results": results}
