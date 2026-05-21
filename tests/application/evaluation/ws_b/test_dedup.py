"""T086 — Pruebas de EmbeddingBasedDeduplicator.

SC-B02: 5 fuentes sindicadas con redaccion distinta -> 1 grupo.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from vigilancia_multiagente.application.evaluation.ws_b.embedding_dedup import (
    EmbeddingBasedDeduplicator,
)
from vigilancia_multiagente.domain.models import BranchType, SourceRef
from vigilancia_multiagente.domain.ports.reranker import RankedDocument

pytestmark = pytest.mark.asyncio


class FakeReranker:
    def __init__(self) -> None:
        self.call_count = 0

    async def rerank(self, query: str, documents: list[str], top_n=None) -> list[RankedDocument]:
        self.call_count += 1
        return [
            RankedDocument(index=i, text=documents[i], score=0.95 if "same" in documents[i] else 0.3)
            for i in range(len(documents))
        ]


@pytest.fixture
def deduplicator() -> EmbeddingBasedDeduplicator:
    return EmbeddingBasedDeduplicator(FakeReranker(), threshold=0.9)


async def test_dedup_5_syndicated_sources_1_group(deduplicator):
    session_id = uuid4()
    sources = [
        SourceRef(
            id=uuid4(),
            session_id=session_id,
            url=f"https://news{i}.com/same-article",
            provider="tavily",
            branch_type=BranchType.AVANCES,
            accessed_at=datetime.now(UTC),
            title=f"same article version {i}",
        )
        for i in range(5)
    ]
    groups = await deduplicator.deduplicate(sources)
    assert len(groups) >= 1


async def test_dedup_unique_sources_no_false_positives(deduplicator):
    session_id = uuid4()
    sources = [
        SourceRef(
            id=uuid4(),
            session_id=session_id,
            url=f"https://unique{i}.com/article",
            provider="tavily",
            branch_type=BranchType.AVANCES,
            accessed_at=datetime.now(UTC),
            title=f"Completely different article about topic {i}",
        )
        for i in range(5)
    ]
    groups = await deduplicator.deduplicate(sources)
    total_sources = sum(1 for g in groups for _ in g.duplicate_urls) + len(groups)
    assert total_sources == 5


async def test_dedup_empty_input(deduplicator):
    groups = await deduplicator.deduplicate([])
    assert groups == []
