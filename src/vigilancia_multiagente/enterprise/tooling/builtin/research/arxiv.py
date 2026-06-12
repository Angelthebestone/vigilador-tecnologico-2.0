"""arXiv tool — WRAP-SDK over the official arxiv package.

Spec 021 FR-053/054: native-first, universal Tool abstraction.
Catalog: ``arxiv`` / domain ``research`` / capabilities
``[search_papers, get_paper, list_categories]``.

Strategy: WRAP-SDK using the official ``arxiv`` package.
Constitución #2 KISS — minimal client wrapper.

Module-level lock enforces arXiv's published 3-second minimum between
requests (constitución #4 — explicit, not silent).
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Final

import arxiv

from vigilancia_multiagente.enterprise.tooling.tool_wrapper import HealthcheckResult

_MIN_REQUEST_INTERVAL_S: Final[float] = 3.0  # arXiv polite-policy floor.

# arXiv top-level subject classes (subset of common cs/* tags published).
_TOP_CATEGORIES: Final[tuple[str, ...]] = (
    "cs.AI",
    "cs.CL",
    "cs.CV",
    "cs.LG",
    "cs.NE",
    "cs.RO",
    "stat.ML",
    "math.ST",
    "math.OC",
    "physics.comp-ph",
    "q-bio",
    "q-fin",
    "econ",
    "eess.SP",
)

# Module-level rate limiter (matches upstream behavior).
_last_request_time: float = 0.0
_request_lock = asyncio.Lock()


@dataclass(frozen=True)
class ArxivTool:
    """Native tool for arXiv search/retrieval."""

    name: str = "arxiv"
    domain: str = "research"
    is_external_mcp: bool = False
    requires_auth: bool = False

    async def healthcheck(self) -> HealthcheckResult:
        """arXiv is anonymous-public; always reports UP."""
        return HealthcheckResult(status="UP")

    async def execute(self, tool_name: str, args: dict[str, object]) -> dict[str, object]:
        """Dispatch to the requested capability.

        Supported ``tool_name`` values:
        * ``search_papers`` — args: ``query`` (str), ``max_results`` (int, default 10).
        * ``get_paper`` — args: ``paper_id`` (str, e.g. ``2401.12345``).
        * ``list_categories`` — no args; returns the curated subject list.
        """
        if tool_name == "search_papers":
            return await self._search(args)
        if tool_name == "get_paper":
            return await self._get_paper(args)
        if tool_name == "list_categories":
            return {"categories": list(_TOP_CATEGORIES)}
        raise ValueError(
            f"ArxivTool: unknown tool_name '{tool_name}' "
            f"(supported: search_papers, get_paper, list_categories)"
        )

    async def _search(self, args: dict[str, object]) -> dict[str, object]:
        query = args.get("query")
        if not isinstance(query, str) or not query.strip():
            raise ValueError("ArxivTool: 'query' must be a non-empty string")
        max_results = args.get("max_results", 10)
        if not isinstance(max_results, int) or max_results <= 0:
            max_results = 10

        async with _request_lock:
            global _last_request_time
            elapsed = time.monotonic() - _last_request_time
            if elapsed < _MIN_REQUEST_INTERVAL_S:
                await asyncio.sleep(_MIN_REQUEST_INTERVAL_S - elapsed)
            _last_request_time = time.monotonic()

        client = arxiv.Client()
        search = arxiv.Search(query=query, max_results=max_results)
        results = []
        for paper in client.results(search):
            results.append(
                {
                    "id": paper.entry_id,
                    "title": paper.title,
                    "summary": paper.summary,
                    "published": paper.published.isoformat() if paper.published else "",
                    "authors": [str(a) for a in paper.authors],
                    "categories": paper.categories,
                    "pdf_url": paper.pdf_url or "",
                }
            )

        return {"query": query, "results": results}

    async def _get_paper(self, args: dict[str, object]) -> dict[str, object]:
        paper_id = args.get("paper_id")
        if not isinstance(paper_id, str) or not paper_id.strip():
            raise ValueError("ArxivTool: 'paper_id' must be a non-empty string")

        async with _request_lock:
            global _last_request_time
            elapsed = time.monotonic() - _last_request_time
            if elapsed < _MIN_REQUEST_INTERVAL_S:
                await asyncio.sleep(_MIN_REQUEST_INTERVAL_S - elapsed)
            _last_request_time = time.monotonic()

        client = arxiv.Client()
        search = arxiv.Search(id_list=[paper_id], max_results=1)
        results = list(client.results(search))
        if not results:
            raise FileNotFoundError(f"ArxivTool: no paper found with id '{paper_id}'")

        paper = results[0]
        return {
            "paper_id": paper_id,
            "paper": {
                "id": paper.entry_id,
                "title": paper.title,
                "summary": paper.summary,
                "published": paper.published.isoformat() if paper.published else "",
                "authors": [str(a) for a in paper.authors],
                "categories": paper.categories,
                "pdf_url": paper.pdf_url or "",
            },
        }
