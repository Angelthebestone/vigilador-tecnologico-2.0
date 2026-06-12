"""Fetch tool — BaseHTTPProvider subclass.

Spec 021 FR-053/054: native-first, universal Tool abstraction.
Catalog: ``fetch`` / domain ``web`` / capabilities ``[fetch_url, extract_text]``.

Strategy: Subclass ``BaseHTTPProvider``. No API key required. Overrides
``client`` to enable ``follow_redirects``. Honors the URL safety floor
from ``enterprise.governance.url_safety`` (FR-025).
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Any, ClassVar

import httpx

from vigilancia_multiagente.enterprise.governance.url_safety import is_safe_url
from vigilancia_multiagente.enterprise.tooling.builtin._base.http_provider import (
    BaseHTTPProvider,
)

_DEFAULT_MAX_BYTES = 1_000_000


class FetchTool(BaseHTTPProvider):
    """Native tool for plain HTTP GET + minimal text extraction."""

    name: ClassVar[str] = "fetch"
    domain: ClassVar[str] = "web"
    base_url: ClassVar[str] = ""
    auth_env_var: ClassVar[str | None] = None
    requires_auth: ClassVar[bool] = False

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
                timeout=httpx.Timeout(30.0, connect=5.0),
                follow_redirects=True,
            )
        return self._client

    def _auth_headers(self, api_key: str) -> dict[str, str]:
        return {}

    async def execute(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        url = args.get("url")
        if not isinstance(url, str) or not url.strip():
            raise ValueError("FetchTool: 'url' must be a non-empty string")
        if not is_safe_url(url):
            raise PermissionError(
                f"FetchTool: URL safety check rejected '{url}' (private/internal "
                "address or cloud-metadata endpoint)"
            )

        if tool_name == "fetch_url":
            return await self._fetch(url)
        if tool_name == "extract_text":
            payload = await self._fetch(url)
            payload["text"] = _html_to_text(str(payload.get("body", "")))
            return payload
        raise ValueError(
            f"FetchTool: unknown tool_name '{tool_name}' (supported: fetch_url, extract_text)"
        )

    async def _fetch(self, url: str) -> dict[str, Any]:
        api_key = await self._api_key()
        resolved_key = api_key or ""
        headers = self._auth_headers(resolved_key)
        try:
            response = await self.client.get(url, headers=headers)
            response.raise_for_status()
            content = response.content[:_DEFAULT_MAX_BYTES]
            try:
                body = content.decode(response.encoding or "utf-8", errors="replace")
            except (LookupError, TypeError):
                body = content.decode("utf-8", errors="replace")
            return {
                "url": str(response.url),
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": body,
                "truncated": len(response.content) > _DEFAULT_MAX_BYTES,
            }
        except httpx.HTTPStatusError as exc:
            self._handle_response_error(exc.response)
            raise
        except httpx.ReadTimeout as exc:
            from vigilancia_multiagente.enterprise.tooling.builtin._base.retry_policy import (
                ProviderTimeoutError,
            )
            raise ProviderTimeoutError("Request timed out") from exc
        except httpx.RequestError as exc:
            from vigilancia_multiagente.enterprise.tooling.builtin._base.retry_policy import (
                ProviderError,
            )
            raise ProviderError(f"Request failed: {exc}") from exc


class _TextExtractor(HTMLParser):
    """Strip tags, drop ``<script>`` / ``<style>`` content, collapse whitespace."""

    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []
        self._skip_depth = 0
        self._skip_tags = {"script", "style"}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self._skip_tags:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in self._skip_tags and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            self._chunks.append(data)

    def text(self) -> str:
        joined = "".join(self._chunks)
        return re.sub(r"\s+", " ", joined).strip()


def _html_to_text(body: str) -> str:
    if not body or "<" not in body:
        return body.strip()
    parser = _TextExtractor()
    parser.feed(body)
    return parser.text()
