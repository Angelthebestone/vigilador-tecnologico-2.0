"""Firecrawl tool — native WRAP-SDK over the Firecrawl REST API.

Spec 021 FR-053/054: native-first, universal Tool abstraction.
Catalog: ``firecrawl`` / domain ``research`` / capabilities
``[crawl_url, scrape_page, map_site]``.

Strategy: WRAP-SDK using ``httpx``. The ``firecrawl-py`` SDK is a thin
wrapper around the same endpoints; we use ``httpx`` directly to avoid
adding another optional dependency.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import httpx

from vigilancia_multiagente.enterprise.governance.url_safety import is_safe_url
from vigilancia_multiagente.enterprise.tooling.tool_wrapper import HealthcheckResult

_FIRECRAWL_BASE_URL = "https://api.firecrawl.dev/v1"
_DEFAULT_TIMEOUT_S = 120.0  # crawl jobs can be slow


@dataclass(frozen=True)
class FirecrawlTool:
    """Native tool for Firecrawl crawl/scrape/map."""

    name: str = "firecrawl"
    domain: str = "research"
    is_external_mcp: bool = False
    requires_auth: bool = True

    def _api_key(self) -> str | None:
        return os.getenv("VT_FIRECRAWL_API_KEY") or None

    async def healthcheck(self) -> HealthcheckResult:
        if not self._api_key():
            return HealthcheckResult(
                status="UNCONFIGURED",
                error="VT_FIRECRAWL_API_KEY not set",
            )
        return HealthcheckResult(status="UP")

    async def execute(
        self, tool_name: str, args: dict[str, object]
    ) -> dict[str, object]:
        """Dispatch to the requested capability.

        Supported ``tool_name`` values:
        * ``scrape_page`` — args: ``url`` (str). Single-page scrape; returns
          ``{url, markdown, html, metadata}``.
        * ``crawl_url`` — args: ``url`` (str), ``limit`` (int, default 10).
          Returns crawl-job submission payload (caller polls).
        * ``map_site`` — args: ``url`` (str). Returns the site URL list.
        """
        api_key = self._api_key()
        if not api_key:
            raise RuntimeError(
                "FirecrawlTool: VT_FIRECRAWL_API_KEY not configured"
            )
        url = args.get("url")
        if not isinstance(url, str) or not url.strip():
            raise ValueError("FirecrawlTool: 'url' must be a non-empty string")
        if not is_safe_url(url):
            raise PermissionError(
                f"FirecrawlTool: URL safety check rejected '{url}'"
            )

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        if tool_name == "scrape_page":
            return await self._post(headers, "/scrape", {"url": url}, key="data")
        if tool_name == "crawl_url":
            limit = args.get("limit", 10)
            if not isinstance(limit, int) or limit <= 0:
                limit = 10
            return await self._post(
                headers, "/crawl", {"url": url, "limit": limit}, key=None
            )
        if tool_name == "map_site":
            return await self._post(headers, "/map", {"url": url}, key="links")
        raise ValueError(
            f"FirecrawlTool: unknown tool_name '{tool_name}' "
            f"(supported: scrape_page, crawl_url, map_site)"
        )

    async def _post(
        self,
        headers: dict[str, str],
        path: str,
        body: dict[str, object],
        *,
        key: str | None,
    ) -> dict[str, object]:
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT_S) as client:
            response = await client.post(
                f"{_FIRECRAWL_BASE_URL}{path}", json=body, headers=headers
            )
            response.raise_for_status()
            payload = response.json()
        if key is None:
            return payload
        return {"url": body.get("url"), key: payload.get(key, payload)}
