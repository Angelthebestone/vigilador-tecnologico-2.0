"""Jina reader tool — BaseHTTPProvider subclass.

Spec 021 FR-053/054: native-first, universal Tool abstraction.
Catalog: ``jina`` / domain ``research`` / capabilities
``[reader, extract_content]``.

Strategy: Subclass ``BaseHTTPProvider``. Override ``_auth_headers()``
with optional Bearer token (anonymous tier works without key).
"""

from __future__ import annotations

from typing import Any, ClassVar

import httpx

from vigilancia_multiagente.enterprise.governance.url_safety import is_safe_url
from vigilancia_multiagente.enterprise.tooling.builtin._base.http_provider import (
    BaseHTTPProvider,
)


class JinaTool(BaseHTTPProvider):
    """Native tool for the Jina reader/extract endpoints."""

    name: ClassVar[str] = "jina"
    domain: ClassVar[str] = "research"
    base_url: ClassVar[str] = "https://r.jina.ai"
    auth_env_var: ClassVar[str | None] = "VT_JINA_API_KEY"
    requires_auth: ClassVar[bool] = False

    def _auth_headers(self, api_key: str) -> dict[str, str]:
        headers: dict[str, str] = {"Accept": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

    async def execute(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        url = args.get("url")
        if not isinstance(url, str) or not url.strip():
            raise ValueError("JinaTool: 'url' must be a non-empty string")
        if not is_safe_url(url):
            raise PermissionError(
                f"JinaTool: URL safety check rejected '{url}' "
                "(private/internal address or cloud-metadata endpoint)"
            )
        if tool_name not in {"reader", "extract_content"}:
            raise ValueError(
                f"JinaTool: unknown tool_name '{tool_name}' (supported: reader, extract_content)"
            )
        return await self._read(url)

    async def _read(self, url: str) -> dict[str, Any]:
        try:
            response = await self.get(f"/{url}")
            content_type = response.get("content-type", "")
            if "application/json" in content_type:
                data = response.get("data") if isinstance(response, dict) else response
                return {"url": url, "content": data}
            return {"url": url, "content": response}
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                return {"url": url, "error": "rate_limited", "content": ""}
            raise
