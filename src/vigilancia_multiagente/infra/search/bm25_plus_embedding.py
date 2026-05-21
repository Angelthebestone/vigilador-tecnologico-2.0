"""BM25PlusEmbeddingSearchEngine — spec 007 T069.

Implementa HybridSearchEngine combinando BM25 (rank_bm25) con cosine
similarity via EmbeddingGateway.
"""

from __future__ import annotations

import math
from typing import cast

import numpy as np
from rank_bm25 import BM25Okapi

from vigilancia_multiagente.domain.evaluation_entities import HybridSearchQuery
from vigilancia_multiagente.domain.models import SourceRef
from vigilancia_multiagente.domain.ports.embedding_gateway import EmbeddingGateway, TaskType
from vigilancia_multiagente.domain.ports.hybrid_search import HybridSearchEngine


class BM25PlusEmbeddingSearchEngine:
    def __init__(self, embedding_gateway: EmbeddingGateway) -> None:
        self._embedding_gateway = embedding_gateway

    async def search(
        self,
        query: HybridSearchQuery,
        candidates: list[SourceRef],
        top_k: int = 10,
    ) -> list[SourceRef]:
        if not candidates:
            return []

        texts = [
            f"{c.title or ''} {c.url}".strip() or c.url for c in candidates
        ]
        tokenized_corpus = [text.lower().split() for text in texts]
        bm25 = BM25Okapi(tokenized_corpus)
        tokenized_query = query.text.lower().split()
        bm25_scores = bm25.get_scores(tokenized_query)

        bm25_norm = _normalize(bm25_scores)

        query_vec = await self._embedding_gateway.embed(
            query.text, task_type=TaskType.RETRIEVAL_QUERY
        )
        doc_vecs = await self._embedding_gateway.embed_documents(texts)
        emb_scores = [
            _cosine_similarity(query_vec, cast(list[float], dv))
            for dv in doc_vecs
        ]
        emb_norm = _normalize(emb_scores)

        combined = [
            query.vector_weight * emb_norm[i]
            + query.keyword_weight * bm25_norm[i]
            for i in range(len(candidates))
        ]

        ranked = sorted(
            zip(candidates, combined, strict=False),
            key=lambda x: x[1],
            reverse=True,
        )
        return [candidate for candidate, _score in ranked[:top_k]]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _normalize(values: list[float]) -> list[float]:
    if not values:
        return []
    arr = np.array(values, dtype=float)
    mn, mx = float(arr.min()), float(arr.max())
    if mx == mn:
        return [0.5] * len(values)
    return [float((v - mn) / (mx - mn)) for v in values]
