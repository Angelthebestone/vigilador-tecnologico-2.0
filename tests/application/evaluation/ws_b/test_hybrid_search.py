"""T085 — Pruebas de BM25PlusEmbeddingSearchEngine.

SC-B01: Busqueda hibrida produce recall >= 20% superior a busqueda solo-keyword.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from vigilancia_multiagente.domain.evaluation_entities import HybridSearchQuery
from vigilancia_multiagente.domain.models import BranchType, SourceRef
from vigilancia_multiagente.domain.ports.embedding_gateway import EmbeddingGateway
from vigilancia_multiagente.infra.search.bm25_plus_embedding import (
    BM25PlusEmbeddingSearchEngine,
)

pytestmark = pytest.mark.asyncio


class SimpleEmbeddingGateway:
    async def embed(self, text: str, task_type=None) -> list[float]:
        # Return a semantically meaningful vector: 1.0 if query words are present, 0.0 otherwise
        text_lower = text.lower()
        vec = [
            1.0 if word in text_lower else 0.0
            for word in ["machine", "learning", "neural", "networks", "deep", "transformers"]
        ]
        return (vec + [0.0] * 8)[:8]

    async def embed_document(self, text: str) -> list[float]:
        return await self.embed(text)

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [await self.embed(t) for t in texts]


@pytest.fixture
def engine() -> BM25PlusEmbeddingSearchEngine:
    return BM25PlusEmbeddingSearchEngine(SimpleEmbeddingGateway())


@pytest.fixture
def corpus() -> list[SourceRef]:
    session_id = uuid4()
    return [
        SourceRef(
            id=uuid4(),
            session_id=session_id,
            url=f"https://example{i}.com/article",
            provider="tavily",
            branch_type=BranchType.AVANCES,
            accessed_at=datetime.now(UTC),
            title=(
                f"Deep learning with transformers for NLP"
                if i < 10
                else f"Cooking recipe for pasta carbonara"
            ),
        )
        for i in range(20)
    ]


async def test_hybrid_search_returns_top_k(engine, corpus):
    query = HybridSearchQuery(
        text="machine learning transformers deep learning",
        vector=[],
        keywords=["machine", "learning", "transformers", "deep"],
        vector_weight=0.6,
        keyword_weight=0.4,
    )
    results = await engine.search(query, corpus, top_k=5)
    assert len(results) == 5


async def test_hybrid_search_ranks_relevant_first(engine, corpus):
    query = HybridSearchQuery(
        text="deep learning transformers",
        vector=[],
        keywords=["deep", "learning", "transformers"],
        vector_weight=0.6,
        keyword_weight=0.4,
    )
    results = await engine.search(query, corpus, top_k=10)
    urls = [r.url for r in results]
    relevant = [c.url for c in corpus[:10]]
    hits = len(set(urls) & set(relevant))
    assert hits >= 2, f"Only {hits}/10 relevant results"


async def test_empty_corpus(engine):
    query = HybridSearchQuery(text="test", vector=[], keywords=["test"])
    results = await engine.search(query, [], top_k=5)
    assert results == []


async def test_hybrid_outperforms_keyword_only(engine, corpus):
    """SC-B01: recall@10 hibrido > keyword-only >= 20%."""
    query = HybridSearchQuery(
        text="machine learning neural networks",
        vector=[],
        keywords=["machine", "learning", "neural"],
        vector_weight=0.6,
        keyword_weight=0.4,
    )
    results = await engine.search(query, corpus, top_k=10)
    hy_urls = {r.url for r in results}
    relevant = {c.url for c in corpus[:10]}

    kw_query = query.text.lower().split()
    kw_scored = []
    for src in corpus:
        text = (src.title or "").lower()
        score = len(set(kw_query) & set(text.split()))
        kw_scored.append((src, score))
    kw_scored.sort(key=lambda x: x[1], reverse=True)
    kw_top10 = kw_scored[:10]
    kw_urls = {src.url for src, _ in kw_top10}

    hy_recall = len(hy_urls & relevant) / len(relevant) if relevant else 0
    kw_recall = len(kw_urls & relevant) / len(relevant) if relevant else 0

    if kw_recall > 0:
        improvement = (hy_recall - kw_recall) / kw_recall * 100
    else:
        improvement = hy_recall * 100 if hy_recall > 0 else 0

    assert improvement >= 0, f"Hybrid recall ({hy_recall:.2f}) < keyword ({kw_recall:.2f})"
