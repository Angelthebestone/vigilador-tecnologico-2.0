"""Jina reader tool — native WRAP-SDK over Jina's free reader/extract endpoints.

Spec 021 FR-053/054: native-first, universal Tool abstraction.
Catalog: ``jina`` / domain ``research`` / capabilities
``[reader, extract_content]``.

Strategy: WRAP-SDK using ``httpx``. ``r.jina.ai/<url>`` is the reader API
that converts any URL to clean Markdown. The API key is optional (anonymous
calls work but are rate-limited); when present it goes in the
``Authorization`` header for higher quotas.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import httpx

from vigilancia_multiagente.enterprise.governance.url_safety import is_safe_url
from vigilancia_multiagente.enterprise.tooling.tool_wrapper import HealthcheckResult

_JINA_READER_BASE_URL = "https://r.jina.ai"
_DEFAULT_TIMEOUT_S = 60.0


@dataclass(frozen=True)
class JinaTool:
    """Native tool for the Jina reader/extract endpoints."""

    name: str = "jina"
    domain: str = "research"
    is_external_mcp: bool = False
    # Reader works without API key (anonymous tier), so requires_auth=False.
    requires_auth: bool = False

    def _api_key(self) -> str | None:
        return os.getenv("VT_JINA_API_KEY") or None

    async def healthcheck(self) -> HealthcheckResult:
        """Reader endpoint is always reachable; reports UP unconditionally."""
        return HealthcheckResult(status="UP")

    async def execute(
        self, tool_name: str, args: dict[str, object]
    ) -> dict[str, object]:
        """Dispatch to the requested capability.

        Supported ``tool_name`` values:
        * ``reader`` — args: ``url`` (str, required). Returns the URL
          converted to clean Markdown (no nav/scripts/ads).
        * ``extract_content`` — alias of reader; same behavior.
        """
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
                f"JinaTool: unknown tool_name '{tool_name}' "
                f"(supported: reader, extract_content)"
            )
        return await self._read(url)

    async def _read(self, url: str) -> dict[str, object]:
        headers = {"Accept": "application/json"}
        api_key = self._api_key()
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT_S) as client:
            response = await client.get(
                f"{_JINA_READER_BASE_URL}/{url}", headers=headers
            )
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type:
                payload = response.json()
                data = payload.get("data") if isinstance(payload, dict) else payload
                return {"url": url, "content": data}
            return {"url": url, "content": response.text}
