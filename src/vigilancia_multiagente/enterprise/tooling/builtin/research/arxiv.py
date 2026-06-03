"""arXiv tool — CLONE-UPSTREAM port of arxiv-mcp-server (v0.5.0, MIT).

Source: https://github.com/blazickjp/arxiv-mcp-server
License: MIT — see ``.mcp-servers/arxiv/arxiv-mcp-server-0.5.0/LICENSE``.

Spec 021 FR-053/054 + audit "CLONE-UPSTREAM" classification (Python repo).
Catalog: ``arxiv`` / domain ``research`` / capabilities
``[search_papers, get_paper, list_categories]``.

The upstream server has many extra features (alerts, citation graphs,
prompt templates) that aren't in our catalog; this port keeps only the
3 declared capabilities and the upstream's rate-limit discipline.

Module-level lock + ``_MIN_REQUEST_INTERVAL`` enforces arXiv's published
3-second minimum between requests (constitución #4 — explicit, not silent).
"""

from __future__ import annotations

import asyncio
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Final

import httpx

from vigilancia_multiagente.enterprise.tooling.tool_wrapper import HealthcheckResult

_ARXIV_API_URL: Final[str] = "https://export.arxiv.org/api/query"
_USER_AGENT: Final[str] = (
    "vigilador-tecnologico/3.0 (adapted from arxiv-mcp-server; research tool)"
)
_MIN_REQUEST_INTERVAL_S: Final[float] = 3.0  # arXiv polite-policy floor.
_DEFAULT_TIMEOUT_S: Final[float] = 30.0
_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}
# arXiv top-level subject classes (subset of common cs/* tags published).
_TOP_CATEGORIES: Final[tuple[str, ...]] = (
    "cs.AI", "cs.CL", "cs.CV", "cs.LG", "cs.NE", "cs.RO",
    "stat.ML", "math.ST", "math.OC", "physics.comp-ph",
    "q-bio", "q-fin", "econ", "eess.SP",
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

    async def execute(
        self, tool_name: str, args: dict[str, object]
    ) -> dict[str, object]:
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
        from urllib.parse import quote_plus

        query = args.get("query")
        if not isinstance(query, str) or not query.strip():
            raise ValueError("ArxivTool: 'query' must be a non-empty string")
        max_results = args.get("max_results", 10)
        if not isinstance(max_results, int) or max_results <= 0:
            max_results = 10

        url = (
            f"{_ARXIV_API_URL}?search_query=all:{quote_plus(query)}"
            f"&max_results={max_results}"
        )
        body = await _rate_limited_get(url)
        return {"query": query, "results": _parse_atom(body)}

    async def _get_paper(self, args: dict[str, object]) -> dict[str, object]:
        paper_id = args.get("paper_id")
        if not isinstance(paper_id, str) or not paper_id.strip():
            raise ValueError("ArxivTool: 'paper_id' must be a non-empty string")
        url = f"{_ARXIV_API_URL}?id_list={paper_id}&max_results=1"
        body = await _rate_limited_get(url)
        results = _parse_atom(body)
        if not results:
            raise FileNotFoundError(f"ArxivTool: no paper found with id '{paper_id}'")
        return {"paper_id": paper_id, "paper": results[0]}


# ---------------------------------------------------------------------------
# arXiv API helpers (adapted from upstream tools/search.py — MIT)
# ---------------------------------------------------------------------------


async def _rate_limited_get(url: str) -> str:
    """GET respecting arXiv's 3s polite-policy floor; explicit on rate-limit."""
    global _last_request_time
    async with _request_lock:
        elapsed = time.monotonic() - _last_request_time
        if elapsed < _MIN_REQUEST_INTERVAL_S:
            await asyncio.sleep(_MIN_REQUEST_INTERVAL_S - elapsed)
        _last_request_time = time.monotonic()

    headers = {"User-Agent": _USER_AGENT}
    async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT_S) as client:
        response = await client.get(url, headers=headers)
        if response.status_code in (429, 503):
            raise RuntimeError(
                f"ArxivTool: arXiv rate-limited this IP (HTTP {response.status_code}). "
                "Wait 60s before retrying."
            )
        response.raise_for_status()
        return response.text


def _parse_atom(xml_body: str) -> list[dict[str, object]]:
    """Parse arXiv's Atom feed → list of paper dicts."""
    root = ET.fromstring(xml_body)
    out: list[dict[str, object]] = []
    for entry in root.findall("atom:entry", _NS):
        out.append(
            {
                "id": _text(entry, "atom:id"),
                "title": _text(entry, "atom:title").strip(),
                "summary": _text(entry, "atom:summary").strip(),
                "published": _text(entry, "atom:published"),
                "authors": [
                    _text(a, "atom:name")
                    for a in entry.findall("atom:author", _NS)
                ],
                "categories": [
                    c.attrib.get("term", "")
                    for c in entry.findall("atom:category", _NS)
                ],
                "pdf_url": next(
                    (
                        link.attrib.get("href", "")
                        for link in entry.findall("atom:link", _NS)
                        if link.attrib.get("title") == "pdf"
                    ),
                    "",
                ),
            }
        )
    return out


def _text(elem: ET.Element, path: str) -> str:
    found = elem.find(path, _NS)
    return found.text if (found is not None and found.text) else ""
