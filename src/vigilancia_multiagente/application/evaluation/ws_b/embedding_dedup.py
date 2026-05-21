"""EmbeddingBasedDeduplicator — spec 007 T071.

Implementa SemanticDeduplicator reusando Reranker.
"""

from __future__ import annotations

import logging

from vigilancia_multiagente.domain.evaluation_entities import DedupedSource
from vigilancia_multiagente.domain.models import SourceRef
from vigilancia_multiagente.domain.ports.dedup import SemanticDeduplicator
from vigilancia_multiagente.domain.ports.reranker import Reranker

logger = logging.getLogger(__name__)


class EmbeddingBasedDeduplicator:
    def __init__(self, reranker: Reranker, threshold: float = 0.92) -> None:
        self._reranker = reranker
        self._threshold = threshold

    async def deduplicate(
        self,
        sources: list[SourceRef],
        threshold: float | None = None,
    ) -> list[DedupedSource]:
        if not sources:
            return []

        threshold = threshold if threshold is not None else self._threshold
        used: set[int] = set()
        groups: list[DedupedSource] = []

        for i in range(len(sources)):
            if i in used:
                continue
            candidates = [
                j
                for j in range(i + 1, len(sources))
                if j not in used
            ]
            if not candidates:
                groups.append(
                    DedupedSource(
                        canonical_url=sources[i].url,
                        duplicate_urls=[],
                        similarity_score=1.0,
                    )
                )
                continue

            docs_a = sources[i].title or sources[i].url
            doc_texts = [
                sources[j].title or sources[j].url for j in candidates
            ]

            try:
                reranked = await self._reranker.rerank(
                    query=docs_a, documents=doc_texts
                )
            except Exception as exc:
                logger.warning("Reranker failed during dedup: %s", exc)
                groups.append(
                    DedupedSource(
                        canonical_url=sources[i].url,
                        duplicate_urls=[],
                        similarity_score=1.0,
                    )
                )
                continue

            duplicates: list[str] = []
            for rd in reranked:
                if rd.score >= threshold:
                    idx = candidates[rd.index]
                    duplicates.append(sources[idx].url)
                    used.add(idx)

            groups.append(
                DedupedSource(
                    canonical_url=sources[i].url,
                    duplicate_urls=duplicates,
                    similarity_score=(
                        max(rd.score for rd in reranked) if reranked else 1.0
                    ),
                )
            )

        return groups
