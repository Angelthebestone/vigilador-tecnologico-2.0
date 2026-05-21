"""Golden test para Source Quality — spec 007 T066.

Golden case: `author-reputation-baseline` con fuente de autor conocido
donde el h_index debe ser documentado correctamente.

Usa mocks de OpenAlex para ser determinista.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from vigilancia_multiagente.application.agents.pipeline.source_quality_step import (
    SourceQualityStep,
)
from vigilancia_multiagente.application.agents.pipeline.tool_loop_step import ToolLoopContext
from vigilancia_multiagente.domain.evaluation_entities import (
    AffiliationType,
    AuthorReputation,
    SourceType,
    TemporalDecayConfig,
)
from vigilancia_multiagente.domain.models import BranchType, Finding, SourceRef

_GOLDEN_AUTHOR_ID = "A123456789"
_GOLDEN_H_INDEX = 42
_GOLDEN_CITATIONS = 8500


class MockIteration:
    def __init__(self, findings: list, sources: list):
        self.findings = findings
        self.sources = sources


@pytest.mark.asyncio
async def test_author_reputation_baseline_golden() -> None:
    finding = Finding(
        id=uuid4(),
        topic="Deep Learning for Protein Folding",
        statement="AlphaFold demonstrates that deep learning can solve protein folding",
        confidence=0.85,
        source_ids=[],
        tags=["AI", "protein", "deepmind"],
    )
    source = SourceRef(
        id=uuid4(),
        session_id=uuid4(),
        url="https://doi.org/10.1234/alphafold",
        provider="arxiv",
        branch_type=BranchType.AVANCES,
        accessed_at=datetime.now(),
    )
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

    author_gateway = AsyncMock()
    author_gateway.lookup.return_value = AuthorReputation(
        author_id=_GOLDEN_AUTHOR_ID,
        display_name="Jane Golden Author",
        h_index=_GOLDEN_H_INDEX,
        total_citations=_GOLDEN_CITATIONS,
        retraction_count=0,
        primary_affiliation="Stanford University",
        affiliation_type=AffiliationType.ACADEMIC,
        domain_weights={"Artificial Intelligence": 0.95},
    )

    decay_store = AsyncMock()
    decay_store.get.return_value = TemporalDecayConfig(
        domain="AI", half_life_months=12, source_type=SourceType.PAPER
    )

    step = SourceQualityStep(
        author_reputation_gateway=author_gateway,
        temporal_decay_store=decay_store,
    )

    result = await step.run(ctx)

    annotations = getattr(result, "source_quality_annotations", [])
    assert len(annotations) == 1
    ann = annotations[0]

    # SC-A01: verificamos >= 4 dimensiones
    assert ann.author_reputation is not None
    rep = ann.author_reputation
    assert rep.h_index == _GOLDEN_H_INDEX  # h-index
    assert rep.total_citations == _GOLDEN_CITATIONS  # citas
    assert rep.primary_affiliation == "Stanford University"  # afiliacion
    assert rep.retraction_count == 0  # retracciones

    # Verificamos que decay_weight se computo (SC-A03)
    assert ann.decay_weight > 0
    # AI half-life=12 meses -> weight = 12/60 = 0.2
    assert ann.decay_weight == 0.2
