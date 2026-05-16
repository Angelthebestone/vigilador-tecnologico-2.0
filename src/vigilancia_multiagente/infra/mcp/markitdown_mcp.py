"""Markitdown MCP provider wrapper. Converts documents (PDF, DOCX, PPTX, etc.) to Markdown."""

from __future__ import annotations

from typing import Any
import logging

logger = logging.getLogger(__name__)


class MarkitdownProvider:
    """
    Wrapper for the Markitdown MCP server.
    Uses the execution client to call convert_to_markdown tool.
    """

    SUPPORTED_FORMATS = frozenset({
        "pdf", "docx", "pptx", "xlsx", "html", "csv", "json", "xml", "png", "jpg",
    })

    def __init__(self, execution_client: Any = None, provider_registry: Any = None) -> None:
        self.execution_client = execution_client
        self.provider_registry = provider_registry
        self._provider: Any = None

    def _get_provider(self):
        if self._provider is None and self.provider_registry is not None:
            self._provider = self.provider_registry.get("markitdown")
        return self._provider

    async def convert_to_markdown(self, uri: str) -> dict[str, Any]:
        """
        Convert a document at the given URI to Markdown.

        Args:
            uri: Document URI (http:, https:, file:, data:)

        Returns:
            dict with 'content' (markdown string), 'format' (source format), 'success' (bool)
        """
        provider = self._get_provider()
        if provider is None or self.execution_client is None:
            return {"success": False, "error": "Markitdown provider not configured", "content": None}

        try:
            result = await self.execution_client.execute_tool(
                provider,
                "convert_to_markdown",
                {"uri": uri},
            )
            payload = result.payload
            if not isinstance(payload, dict):
                return {"success": False, "error": "Unexpected response format", "content": None}

            content = payload.get("content") or payload.get("markdown") or ""
            fmt = payload.get("format") or payload.get("source_format") or _detect_format(uri)
            return {
                "content": str(content),
                "format": str(fmt),
                "success": True,
                "provider": result.provider,
            }
        except Exception as exc:
            logger.warning("Markitdown conversion failed for %s: %s", uri, exc)
            return {"success": False, "error": str(exc), "content": None, "format": None}

    async def get_supported_formats(self) -> list[str]:
        """Return list of supported document formats."""
        return sorted(self.SUPPORTED_FORMATS)


def _detect_format(uri: str) -> str:
    ext = uri.rsplit(".", 1)[-1].lower() if "." in uri else "unknown"
    return ext if ext in MarkitdownProvider.SUPPORTED_FORMATS else "unknown"
