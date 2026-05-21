#!/usr/bin/env python3
"""Benchmark: compara recall@10 con WS-B flag off vs on.

Ejecuta busquedas sobre un corpus sintetico, primero con busqueda solo-keyword
(flag off) y luego con busqueda hibrida (flag on). Reporta recall@10 como JSON.

Uso:
    python scripts/benchmark_recall.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vigilancia_multiagente.domain.evaluation_entities import (
    HybridSearchQuery,
)
from vigilancia_multiagente.domain.models import BranchType, SourceRef
from vigilancia_multiagente.infra.search.bm25_plus_embedding import (
    BM25PlusEmbeddingSearchEngine,
)


class FakeEmbeddingGateway:
    async def embed(self, text: str, task_type=None) -> list[float]:
        return [hash(text) % 1000 / 1000.0] * 8

    async def embed_document(self, text: str) -> list[float]:
        return await self.embed(text)

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [await self.embed(t) for t in texts]


def _build_corpus() -> tuple[str, list[SourceRef], list[SourceRef]]:
    """Devuelve (query, candidates, relevant_docs) para el benchmark."""
    session_id = uuid4()
    query = "machine learning transformers neural networks"
    candidates: list[SourceRef] = []
    for i in range(50):
        candidates.append(
            SourceRef(
                id=uuid4(),
                session_id=session_id,
                url=f"https://example{i}.com/article",
                provider="tavily",
                branch_type=BranchType.AVANCES,
                accessed_at=datetime.now(UTC),
                title=f"Article {i} about {'ML' if i < 15 else 'cooking recipes'}",
            )
        )
    relevant = candidates[:15]
    return query, candidates, relevant


async def benchmark_keyword_only(
    query: str, candidates: list[SourceRef], relevant: list[SourceRef]
) -> dict[str, object]:
    """Simula busqueda solo-keyword: ordena por coincidencia de terminos."""
    query_terms = set(query.lower().split())
    scored = []
    for src in candidates:
        text = (src.title or "").lower()
        score = len(query_terms & set(text.split()))
        scored.append((src, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    top10 = scored[:10]
    retrieved = {src.url for src, _ in top10}
    relevant_set = {src.url for src in relevant}
    hits = len(retrieved & relevant_set)
    recall = hits / len(relevant_set) if relevant_set else 0.0
    return {"recall@10": round(recall, 4), "hits": hits, "total_relevant": len(relevant_set)}


async def benchmark_hybrid(
    query: str, candidates: list[SourceRef], relevant: list[SourceRef]
) -> dict[str, object]:
    """Simula busqueda hibrida (BM25 + embeddings)."""
    engine = BM25PlusEmbeddingSearchEngine(FakeEmbeddingGateway())
    hq = HybridSearchQuery(
        text=query,
        vector=[],
        keywords=query.lower().split(),
        vector_weight=0.6,
        keyword_weight=0.4,
    )
    results = await engine.search(hq, candidates, top_k=10)
    retrieved = {src.url for src in results}
    relevant_set = {src.url for src in relevant}
    hits = len(retrieved & relevant_set)
    recall = hits / len(relevant_set) if relevant_set else 0.0
    return {"recall@10": round(recall, 4), "hits": hits, "total_relevant": len(relevant_set)}


async def main() -> None:
    query, candidates, relevant = _build_corpus()

    kw_result = await benchmark_keyword_only(query, candidates, relevant)
    hy_result = await benchmark_hybrid(query, candidates, relevant)

    improvement = (
        (hy_result["recall@10"] - kw_result["recall@10"]) / kw_result["recall@10"] * 100
        if kw_result["recall@10"] > 0
        else 0.0
    )

    result = {
        "scenario": "SC-B01",
        "query": query,
        "corpus_size": len(candidates),
        "relevant_count": len(relevant),
        "keyword_only": kw_result,
        "hybrid": hy_result,
        "improvement_pct": round(improvement, 2),
        "benchmark_passed": improvement >= 20.0,
    }

    print(json.dumps(result, indent=2))
    sys.exit(0 if result["benchmark_passed"] else 1)


if __name__ == "__main__":
    asyncio.run(main())
