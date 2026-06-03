"""Fetch tool — native WRAP-SDK over ``httpx`` for plain HTTP fetch + text extract.

Spec 021 FR-053/054: native-first, universal Tool abstraction.
Catalog: ``fetch`` / domain ``web`` / capabilities ``[fetch_url, extract_text]``.

Strategy: WRAP-SDK using ``httpx``. No API key required. Honors the URL
safety floor from ``enterprise.governance.url_safety`` (FR-025) so the
agent cannot fetch private/internal addresses or cloud metadata endpoints.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser

import httpx

from vigilancia_multiagente.enterprise.governance.url_safety import is_safe_url
from vigilancia_multiagente.enterprise.tooling.tool_wrapper import HealthcheckResult

_DEFAULT_TIMEOUT_S = 30.0
_DEFAULT_MAX_BYTES = 1_000_000  # 1 MB body cap; over-large pages truncate cleanly.


@dataclass(frozen=True)
class FetchTool:
    """Native tool for plain HTTP GET + minimal text extraction."""

    name: str = "fetch"
    domain: str = "web"
    is_external_mcp: bool = False
    requires_auth: bool = False

    async def healthcheck(self) -> HealthcheckResult:
        """Always reports UP — ``httpx`` is a hard dependency of the project."""
        return HealthcheckResult(status="UP")

    async def execute(
        self, tool_name: str, args: dict[str, object]
    ) -> dict[str, object]:
        """Dispatch to the requested capability.

        Supported ``tool_name`` values:
        * ``fetch_url`` — args: ``url`` (str, required). Returns
          ``{url, status_code, headers, body}`` (body capped at 1 MB).
        * ``extract_text`` — args: ``url`` (str). Same fetch + a minimal
          HTML→text pass.

        Raises:
            ValueError: unsupported tool_name or invalid url.
            PermissionError: URL fails the SSRF safety check
                (governance.url_safety.is_safe_url).
            httpx.HTTPStatusError: non-2xx response.
        """
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
            payload["text"] = _html_to_text(payload.get("body", ""))
            return payload
        raise ValueError(
            f"FetchTool: unknown tool_name '{tool_name}' "
            f"(supported: fetch_url, extract_text)"
        )

    async def _fetch(self, url: str) -> dict[str, object]:
        async with httpx.AsyncClient(
            timeout=_DEFAULT_TIMEOUT_S,
            follow_redirects=True,
        ) as client:
            response = await client.get(url)
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


# ---------------------------------------------------------------------------
# Minimal HTML → text extractor (KISS — no BeautifulSoup dependency)
# ---------------------------------------------------------------------------


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
        # Collapse runs of whitespace (including newlines from block elements).
        return re.sub(r"\s+", " ", joined).strip()


def _html_to_text(body: str) -> str:
    """Best-effort HTML→text. Empty/non-HTML body passes through trimmed."""
    if not body or "<" not in body:
        return body.strip()
    parser = _TextExtractor()
    parser.feed(body)
    return parser.text()
