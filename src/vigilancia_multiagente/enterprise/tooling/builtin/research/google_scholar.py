"""Google Scholar tool — CLONE-UPSTREAM port from Google-Scholar-MCP-Server (MIT).

Source: https://github.com/adithya-s-k/google-scholar-mcp
License: MIT — see ``.mcp-servers/google-scholar/Google-Scholar-MCP-Server-main/``.

Spec 021 FR-053/054 + audit "CLONE-UPSTREAM" classification (Python repo).
Catalog: ``google_scholar`` / domain ``research`` / capabilities
``[search_papers, get_citations]``.

The upstream uses the ``scholarly`` Python package (which scrapes Google
Scholar with rotation/captcha handling). It is an optional dependency:
``pip install scholarly``. The catalog declares ``env_var: SERPER_API_KEY``
but the upstream code does NOT use Serper; it talks to Google Scholar
directly. We follow the upstream — no API key is needed — and surface
this discrepancy in :func:`docs/audit-mcp-strategy.json` for catalog cleanup.

``scholarly`` is sync; we offload calls via ``asyncio.to_thread``.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from vigilancia_multiagente.enterprise.tooling.tool_wrapper import HealthcheckResult


@dataclass(frozen=True)
class GoogleScholarTool:
    """Native tool for Google Scholar via the ``scholarly`` Python package."""

    name: str = "google_scholar"
    domain: str = "research"
    is_external_mcp: bool = False
    requires_auth: bool = False

    async def healthcheck(self) -> HealthcheckResult:
        """Verify the optional ``scholarly`` package is importable."""
        try:
            import scholarly  # noqa: F401  # presence-only import probe
        except ImportError:
            return HealthcheckResult(
                status="UNCONFIGURED",
                error=(
                    "scholarly package not installed; run `pip install scholarly` "
                    "to enable this tool"
                ),
            )
        return HealthcheckResult(status="UP")

    async def execute(
        self, tool_name: str, args: dict[str, object]
    ) -> dict[str, object]:
        """Dispatch to the requested capability.

        Supported ``tool_name`` values:
        * ``search_papers`` — args: ``query`` (str, required),
          ``num_results`` (int, default 5).
        * ``get_citations`` — args: ``paper_title`` (str, required).
          Returns the citation count + recent citing publications.
        """
        try:
            from scholarly import scholarly
        except ImportError as exc:
            raise RuntimeError(
                "GoogleScholarTool: scholarly package not installed"
            ) from exc

        if tool_name == "search_papers":
            query = args.get("query")
            if not isinstance(query, str) or not query.strip():
                raise ValueError(
                    "GoogleScholarTool: 'query' must be a non-empty string"
                )
            num_results = args.get("num_results", 5)
            if not isinstance(num_results, int) or num_results <= 0:
                num_results = 5
            return await asyncio.to_thread(
                _search_papers, scholarly, query, num_results
            )

        if tool_name == "get_citations":
            paper_title = args.get("paper_title")
            if not isinstance(paper_title, str) or not paper_title.strip():
                raise ValueError(
                    "GoogleScholarTool: 'paper_title' must be a non-empty string"
                )
            return await asyncio.to_thread(_get_citations, scholarly, paper_title)

        raise ValueError(
            f"GoogleScholarTool: unknown tool_name '{tool_name}' "
            f"(supported: search_papers, get_citations)"
        )


# ---------------------------------------------------------------------------
# Sync helpers (run in a worker thread; ``scholarly`` is sync only)
# ---------------------------------------------------------------------------


def _search_papers(
    scholarly_mod: object, query: str, num_results: int
) -> dict[str, object]:
    """Search Google Scholar and return up to ``num_results`` papers."""
    iterator = scholarly_mod.search_pubs(query)  # type: ignore[attr-defined]
    out: list[dict[str, object]] = []
    for _ in range(num_results):
        try:
            pub = next(iterator)
        except StopIteration:
            break
        bib = pub.get("bib", {}) if isinstance(pub, dict) else {}
        out.append(
            {
                "title": bib.get("title", ""),
                "authors": bib.get("author", ""),
                "abstract": bib.get("abstract", ""),
                "year": bib.get("pub_year", ""),
                "venue": bib.get("venue", ""),
                "url": pub.get("pub_url", "") if isinstance(pub, dict) else "",
                "num_citations": pub.get("num_citations", 0)
                if isinstance(pub, dict)
                else 0,
            }
        )
    return {"query": query, "results": out}


def _get_citations(scholarly_mod: object, paper_title: str) -> dict[str, object]:
    """Locate a paper by title and report its citation count."""
    iterator = scholarly_mod.search_pubs(paper_title)  # type: ignore[attr-defined]
    try:
        pub = next(iterator)
    except StopIteration:
        return {"paper_title": paper_title, "found": False}
    if not isinstance(pub, dict):
        return {"paper_title": paper_title, "found": False}
    bib = pub.get("bib", {})
    return {
        "paper_title": paper_title,
        "found": True,
        "matched_title": bib.get("title", ""),
        "num_citations": pub.get("num_citations", 0),
        "url": pub.get("pub_url", ""),
        "cites_id": pub.get("cites_id", []),
    }
