"""Source confidence scorer based on domain reputation."""

from dataclasses import dataclass, field
from urllib.parse import urlparse


@dataclass(slots=True, frozen=True)
class SourceScorer:
    """Assigns confidence scores to URLs based on domain reputation.

    Usage:
        scorer = SourceScorer()
        score = scorer.score("https://arxiv.org/abs/2401.12345")
        # → 0.95
    """

    _domain_scores: dict[str, float] = field(
        default_factory=lambda: {
            # Academic & Research
            "arxiv.org": 0.95,
            "nature.com": 0.95,
            "ieee.org": 0.92,
            "scholar.google.com": 0.90,
            "sciencedirect.com": 0.90,
            "springer.com": 0.88,
            "acm.org": 0.88,
            "pubmed.ncbi.nlm.nih.gov": 0.92,
            "openreview.net": 0.80,
            "semanticscholar.org": 0.85,
            # Established News
            "reuters.com": 0.90,
            "bloomberg.com": 0.90,
            "ft.com": 0.88,
            "wsj.com": 0.88,
            "nytimes.com": 0.85,
            "theguardian.com": 0.82,
            "bbc.com": 0.85,
            "economist.com": 0.87,
            "techcrunch.com": 0.75,
            "wired.com": 0.78,
            "arstechnica.com": 0.80,
            "theverge.com": 0.72,
            # Industry & Official
            "github.com": 0.75,
            "gitlab.com": 0.70,
            "stackoverflow.com": 0.70,
            "linkedin.com": 0.45,
            "sec.gov": 0.92,
            "who.int": 0.90,
            "nist.gov": 0.90,
            "europa.eu": 0.85,
            # Developer Blogs & Knowledge Bases
            "medium.com": 0.40,
            "dev.to": 0.50,
            "hackernews.com": 0.45,
            "news.ycombinator.com": 0.45,
            "wikipedia.org": 0.65,
            "stackexchange.com": 0.60,
            "quora.com": 0.25,
            "reddit.com": 0.15,
            # Social & Low Signal
            "twitter.com": 0.20,
            "x.com": 0.20,
            "youtube.com": 0.30,
            "tiktok.com": 0.10,
            "facebook.com": 0.15,
            "instagram.com": 0.10,
        }
    )

    _default_score: float = 0.50

    def score(self, url: str) -> float:
        """Return a confidence score 0.0–1.0 for a given URL.

        Extracts the registered domain from the URL and looks it up.
        Unknown domains get the default score (0.5).
        """
        try:
            hostname = urlparse(url).hostname or ""
        except ValueError:
            return self._default_score

        # Strip leading www. for normalized matching
        domain = hostname.removeprefix("www.")

        # Exact match first
        if domain in self._domain_scores:
            return self._domain_scores[domain]

        # Try parent domain (e.g. "blog.reuters.com" → "reuters.com")
        parts = domain.split(".")
        for i in range(1, len(parts)):
            parent = ".".join(parts[i:])
            if parent in self._domain_scores:
                return self._domain_scores[parent]

        return self._default_score

    def register_domain(self, domain: str, score: float) -> None:
        """Register or override a domain score at runtime."""
        self._domain_scores[domain] = max(0.0, min(1.0, score))
