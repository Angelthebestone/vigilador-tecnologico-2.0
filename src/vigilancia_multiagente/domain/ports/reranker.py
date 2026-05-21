"""Document reranking port.

Reorders a list of candidate documents by semantic relevance to a query.
Implementations may use a cross-encoder API (Cohere Rerank), embedding-based
cosine similarity, or any other strategy — callers do not depend on the
specifics.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class RankedDocument:
    index: int  # original position in the input list
    text: str
    score: float  # relevance in [0, 1] — higher = more relevant


class Reranker(Protocol):
    """Reorder ``documents`` by relevance to ``query``.

    By contract, implementations are resilient: on upstream/network error
    they return documents in their original order rather than raising.
    """

    async def rerank(
        self,
        query: str,
        documents: list[str],
        top_n: int | None = None,
    ) -> list[RankedDocument]: ...
