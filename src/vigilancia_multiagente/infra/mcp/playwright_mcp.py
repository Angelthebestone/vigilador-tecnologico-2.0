"""Playwright MCP provider wrapper. Browser automation for web interaction."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_BLOCKED_PATTERNS = (
    "access denied",
    "accessdenied",
    "forbidden",
    "blocked",
    "captcha",
    "please verify",
    "too many requests",
    "rate limit",
    "service unavailable",
    "503",
    "403",
)


class PlaywrightProvider:
    """
    Wrapper for the Playwright MCP server.
    Provides browser automation capabilities through MCP tools.
    """

    def __init__(
        self, execution_client: Any = None, provider_registry: Any = None, headless: bool = True
    ) -> None:
        self.execution_client = execution_client
        self.provider_registry = provider_registry
        self.headless = headless
        self._provider: Any = None

    def _get_provider(self):
        if self._provider is None and self.provider_registry is not None:
            self._provider = self.provider_registry.get("playwright")
        return self._provider

    async def navigate(self, url: str) -> dict[str, Any]:
        """Navigate to a URL and return the page snapshot."""
        provider = self._get_provider()
        if provider is None or self.execution_client is None:
            return {"success": False, "error": "Playwright provider not configured"}

        try:
            result = await self.execution_client.execute_tool(
                provider,
                "browser_navigate",
                {"url": url},
            )
            response = {
                "success": True,
                "data": result.payload,
                "provider": result.provider,
            }
            return await self._handle_blocked_response(response, url)
        except Exception as exc:
            logger.warning("Playwright navigate failed for %s: %s", url, exc)
            return {"success": False, "error": str(exc), "blocked": False}

    async def snapshot(self, target: str | None = None) -> dict[str, Any]:
        """Capture accessibility snapshot of current page."""
        provider = self._get_provider()
        if provider is None or self.execution_client is None:
            return {"success": False, "error": "Playwright provider not configured"}

        try:
            args = {"target": target} if target else {}
            result = await self.execution_client.execute_tool(
                provider,
                "browser_snapshot",
                args,
            )
            return {
                "success": True,
                "data": result.payload,
                "provider": result.provider,
            }
        except Exception as exc:
            logger.warning("Playwright snapshot failed: %s", exc)
            return {"success": False, "error": str(exc)}

    async def screenshot(self, full_page: bool = False) -> dict[str, Any]:
        """Take a screenshot of the current page. Returns base64-encoded image."""
        provider = self._get_provider()
        if provider is None or self.execution_client is None:
            return {"success": False, "error": "Playwright provider not configured"}

        try:
            result = await self.execution_client.execute_tool(
                provider,
                "browser_screenshot",
                {"full_page": full_page},
            )
            return {
                "success": True,
                "data": result.payload,
                "provider": result.provider,
            }
        except Exception as exc:
            logger.warning("Playwright screenshot failed: %s", exc)
            return {"success": False, "error": str(exc)}

    async def click(self, target: str, element: str | None = None) -> dict[str, Any]:
        """Click on an element identified by target selector."""
        provider = self._get_provider()
        if provider is None or self.execution_client is None:
            return {"success": False, "error": "Playwright provider not configured"}

        try:
            args: dict[str, Any] = {"target": target}
            if element:
                args["element"] = element
            result = await self.execution_client.execute_tool(
                provider,
                "browser_click",
                args,
            )
            return {
                "success": True,
                "data": result.payload,
                "provider": result.provider,
            }
        except Exception as exc:
            logger.warning("Playwright click failed: %s", exc)
            return {"success": False, "error": str(exc)}

    async def type_text(self, target: str, text: str, submit: bool = False) -> dict[str, Any]:
        """Type text into an editable element."""
        provider = self._get_provider()
        if provider is None or self.execution_client is None:
            return {"success": False, "error": "Playwright provider not configured"}

        try:
            result = await self.execution_client.execute_tool(
                provider,
                "browser_type",
                {"target": target, "text": text, "submit": submit},
            )
            return {
                "success": True,
                "data": result.payload,
                "provider": result.provider,
            }
        except Exception as exc:
            logger.warning("Playwright type_text failed: %s", exc)
            return {"success": False, "error": str(exc)}

    async def get_network_requests(self, static: bool = False) -> list[dict[str, Any]]:
        """Get list of network requests made during page load."""
        provider = self._get_provider()
        if provider is None or self.execution_client is None:
            return [{"success": False, "error": "Playwright provider not configured"}]

        try:
            result = await self.execution_client.execute_tool(
                provider,
                "browser_network_requests",
                {"static": static},
            )
            payload = result.payload
            if isinstance(payload, dict):
                data = payload.get("requests") or payload.get("data") or []
            else:
                data = []
            return list(data) if isinstance(data, list) else []
        except Exception as exc:
            logger.warning("Playwright get_network_requests failed: %s", exc)
            return [{"error": str(exc)}]

    async def get_network_request_detail(self, index: int) -> dict[str, Any]:
        """Get full details of a specific network request."""
        provider = self._get_provider()
        if provider is None or self.execution_client is None:
            return {"success": False, "error": "Playwright provider not configured"}

        try:
            result = await self.execution_client.execute_tool(
                provider,
                "browser_network_request",
                {"index": index},
            )
            return {
                "success": True,
                "data": result.payload,
                "provider": result.provider,
            }
        except Exception as exc:
            logger.warning("Playwright get_network_request_detail failed: %s", exc)
            return {"success": False, "error": str(exc)}

    async def _handle_blocked_response(
        self, response: dict[str, Any], source_url: str
    ) -> dict[str, Any]:
        """
        Detect if a response indicates blocked access and emit negative source signal.

        Checks for:
        - HTTP 403/429/503 status codes
        - CAPTCHA detection in page content
        - "access denied" / "blocked" in snapshot text

        Returns modified response with 'blocked' flag.
        """
        if not response.get("success"):
            return response

        data = response.get("data", {})
        if not isinstance(data, dict):
            return response

        status = data.get("statusCode") or data.get("status") or 0
        if status in (403, 429, 503):
            logger.warning("Blocked access to %s — HTTP %s", source_url, status)
            response["blocked"] = True
            response["block_reason"] = f"HTTP {status}"
            return response

        snapshot = data.get("snapshot") or data.get("content") or data.get("text") or ""
        if isinstance(snapshot, str) and snapshot:
            lowered = snapshot.lower()
            for pattern in _BLOCKED_PATTERNS:
                if pattern in lowered:
                    logger.warning("Blocked access to %s — detected '%s'", source_url, pattern)
                    response["blocked"] = True
                    response["block_reason"] = f"Blocked content: {pattern}"
                    return response

        response["blocked"] = False
        return response
