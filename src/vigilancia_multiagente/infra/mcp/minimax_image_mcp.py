"""MiniMax Image MCP provider wrapper. Understands image content via the MiniMax vision API."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class MinimaxImageProvider:
    """Wrapper for the MiniMax Image MCP server (Token Plan).

    Uses ``understand_image(prompt, image_url)`` to analyze images
    (JPEG, PNG, GIF, WebP — max 20 MB).
    """

    SUPPORTED_FORMATS = frozenset({"jpg", "jpeg", "png", "gif", "webp"})

    def __init__(
        self,
        execution_client: Any = None,
        provider_registry: Any = None,
    ) -> None:
        self.execution_client = execution_client
        self.provider_registry = provider_registry
        self._provider: Any = None

    def _get_provider(self):
        if self._provider is None and self.provider_registry is not None:
            self._provider = self.provider_registry.get("minimax-image")
        return self._provider

    async def understand_image(self, prompt: str, image_url: str) -> dict[str, Any]:
        """Analyze an image and return a textual understanding.

        Args:
            prompt: Natural-language instruction for the vision model.
            image_url: URL of the image (http/https, data: URI).

        Returns:
            dict with 'content' (analysis text), 'success' (bool).
        """
        provider = self._get_provider()
        if provider is None or self.execution_client is None:
            return {
                "success": False,
                "error": "MiniMax Image provider not configured",
                "content": None,
            }

        try:
            result = await self.execution_client.execute_tool(
                provider,
                "understand_image",
                {"prompt": prompt, "image_url": image_url},
            )
            payload = result.payload
            if not isinstance(payload, dict):
                content = str(payload) if payload else ""
                return {"success": True, "content": content}

            content = payload.get("content") or payload.get("text") or payload.get("result") or ""
            return {
                "success": True,
                "content": str(content),
                "provider": result.provider,
            }
        except Exception as exc:
            logger.warning("MiniMax image understanding failed: %s", exc)
            return {"success": False, "error": str(exc), "content": None}
