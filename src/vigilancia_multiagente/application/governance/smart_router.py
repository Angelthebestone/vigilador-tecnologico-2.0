"""Dynamic tool-order router — selects optimal sequence based on query analysis."""

from __future__ import annotations

from dataclasses import dataclass

# Module-level constants (immutable by convention, never mutated at runtime)
_QUERY_TYPES: dict[str, tuple[str, ...]] = {
    "academic": ("search_papers", "search_google_scholar_key_words", "read_url"),
    "company": ("web_search_advanced_exa", "brave_web_search", "tavily_extract"),
    "patent": ("search_google_scholar_advanced", "search_papers", "read_url"),
    "news": ("brave_news_search", "tavily_search", "web_search_exa"),
    "deep_research": ("tavily_extract", "firecrawl_scrape", "read_url"),
    "general": (),
}

_KEYWORDS: dict[str, tuple[str, ...]] = {
    "academic": ("paper", "research", "study", "arxiv", "publication", "scholar"),
    "company": ("company", "startup", "enterprise", "vendor", "provider", "software"),
    "patent": ("patent", "ip", "intellectual property", "trademark", "copyright"),
    "news": ("news", "announce", "release", "latest", "update", "today"),
    "deep_research": ("analysis", "comparison", "review", "state of the art", "survey"),
}


@dataclass(frozen=True, slots=True)
class SmartToolRouter:
    """Stateless router that maps query text to optimal tool execution order.

    Each query type maps to a curated tool-order tuple. When the type cannot
    be determined, an empty tuple is returned so the caller can fall back to
    a default ordering.
    """

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
