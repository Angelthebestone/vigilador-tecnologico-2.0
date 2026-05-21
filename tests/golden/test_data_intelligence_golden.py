"""T092 — Golden test: DataIntelligenceStep ejecuta todas las sub-fases.

Verifica que hybrid_search -> dedup -> schema_validate -> authenticity
-> multilingual -> consensus_dispute se ejecutan sin error.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from vigilancia_multiagente.application.agents.pipeline.data_intelligence_step import (
    DataIntelligenceStep,
)
from vigilancia_multiagente.application.agents.pipeline.tool_loop_step import ToolLoopContext
from vigilancia_multiagente.application.evaluation.authenticity.local_perplexity_detector import (
    LocalPerplexityAuthenticityDetector,
)
from vigilancia_multiagente.application.evaluation.ws_b.consensus_dispute_mapper import (
    ConsensusDisputeMapperImpl,
)
from vigilancia_multiagente.application.evaluation.ws_b.embedding_dedup import (
    EmbeddingBasedDeduplicator,
)
from vigilancia_multiagente.application.evaluation.ws_b.llm_multilingual import (
    LlmMultilingualNormalizer,
)
from vigilancia_multiagente.application.evaluation.ws_b.pydantic_schema_registry import (
    PydanticExtractionSchemaRegistry,
)
from vigilancia_multiagente.domain.models import (
    BranchConfig,
    BranchType,
    Finding,
    ResearchSession,
    SourceRef,
)
from vigilancia_multiagente.domain.ports.reranker import RankedDocument
from vigilancia_multiagente.domain.session_state import SessionStatus

pytestmark = pytest.mark.asyncio


class FakeHybridSearch:
    async def search(self, query, candidates, top_k=10):
        return candidates[:5]


class FakeDedup:
    def __init__(self) -> None:
        self.deduplicate = AsyncMock(return_value=[])


class FakeSchemaRegistry:
    def get_schema(self, source_type, domain):
        from vigilancia_multiagente.domain.evaluation_entities import (
            ExtractionSchema,
            SourceType,
        )

        return ExtractionSchema(
            source_type=SourceType.NEWS,
            domain="general",
            json_schema={"title": "str"},
            version=1,
        )

    def validate(self, raw, schema):
        return raw


class FakeLLM:
    complete = AsyncMock(
        return_value={
            "choices": [{"message": {"content": '{"language": "en"}'}}]
        }
    )


class FakeReranker:
    async def rerank(self, query, documents, top_n=None):
        return [
            RankedDocument(index=i, text=documents[i], score=0.5)
            for i in range(len(documents))
        ]


@pytest.fixture
def ctx() -> ToolLoopContext:
    session_id = uuid4()
    sources = [
        SourceRef(
            id=uuid4(),
            session_id=session_id,
            url=f"https://example{i}.com",
            provider="tavily",
            branch_type=BranchType.AVANCES,
            accessed_at=datetime.now(UTC),
            title=f"Article {i}",
        )
        for i in range(3)
    ]
    _session = ResearchSession(
        id=session_id, user_query="test",
        created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
        status=SessionStatus.DRAFT,
    )
    _branch = BranchConfig(
        branch_type=BranchType.AVANCES,
        focus_queries=["test"],
        mcp_providers=["tavily"],
    )
    ctx = ToolLoopContext(
        session=_session,
        branch_config=_branch,
        branch_overlay=object(),
        policy=object(),
        query_type="general",
        seed_query="machine learning",
        executions=[object()],
        errors=[],
    )
    ctx.sources = sources
    return ctx


async def test_data_intelligence_step_runs_all_phases(ctx):
    step = DataIntelligenceStep(
        hybrid_search=FakeHybridSearch(),
        deduplicator=EmbeddingBasedDeduplicator(FakeReranker(), threshold=0.9),
        schema_registry=FakeSchemaRegistry(),
        multilingual=LlmMultilingualNormalizer(FakeLLM()),
        authenticity_detector=LocalPerplexityAuthenticityDetector(FakeLLM()),
        consensus_dispute=ConsensusDisputeMapperImpl(),
    )

    result = await step.run(ctx)
    assert result is ctx
    assert len(result.errors) == 0


async def test_data_intelligence_step_empty_executions():
    _session = ResearchSession(
        id=uuid4(), user_query="test",
        created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
        status=SessionStatus.DRAFT,
    )
    _branch = BranchConfig(
        branch_type=BranchType.AVANCES,
        focus_queries=["test"],
        mcp_providers=[],
    )
    ctx = ToolLoopContext(
        session=_session,
        branch_config=_branch,
        branch_overlay=object(),
        policy=object(),
        query_type="general",
        seed_query="test",
        executions=[],
        errors=[],
    )
    step = DataIntelligenceStep()
    result = await step.run(ctx)
    assert result is ctx


async def test_data_intelligence_step_graceful_failure():
    class BrokenSearch:
        async def search(self, query, candidates, top_k=10):
            raise RuntimeError("Search failed")

    _session = ResearchSession(
        id=uuid4(), user_query="test",
        created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
        status=SessionStatus.DRAFT,
    )
    _branch = BranchConfig(
        branch_type=BranchType.AVANCES,
        focus_queries=["test"],
        mcp_providers=[],
    )
    session_id = uuid4()
    ctx = ToolLoopContext(
        session=_session,
        branch_config=_branch,
        branch_overlay=object(),
        policy=object(),
        query_type="general",
        seed_query="test",
        executions=[object()],
        errors=[],
    )
    ctx.sources = [
        SourceRef(
            id=uuid4(),
            session_id=session_id,
            url="https://example.com",
            provider="tavily",
            branch_type=BranchType.AVANCES,
            accessed_at=datetime.now(UTC),
        )
    ]
    step = DataIntelligenceStep(hybrid_search=BrokenSearch())
    result = await step.run(ctx)
    assert len(result.errors) >= 1
    assert result.errors[0].workstream.value == "WS-B"
