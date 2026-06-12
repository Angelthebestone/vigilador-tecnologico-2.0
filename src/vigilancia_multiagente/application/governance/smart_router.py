"""Dynamic tool-order router — selects optimal sequence based on query analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Module-level constants (immutable by convention, never mutated at runtime)
_QUERY_TYPES: dict[str, tuple[str, ...]] = {
    "academic": (
        "search_papers",
        "download_paper",
        "read_paper",
        "search_google_scholar_key_words",
        "search_works",
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
        "search_authors_by_expertise",
        "get_author_info",
        "brave_web_search",
        "browser_navigate",
        "read_url",
    ),
    "patent": (
        "search_google_scholar_advanced",
        "search_papers",
        "download_paper",
        "read_paper",
        "search_works",
        "convert_to_markdown",
        "read_url",
    ),
    "news": ("brave_news_search", "browser_navigate", "tavily_search", "web_search_exa"),
    "bibliometric": (
        "search_works",
        "get_citation_network",
        "get_top_cited_works",
        "analyze_topic_trends",
        "get_trending_topics",
        "compare_research_areas",
        "analyze_geographic_distribution",
    ),
    "deep_research": (
        "fetch",
        "browser_navigate",
        "browser_snapshot",
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
    "patent": (
        "patent",
        "ip",
        "intellectual property",
        "trademark",
        "copyright",
        "patente",
        "prior art",
        "invención",
        "asignatario",
    ),
    "news": ("news", "announce", "release", "latest", "update", "today"),
    "bibliometric": (
        "citation",
        "citas",
        "h-index",
        "impact factor",
        "bibliometric",
        "bibliométrico",
        "co-authorship",
        "coautoría",
        "research trend",
        "tendencia de investigación",
        "most cited",
        "más citado",
    ),
    "deep_research": ("analysis", "comparison", "review", "state of the art", "survey"),
}

# tool -> query type. Single source of truth, reusada por ToolSelector para
# calcular afinidad query→tool sin duplicar la tabla. Toda tool registrada
# que un selector pueda recibir debería tener entrada aquí.
TOOL_QUERY_TYPES: dict[str, str] = {
    "search_papers": "academic",
    "download_paper": "academic",
    "read_paper": "academic",
    "search_google_scholar_key_words": "academic",
    "search_google_scholar_advanced": "patent",
    "get_author_info": "people",
    "brave_web_search": "general",
    "brave_news_search": "news",
    "tavily_search": "general",
    "tavily_extract": "deep_research",
    "web_search_exa": "general",
    "web_search_advanced_exa": "company",
    "firecrawl_scrape": "deep_research",
    "read_url": "general",
    "fetch": "deep_research",
    "convert_to_markdown": "deep_research",
    "browser_navigate": "deep_research",
    "browser_snapshot": "deep_research",
    "execute_code": "deep_research",
    "search_works": "bibliometric",
    "get_citation_network": "bibliometric",
    "get_top_cited_works": "bibliometric",
    "analyze_topic_trends": "bibliometric",
    "get_trending_topics": "bibliometric",
    "compare_research_areas": "bibliometric",
    "analyze_geographic_distribution": "bibliometric",
    "find_seminal_papers": "academic",
    "search_authors_by_expertise": "people",
    "google_search": "general",
    "google_search_patents": "patent",
    "google_search_scholar": "academic",
    "google_search_news": "news",
    "webpage_scrape": "deep_research",
    # ── Tools añadidas tras auditoría contra docs/repos oficiales ──
    # Tavily map/crawl: descubrimiento estructurado de un sitio.
    "tavily_map": "deep_research",
    "tavily_crawl": "deep_research",
    # Firecrawl: search → general; el resto, extracción profunda.
    "firecrawl_search": "general",
    "firecrawl_map": "deep_research",
    "firecrawl_crawl": "deep_research",
    "firecrawl_extract": "deep_research",
    "firecrawl_batch_scrape": "deep_research",
    "firecrawl_check_crawl_status": "deep_research",
    # Jina: lectura paralela y captura — extracción.
    "parallel_read_url": "deep_research",
    "capture_screenshot_url": "deep_research",
    # ArXiv: resumir/comparar papers — académico.
    "list_papers": "academic",
    "summarize_paper": "academic",
    "compare_papers": "academic",
    # OpenAlex autocomplete — bibliométrico.
    "autocomplete_search": "bibliometric",
    # Serper: vídeos/maps/places/reviews/shopping/lens/autocomplete.
    "google_search_images": "general",
    "google_search_videos": "news",
    "google_search_maps": "company",
    "google_search_places": "company",
    "google_search_reviews": "company",
    "google_search_shopping": "company",
    "google_search_lens": "general",
    "google_search_autocomplete": "general",
    # Brave summarizer — extracción/síntesis.
    "brave_summarizer": "deep_research",
    # Playwright: scraping avanzado sobre páginas con JS.
    "browser_navigate_back": "deep_research",
    "browser_take_screenshot": "deep_research",
    "browser_pdf_save": "deep_research",
    "browser_press_key": "deep_research",
    "browser_wait_for": "deep_research",
    "browser_evaluate": "deep_research",
    "browser_console_messages": "deep_research",
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
    strategy_memory: Any = None  # StrategyMemory opcional; sesga el tool-order

    _TOOL_QUERY_TYPES: dict[str, str] = field(default_factory=lambda: dict(TOOL_QUERY_TYPES))

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

        Si hay una estrategia aprendida de alta confianza para este tipo de
        query (StrategyMemory), se prioriza sobre el orden estático. Si no,
        cae al mapa estático; ``()`` cuando el tipo es ``"general"``.
        """
        query_type = self.classify(query)
        if self.strategy_memory is not None:
            learned = self.strategy_memory.best_tool_order(query_type)
            if learned:
                return learned
        return _QUERY_TYPES.get(query_type, ())

    def _classify_tool(self, tool_name: str) -> str:
        return self._TOOL_QUERY_TYPES.get(tool_name, "general")

    async def _select_provider(self, candidates: list[str], tool_name: str) -> str | None:
        """Pick best provider from *candidates* using source trust scores."""
        if len(candidates) <= 1:
            return candidates[0] if candidates else None
        if self.source_scorer:
            preferred = await self.source_scorer.get_preferred_sources(limit=1)
            if preferred and preferred[0]["source_id"] in candidates:
                return preferred[0]["source_id"]
        return candidates[0]
