"""MiniMax Image tool — BaseHTTPProvider subclass.

Spec 021 FR-053/054: native-first, universal Tool abstraction.
Catalog: ``minimax_image`` / domain ``creative`` / capabilities
``[generate_image, edit_image]``.

Strategy: Subclass ``BaseHTTPProvider``. Uses default Bearer auth.
Overrides timeout to 120s for image generation.
"""

from __future__ import annotations

import os
from typing import Any, ClassVar

import httpx

from vigilancia_multiagente.enterprise.tooling.builtin._base.http_provider import (
    BaseHTTPProvider,
)


def _resolve_base_url() -> str:
    return os.environ.get("VT_MINIMAX_API_HOST") or "https://api.minimax.io"


class MiniMaxImageTool(BaseHTTPProvider):
    """Native tool for MiniMax image generation/edit."""

    name: ClassVar[str] = "minimax_image"
    domain: ClassVar[str] = "creative"
    base_url: ClassVar[str] = _resolve_base_url()
    auth_env_var: ClassVar[str | None] = "VT_MINIMAX_IMAGE_API_KEY"
    requires_auth: ClassVar[bool] = True

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
                timeout=httpx.Timeout(120.0, connect=5.0),
            )
        return self._client

    async def execute(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        if tool_name == "generate_image":
            return await self._generate(args)
        if tool_name == "edit_image":
            return await self._edit(args)
        raise ValueError(
            f"MiniMaxImageTool: unknown tool_name '{tool_name}' "
            f"(supported: generate_image, edit_image)"
        )

    async def _generate(self, args: dict[str, Any]) -> dict[str, Any]:
        prompt = args.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("MiniMaxImageTool: 'prompt' required")
        model = args.get("model") or "image-01"
        aspect_ratio = args.get("aspect_ratio") or "1:1"

        body = {"prompt": prompt, "model": model, "aspect_ratio": aspect_ratio}
        payload = await self.post("/v1/image_generation", json=body)
        return {"prompt": prompt, "result": payload}

    async def _edit(self, args: dict[str, Any]) -> dict[str, Any]:
        image_url = args.get("image_url")
        prompt = args.get("prompt")
        if not isinstance(image_url, str) or not image_url.strip():
            raise ValueError("MiniMaxImageTool: 'image_url' required")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("MiniMaxImageTool: 'prompt' required")
        model = args.get("model") or "image-01"

        body = {"prompt": prompt, "image_url": image_url, "model": model}
        payload = await self.post("/v1/image_edit", json=body)
        return {"prompt": prompt, "result": payload}
