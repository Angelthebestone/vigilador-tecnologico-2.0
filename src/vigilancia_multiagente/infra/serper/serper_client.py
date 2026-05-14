"""Serper REST API client.

Serper does not have an MCP server. Use this client directly for
news, patents, and scholar searches via Serper's REST API.

Usage:
    client = SerperClient(api_key="...")
    news = await client.search_news("apple inc")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx


class SerperError(Exception):
    """Raised when the Serper API returns an error or is unreachable."""


@dataclass(slots=True, frozen=True)
class SerperResult:
    """Structured result from a Serper API call."""

    items: list[dict[str, Any]]
    total: int


@dataclass(slots=True)
class SerperClient:
    """Async Serper API client.

    Thread-safe, connection-pooled via httpx.AsyncClient.
    Configure via ``VT_SERPER_API_KEY`` env var.
    """

    api_key: str
    _client: httpx.AsyncClient | None = field(default=None, repr=False)

    _BASE_URLS = {
        "news": "https://google.serper.dev/news",
        "patents": "https://google.serper.dev/patents",
        "scholar": "https://google.serper.dev/scholar",
    }

    async def _request(self, endpoint: str, queries: list[str]) -> httpx.Response:
        """Execute a POST request to the Serper API."""
        url = self._BASE_URLS[endpoint]

        if self._client is None:
            self._client = httpx.AsyncClient(
                headers={"X-API-KEY": self.api_key, "Content-Type": "application/json"},
                timeout=httpx.Timeout(30.0),
            )

        payload = [{"q": q, "tbs": "qdr:h"} for q in queries]
        try:
            response = await self._client.post(url, json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise SerperError(f"Serper {endpoint} returned {exc.response.status_code}") from exc
        except httpx.RequestError as exc:
            raise SerperError(f"Serper {endpoint} request failed: {exc}") from exc
        return response

    async def search_news(self, *queries: str) -> SerperResult:
        resp = await self._request("news", list(queries))
        items = _extract_items(resp.json(), ("news", "organic", "results"))
        return SerperResult(items=items, total=len(items))

    async def search_patents(self, *queries: str) -> SerperResult:
        resp = await self._request("patents", list(queries))
        items = _extract_items(resp.json(), ("patents", "organic", "results"))
        return SerperResult(items=items, total=len(items))

    async def search_scholar(self, *queries: str) -> SerperResult:
        resp = await self._request("scholar", list(queries))
        items = _extract_items(resp.json(), ("organic", "scholar", "results"))
        return SerperResult(items=items, total=len(items))

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> SerperClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()


def _extract_items(data: Any, keys: tuple[str, ...]) -> list[dict[str, Any]]:
    if isinstance(data, dict):
        for key in keys:
            value = data.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        return []
    if not isinstance(data, list):
        return []

    items: list[dict[str, Any]] = []
    for entry in data:
        if isinstance(entry, dict):
            nested = _extract_items(entry, keys)
            items.extend(nested or [entry])
        elif isinstance(entry, list):
            items.extend(item for item in entry if isinstance(item, dict))
    return items
