"""Playwright MCP provider wrapper. Browser automation for web interaction."""

from __future__ import annotations

import logging
from typing import Any

from vigilancia_multiagente.shared.mcp_dto import NavigationResult, ScreenshotResult

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


def _navigation_from_response(url: str, response: dict[str, Any]) -> NavigationResult:
    if not response.get("success"):
        return NavigationResult(
            url=url,
            blocked=bool(response.get("blocked")),
            block_reason=str(response.get("block_reason") or response.get("error") or ""),
        )
    data = response.get("data") or {}
    if not isinstance(data, dict):
        data = {}
    content = str(data.get("snapshot") or data.get("content") or data.get("text") or "")
    return NavigationResult(
        url=url,
        title=str(data.get("title", "")),
        content=content,
        screenshot_path=data.get("screenshot_path"),
        blocked=bool(response.get("blocked")),
        block_reason=response.get("block_reason"),
    )


def _screenshot_from_response(url: str, response: dict[str, Any]) -> ScreenshotResult:
    if not response.get("success"):
        return ScreenshotResult(
            url=url,
            blocked=bool(response.get("blocked")),
            block_reason=str(response.get("error") or ""),
        )
    data = response.get("data") or {}
    image_path = None
    if isinstance(data, dict):
        image_path = data.get("path") or data.get("image_path")
    return ScreenshotResult(
        url=url,
        image_path=str(image_path) if image_path else None,
        blocked=bool(response.get("blocked")),
        block_reason=response.get("block_reason"),
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

    async def navigate(self, url: str) -> NavigationResult:
        """Navigate to a URL and return the page snapshot."""
        provider = self._get_provider()
        if provider is None or self.execution_client is None:
            return NavigationResult(
                url=url,
                blocked=False,
                block_reason="Playwright provider not configured",
            )

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
            handled = await self._handle_blocked_response(response, url)
            return _navigation_from_response(url, handled)
        except Exception as exc:
            logger.warning("Playwright navigate failed for %s: %s", url, exc)
            return NavigationResult(url=url, block_reason=str(exc))

    async def snapshot(self, target: str | None = None) -> NavigationResult:
        """Capture accessibility snapshot of current page."""
        provider = self._get_provider()
        if provider is None or self.execution_client is None:
            return NavigationResult(
                url=target or "",
                block_reason="Playwright provider not configured",
            )

        try:
            args = {"target": target} if target else {}
            result = await self.execution_client.execute_tool(
                provider,
                "browser_snapshot",
                args,
            )
            response = {
                "success": True,
                "data": result.payload,
                "provider": result.provider,
            }
            return _navigation_from_response(target or "", response)
        except Exception as exc:
            logger.warning("Playwright snapshot failed: %s", exc)
            return NavigationResult(url=target or "", block_reason=str(exc))

    async def screenshot(self, full_page: bool = False) -> ScreenshotResult:
        """Take a screenshot of the current page."""
        provider = self._get_provider()
        if provider is None or self.execution_client is None:
            return ScreenshotResult(
                url="",
                block_reason="Playwright provider not configured",
            )

        try:
            result = await self.execution_client.execute_tool(
                provider,
                "browser_screenshot",
                {"full_page": full_page},
            )
            response = {
                "success": True,
                "data": result.payload,
                "provider": result.provider,
            }
            return _screenshot_from_response("", response)
        except Exception as exc:
            logger.warning("Playwright screenshot failed: %s", exc)
            return ScreenshotResult(url="", block_reason=str(exc))

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
