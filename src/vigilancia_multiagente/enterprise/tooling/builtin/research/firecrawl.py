"""Firecrawl tool — WRAP-SDK over the official firecrawl-py package.

Spec 021 FR-053/054: native-first, universal Tool abstraction.
Catalog: ``firecrawl`` / domain ``research`` / capabilities
``[crawl_url, scrape_page, map_site]``.

Strategy: WRAP-SDK using the official ``firecrawl_py`` package.
Constitución #2 KISS — minimal client wrapper.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from firecrawl import FirecrawlApp

from vigilancia_multiagente.enterprise.governance.url_safety import is_safe_url
from vigilancia_multiagente.enterprise.tooling.tool_wrapper import HealthcheckResult


@dataclass(frozen=True)
class FirecrawlTool:
    """Native tool for Firecrawl crawl/scrape/map."""

    name: str = "firecrawl"
    domain: str = "research"
    is_external_mcp: bool = False
    requires_auth: bool = True

    def _api_key(self) -> str | None:
        return os.getenv("VT_FIRECRAWL_API_KEY") or None

    def _client(self) -> FirecrawlApp:
        return FirecrawlApp(api_key=self._api_key())

    async def healthcheck(self) -> HealthcheckResult:
        if not self._api_key():
            return HealthcheckResult(
                status="UNCONFIGURED",
                error="VT_FIRECRAWL_API_KEY not set",
            )
        return HealthcheckResult(status="UP")

    async def execute(self, tool_name: str, args: dict[str, object]) -> dict[str, object]:
        """Dispatch to the requested capability.

        Supported ``tool_name`` values:
        * ``scrape_page`` — args: ``url`` (str). Single-page scrape; returns
          ``{url, markdown, html, metadata}``.
        * ``crawl_url`` — args: ``url`` (str), ``limit`` (int, default 10).
          Returns crawl-job submission payload (caller polls).
        * ``map_site`` — args: ``url`` (str). Returns the site URL list.

        Raises:
            ValueError: unsupported tool_name or invalid args.
            RuntimeError: missing API key.
            PermissionError: URL safety check failed.
        """
        api_key = self._api_key()
        if not api_key:
            raise RuntimeError("FirecrawlTool: VT_FIRECRAWL_API_KEY not configured")
        url = args.get("url")
        if not isinstance(url, str) or not url.strip():
            raise ValueError("FirecrawlTool: 'url' must be a non-empty string")
        if not is_safe_url(url):
            raise PermissionError(f"FirecrawlTool: URL safety check rejected '{url}'")

        client = self._client()

        if tool_name == "scrape_page":
            return self._scrape(client, url)
        if tool_name == "crawl_url":
            limit = args.get("limit", 10)
            if not isinstance(limit, int) or limit <= 0:
                limit = 10
            return self._crawl(client, url, limit)
        if tool_name == "map_site":
            return self._map(client, url)
        raise ValueError(
            f"FirecrawlTool: unknown tool_name '{tool_name}' "
            f"(supported: scrape_page, crawl_url, map_site)"
        )

    def _scrape(self, client: FirecrawlApp, url: str) -> dict[str, object]:
        result = client.scrape_url(url, formats=["markdown", "html"])
        getter = result.get if isinstance(result, dict) else lambda k, d=None: getattr(result, k, d)
        return {
            "url": url,
            "markdown": getter("markdown", ""),
            "html": getter("html", ""),
            "metadata": getter("metadata", {}),
        }

    def _crawl(self, client: FirecrawlApp, url: str, limit: int) -> dict[str, object]:
        result = client.crawl_url(
            url, params={"limit": limit, "scrapeOptions": {"formats": ["markdown"]}}
        )
        getter = result.get if isinstance(result, dict) else lambda k, d=None: getattr(result, k, d)
        return {"url": url, "id": getter("id", ""), "status": getter("status", "")}

    def _map(self, client: FirecrawlApp, url: str) -> dict[str, object]:
        result = client.map_url(url)
        getter = result.get if isinstance(result, dict) else lambda k, d=None: getattr(result, k, d)
        return {"url": url, "links": getter("links", [])}
