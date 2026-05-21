"""Tests SourceQualityStep — spec 007 T065.

Integracion del step con los 6 servicios mockeados.
Verifica que los findings se anoten correctamente.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from vigilancia_multiagente.application.agents.pipeline.source_quality_step import (
    SourceQualityAnnotation,
    SourceQualityStep,
)
from vigilancia_multiagente.application.agents.pipeline.tool_loop_step import ToolLoopContext
from vigilancia_multiagente.domain.evaluation_entities import (
    AffiliationType,
    AuthorReputation,
    ClaimExternalValidation,
    ConflictOfInterest,
    ExternalValidationStatus,
    FunderType,
    ReproducibilityScore,
    RiskLevel,
    SourceType,
    TemporalDecayConfig,
)
from vigilancia_multiagente.domain.models import BranchType, Finding, SourceRef


@pytest.fixture
def mock_services():
    author_gateway = AsyncMock()
    conflict_analyzer = AsyncMock()
    fact_checker = AsyncMock()
    retraction_monitor = AsyncMock()
    reproducibility_checker = AsyncMock()
    temporal_decay_store = AsyncMock()

    author_gateway.lookup.return_value = AuthorReputation(
        author_id="A123",
        display_name="Test Author",
        h_index=30,
        total_citations=2000,
        retraction_count=0,
        primary_affiliation="MIT",
        affiliation_type=AffiliationType.ACADEMIC,
    )
    conflict_analyzer.analyze.return_value = ConflictOfInterest(
        source_id=uuid4(),
        funder_entity="NIH",
        funder_type=FunderType.GOVERNMENT,
        corporate_ratio=0.0,
        risk_level=RiskLevel.LOW,
    )
    fact_checker.verify.return_value = ClaimExternalValidation(
        claim_id=uuid4(),
        external_db="google_factcheck",
        status=ExternalValidationStatus.VERIFIED,
    )
    retraction_monitor.is_retracted.return_value = None
    reproducibility_checker.score.return_value = ReproducibilityScore(
        finding_id=uuid4(),
        has_public_repo=True,
        has_open_data=True,
        has_reproducible_env=True,
        score=1.0,
    )
    temporal_decay_store.get.return_value = TemporalDecayConfig(
        domain="AI",
        half_life_months=12,
        source_type=SourceType.PAPER,
    )

    return {
        "author_gateway": author_gateway,
        "conflict_analyzer": conflict_analyzer,
        "fact_checker": fact_checker,
        "retraction_monitor": retraction_monitor,
        "reproducibility_checker": reproducibility_checker,
        "temporal_decay_store": temporal_decay_store,
    }


def _make_finding() -> Finding:
    return Finding(
        id=uuid4(),
        topic="AI in healthcare",
        statement="Deep learning models are transforming medical diagnosis",
        confidence=0.8,
        source_ids=[],
        tags=["AI", "healthcare"],
    )


def _make_source() -> SourceRef:
    return SourceRef(
        id=uuid4(),
        session_id=uuid4(),
        url="https://doi.org/10.1234/ai-health",
        provider="arxiv",
        branch_type=BranchType.AVANCES,
        accessed_at=datetime.now(),
    )


class MockIteration:
    def __init__(self, findings: list, sources: list):
        self.findings = findings
        self.sources = sources


@pytest.mark.asyncio
async def test_source_quality_step_annotates_findings(mock_services: dict) -> None:
    finding = _make_finding()
    source = _make_source()
    iteration = MockIteration(findings=[finding], sources=[source])

    session = AsyncMock()
    session.id = uuid4()
    session.user_query = "test query"

    ctx = ToolLoopContext(
        session=session,
        branch_config=AsyncMock(),
        policy=AsyncMock(),
        branch_overlay=AsyncMock(),
        iterations=[iteration],
        executions=["exec1"],
    )
    ctx.errors = []

    step = SourceQualityStep(
        author_reputation_gateway=mock_services["author_gateway"],
        conflict_analyzer=mock_services["conflict_analyzer"],
        fact_checker=mock_services["fact_checker"],
        retraction_monitor=mock_services["retraction_monitor"],
        reproducibility_checker=mock_services["reproducibility_checker"],
        temporal_decay_store=mock_services["temporal_decay_store"],
    )

    result = await step.run(ctx)

    annotations: list[SourceQualityAnnotation] = getattr(result, "source_quality_annotations", [])
    assert len(annotations) == 1
    ann = annotations[0]
    assert ann.author_reputation is not None
    assert ann.author_reputation.h_index == 30
    assert ann.conflict_of_interest is not None
    assert ann.conflict_of_interest.risk_level == RiskLevel.LOW
    assert ann.claim_external_validation is not None
    assert ann.claim_external_validation.status == ExternalValidationStatus.VERIFIED
    assert ann.retraction_status is None
    assert ann.reproducibility_score is not None
    assert ann.reproducibility_score.score == 1.0


@pytest.mark.asyncio
async def test_source_quality_step_no_services_still_works() -> None:
    finding = _make_finding()
    iteration = MockIteration(findings=[finding], sources=[])

    session = AsyncMock()
    session.id = uuid4()
    session.user_query = "test query"

    ctx = ToolLoopContext(
        session=session,
        branch_config=AsyncMock(),
        policy=AsyncMock(),
        branch_overlay=AsyncMock(),
        iterations=[iteration],
        executions=["exec1"],
    )
    ctx.errors = []

    step = SourceQualityStep()

    result = await step.run(ctx)

    annotations: list[SourceQualityAnnotation] = getattr(result, "source_quality_annotations", [])
    assert len(annotations) == 1
    ann = annotations[0]
    assert ann.author_reputation is None
    assert ann.conflict_of_interest is None
    assert ann.claim_external_validation is None


@pytest.mark.asyncio
async def test_source_quality_step_captures_errors(mock_services: dict) -> None:
    finding = _make_finding()
    source = _make_source()
    iteration = MockIteration(findings=[finding], sources=[source])

    session = AsyncMock()
    session.id = uuid4()
    session.user_query = "test query"

    ctx = ToolLoopContext(
        session=session,
        branch_config=AsyncMock(),
        policy=AsyncMock(),
        branch_overlay=AsyncMock(),
        iterations=[iteration],
        executions=["exec1"],
    )
    ctx.errors = []

    mock_services["author_gateway"].lookup.side_effect = RuntimeError("API timeout")

    step = SourceQualityStep(
        author_reputation_gateway=mock_services["author_gateway"],
    )

    await step.run(ctx)

    assert len(ctx.errors) >= 1
    error = ctx.errors[0]
    assert "API timeout" in error.reason
    assert error.workstream.value == "WS-A"
