"""MiniMax Image tool — native WRAP-SDK over MiniMax's image-gen REST API.

Spec 021 FR-053/054: native-first, universal Tool abstraction.
Catalog: ``minimax_image`` / domain ``creative`` / capabilities
``[generate_image, edit_image]``.

Strategy: WRAP-SDK using ``httpx``. The MiniMax image API uses the same
host as their text API (``api.minimax.io`` or ``api.minimax.chat``) but a
distinct API key (per Token Plan separation).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import httpx

from vigilancia_multiagente.enterprise.tooling.tool_wrapper import HealthcheckResult

_DEFAULT_TIMEOUT_S = 120.0


@dataclass(frozen=True)
class MiniMaxImageTool:
    """Native tool for MiniMax image generation/edit."""

    name: str = "minimax_image"
    domain: str = "creative"
    is_external_mcp: bool = False
    requires_auth: bool = True

    def _api_key(self) -> str | None:
        return os.getenv("VT_MINIMAX_IMAGE_API_KEY") or None

    def _base_url(self) -> str:
        return os.getenv("VT_MINIMAX_API_HOST") or "https://api.minimax.io"

    async def healthcheck(self) -> HealthcheckResult:
        if not self._api_key():
            return HealthcheckResult(
                status="UNCONFIGURED",
                error="VT_MINIMAX_IMAGE_API_KEY not set",
            )
        return HealthcheckResult(status="UP")

    async def execute(
        self, tool_name: str, args: dict[str, object]
    ) -> dict[str, object]:
        """Dispatch to the requested capability.

        Supported ``tool_name`` values:
        * ``generate_image`` — args: ``prompt`` (str, required),
          ``model`` (str, default ``image-01``),
          ``aspect_ratio`` (str, default ``1:1``).
        * ``edit_image`` — args: ``image_url`` (str), ``prompt`` (str),
          ``model`` (str, default ``image-01``).
        """
        api_key = self._api_key()
        if not api_key:
            raise RuntimeError(
                "MiniMaxImageTool: VT_MINIMAX_IMAGE_API_KEY not configured"
            )
        if tool_name == "generate_image":
            return await self._generate(api_key, args)
        if tool_name == "edit_image":
            return await self._edit(api_key, args)
        raise ValueError(
            f"MiniMaxImageTool: unknown tool_name '{tool_name}' "
            f"(supported: generate_image, edit_image)"
        )

    async def _generate(
        self, api_key: str, args: dict[str, object]
    ) -> dict[str, object]:
        prompt = args.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("MiniMaxImageTool: 'prompt' required")
        model = args.get("model") or "image-01"
        aspect_ratio = args.get("aspect_ratio") or "1:1"

        body = {"prompt": prompt, "model": model, "aspect_ratio": aspect_ratio}
        return await self._post(api_key, "/v1/image_generation", body, prompt)

    async def _edit(
        self, api_key: str, args: dict[str, object]
    ) -> dict[str, object]:
        image_url = args.get("image_url")
        prompt = args.get("prompt")
        if not isinstance(image_url, str) or not image_url.strip():
            raise ValueError("MiniMaxImageTool: 'image_url' required")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("MiniMaxImageTool: 'prompt' required")
        model = args.get("model") or "image-01"

        body = {"prompt": prompt, "image_url": image_url, "model": model}
        return await self._post(api_key, "/v1/image_edit", body, prompt)

    async def _post(
        self,
        api_key: str,
        path: str,
        body: dict[str, object],
        echo: str,
    ) -> dict[str, object]:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT_S) as client:
            response = await client.post(
                f"{self._base_url()}{path}", json=body, headers=headers
            )
            response.raise_for_status()
            payload = response.json()
        return {"prompt": echo, "result": payload}
