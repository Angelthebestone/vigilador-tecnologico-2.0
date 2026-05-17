"""Dynamic tool-order router — selects optimal sequence based on query analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Module-level constants (immutable by convention, never mutated at runtime)
_QUERY_TYPES: dict[str, tuple[str, ...]] = {
    "academic": (
        "search_papers",
        "search_google_scholar_key_words",
        "convert_to_markdown",
        "read_url",
    ),
    "company": (
        "web_search_advanced_exa",
        "brave_web_search",
        "browser_navigate",
        "tavily_extract",
    ),
    "people": (
        "web_search_advanced_exa",
        "brave_web_search",
        "browser_navigate",
        "read_url",
    ),
    "patent": (
        "search_google_scholar_advanced",
        "search_papers",
        "convert_to_markdown",
        "read_url",
    ),
    "news": ("brave_news_search", "browser_navigate", "tavily_search", "web_search_exa"),
    "deep_research": (
        "tavily_extract",
        "execute_code",
        "firecrawl_scrape",
        "convert_to_markdown",
        "read_url",
    ),
    "general": (),
}

_KEYWORDS: dict[str, tuple[str, ...]] = {
    "academic": ("paper", "research", "study", "arxiv", "publication", "scholar"),
    "company": ("company", "startup", "enterprise", "vendor", "provider", "software"),
    "people": (
        "ceo",
        "cto",
        "founder",
        "fundador",
        "researcher",
        "investigador",
        "scientist",
        "científico",
        "director",
        "executive",
        "ejecutivo",
        "expert",
        "experto",
        "inventor",
        "professor",
        "profesor",
    ),
    "patent": ("patent", "ip", "intellectual property", "trademark", "copyright"),
    "news": ("news", "announce", "release", "latest", "update", "today"),
    "deep_research": ("analysis", "comparison", "review", "state of the art", "survey"),
}


@dataclass
class SmartToolRouter:
    """Router that maps query text to optimal tool execution order.

    Each query type maps to a curated tool-order tuple. When the type cannot
    be determined, an empty tuple is returned so the caller can fall back to
    a default ordering.

    When a source_scorer is provided, provider selection is influenced by
    historical trust scores.
    """

    source_scorer: Any = None

    _TOOL_QUERY_TYPES: dict[str, str] = field(
        default_factory=lambda: {
            "search_papers": "academic",
            "search_google_scholar_key_words": "academic",
            "search_google_scholar_advanced": "academic",
            "brave_web_search": "general",
            "brave_news_search": "news",
            "tavily_search": "general",
            "tavily_extract": "deep_research",
            "web_search_exa": "general",
            "web_search_advanced_exa": "company",
            "firecrawl_scrape": "deep_research",
            "read_url": "general",
            "fetch": "deep_research",
        }
    )

    def classify(self, query: str) -> str:
        """Classify *query* into a type based on keyword matching.

        The type with the highest keyword-hit count wins.
        Returns ``"general"`` if no keywords match.
        """
        lowered: str = query.lower()
        best_type: str = "general"
        best_score: int = 0

        for qtype, keywords in _KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in lowered)
            if score > best_score:
                best_score = score
                best_type = qtype

        return best_type

    def select(self, query: str) -> tuple[str, ...]:
        """Return the optimal tool-order tuple for *query*.

        Returns ``()`` when the type is ``"general"`` (caller falls back).
        """
        return _QUERY_TYPES.get(self.classify(query), ())

    def _classify_tool(self, tool_name: str) -> str:
        return self._TOOL_QUERY_TYPES.get(tool_name, "general")

    async def _select_provider(self, candidates: list[str], tool_name: str) -> str | None:
        """Pick best provider from *candidates* using source trust scores."""
        if len(candidates) <= 1:
            return candidates[0] if candidates else None
        if hasattr(self, "source_scorer") and self.source_scorer:
            preferred = await self.source_scorer.get_preferred_sources(limit=1)
            if preferred and preferred[0]["source_id"] in candidates:
                return preferred[0]["source_id"]
        return candidates[0]
