"""OpenAlex tool — WRAP-SDK over the pyalex package.

Spec 021 FR-053/054: native-first, universal Tool abstraction.
Catalog: ``openalex`` / domain ``research`` / capabilities
``[search_works, get_authors, get_institutions]``.

Strategy: WRAP-SDK using the official ``pyalex`` package.
Constitución #2 KISS — minimal client wrapper.

Reference: https://docs.openalex.org/
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import pyalex
from pyalex import Authors, Institutions, Works

from vigilancia_multiagente.enterprise.tooling.tool_wrapper import HealthcheckResult


@dataclass(frozen=True)
class OpenAlexTool:
    """Native tool for OpenAlex's free scholarly metadata API."""

    name: str = "openalex"
    domain: str = "research"
    is_external_mcp: bool = False
    requires_auth: bool = False

    def _configure(self) -> None:
        """Configure pyalex with polite pool email and optional API key."""
        mailto = os.getenv("VT_OPENALEX_EMAIL") or ""
        if mailto:
            pyalex.config.email = mailto
        api_key = os.getenv("VT_OPENALEX_API_KEY") or ""
        if api_key:
            pyalex.config.api_key = api_key

    async def healthcheck(self) -> HealthcheckResult:
        """Always reports UP — OpenAlex is anonymous-public."""
        return HealthcheckResult(status="UP")

    async def execute(self, tool_name: str, args: dict[str, object]) -> dict[str, object]:
        """Dispatch to the requested capability.

        Supported ``tool_name`` values:
        * ``search_works`` — args: ``query`` (str, required),
          ``per_page`` (int, default 25).
        * ``get_authors`` — args: ``query`` (str, required),
          ``per_page`` (int, default 25).
        * ``get_institutions`` — args: ``query`` (str, required),
          ``per_page`` (int, default 25).

        Raises:
            ValueError: if ``tool_name`` is not supported or query is empty.
        """
        self._configure()

        query = args.get("query")
        if not isinstance(query, str) or not query.strip():
            raise ValueError("OpenAlexTool: 'query' must be a non-empty string")
        per_page = args.get("per_page", 25)
        if not isinstance(per_page, int) or per_page <= 0:
            per_page = 25

        entity_map = {
            "search_works": Works,
            "get_authors": Authors,
            "get_institutions": Institutions,
        }
        entity_class = entity_map.get(tool_name)
        if entity_class is None:
            raise ValueError(
                f"OpenAlexTool: unknown tool_name '{tool_name}' "
                f"(supported: {', '.join(entity_map)})"
            )

        results = entity_class().search(query).per_page(per_page).get()

        return {
            "query": query,
            "tool": tool_name,
            "results": results,
            "meta": {"per_page": per_page, "count": len(results)},
        }
