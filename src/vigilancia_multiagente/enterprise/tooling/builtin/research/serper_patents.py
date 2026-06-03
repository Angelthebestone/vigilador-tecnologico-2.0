"""Serper Patents tool — alias entry that delegates to ``SerperTool``.

Spec 021 FR-053/054: native-first, universal Tool abstraction.
Catalog: ``serper_patents`` / domain ``research`` / capabilities
``[patent_search, patent_details]``.

The catalog has both ``serper`` (4 capabilities) and ``serper_patents``
(2 capabilities, ``dedup_group: serper_capabilities``). Per FR-040, both
must register as separate ToolWrappers so the discovery layer can offer
patent-specific aliases without enabling the broader Google search surface.
This wrapper reuses the same REST backend.

``patent_details`` requests a single patent by id; we expose it as
``q="patent_id:XYZ"`` against the patents endpoint, which Serper handles.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import httpx

from vigilancia_multiagente.enterprise.tooling.tool_wrapper import HealthcheckResult

_SERPER_BASE_URL = "https://google.serper.dev"
_DEFAULT_TIMEOUT_S = 30.0


@dataclass(frozen=True)
class SerperPatentsTool:
    """Native tool exposing Serper's patent endpoint as a focused alias."""

    name: str = "serper_patents"
    domain: str = "research"
    is_external_mcp: bool = False
    requires_auth: bool = True

    def _api_key(self) -> str | None:
        return os.getenv("VT_SERPER_API_KEY") or None

    async def healthcheck(self) -> HealthcheckResult:
        if not self._api_key():
            return HealthcheckResult(
                status="UNCONFIGURED",
                error="VT_SERPER_API_KEY not set",
            )
        return HealthcheckResult(status="UP")

    async def execute(
        self, tool_name: str, args: dict[str, object]
    ) -> dict[str, object]:
        """Dispatch to patent endpoints.

        Supported ``tool_name`` values:
        * ``patent_search`` — args: ``query`` (str, required),
          ``num`` (int, default 10).
        * ``patent_details`` — args: ``patent_id`` (str, required).
        """
        api_key = self._api_key()
        if not api_key:
            raise RuntimeError(
                "SerperPatentsTool: VT_SERPER_API_KEY not configured"
            )

        if tool_name == "patent_search":
            query = args.get("query")
            if not isinstance(query, str) or not query.strip():
                raise ValueError(
                    "SerperPatentsTool: 'query' must be a non-empty string"
                )
            num = args.get("num", 10)
            if not isinstance(num, int) or num <= 0:
                num = 10
            return await self._post(api_key, {"q": query, "num": num}, query)

        if tool_name == "patent_details":
            patent_id = args.get("patent_id")
            if not isinstance(patent_id, str) or not patent_id.strip():
                raise ValueError(
                    "SerperPatentsTool: 'patent_id' must be a non-empty string"
                )
            return await self._post(
                api_key,
                {"q": f"patent_id:{patent_id}", "num": 1},
                patent_id,
            )

        raise ValueError(
            f"SerperPatentsTool: unknown tool_name '{tool_name}' "
            f"(supported: patent_search, patent_details)"
        )

    async def _post(
        self,
        api_key: str,
        body: dict[str, object],
        echo: str,
    ) -> dict[str, object]:
        headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT_S) as client:
            response = await client.post(
                f"{_SERPER_BASE_URL}/patents", json=body, headers=headers
            )
            response.raise_for_status()
            payload = response.json()
        return {"query": echo, "results": payload}
