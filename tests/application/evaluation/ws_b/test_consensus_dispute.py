"""T090 — Pruebas de ConsensusDisputeMapper.

SC-B04: 3 afirmaciones contradictorias -> mapas de disputa.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from vigilancia_multiagente.application.evaluation.ws_b.consensus_dispute_mapper import (
    ConsensusDisputeMapperImpl,
)
from vigilancia_multiagente.domain.models import Finding

pytestmark = pytest.mark.asyncio


async def test_three_contradictory_claims():
    mapper = ConsensusDisputeMapperImpl()
    findings = [
        Finding(
            id=uuid4(),
            topic="AI regulation",
            statement="AI should be heavily regulated by governments",
            confidence=0.8,
            source_ids=[uuid4()],
        ),
        Finding(
            id=uuid4(),
            topic="AI regulation",
            statement="AI should not be regulated at all",
            confidence=0.7,
            source_ids=[uuid4()],
        ),
        Finding(
            id=uuid4(),
            topic="AI regulation",
            statement="Self-regulation by industry is sufficient",
            confidence=0.6,
            source_ids=[uuid4()],
        ),
    ]
    maps = await mapper.build(findings)
    assert len(maps) >= 1


async def test_no_disputes_with_single_finding():
    mapper = ConsensusDisputeMapperImpl()
    findings = [
        Finding(
            id=uuid4(),
            topic="Climate change",
            statement="Global temperatures are rising",
            confidence=0.9,
            source_ids=[uuid4()],
        ),
    ]
    maps = await mapper.build(findings)
    assert maps == []


async def test_disputes_contain_evidence_strength():
    mapper = ConsensusDisputeMapperImpl()
    findings = [
        Finding(
            id=uuid4(),
            topic="Quantum computing",
            statement="Quantum supremacy has been achieved",
            confidence=0.8,
            source_ids=[uuid4()],
        ),
        Finding(
            id=uuid4(),
            topic="Quantum computing",
            statement="Quantum supremacy has not been achieved",
            confidence=0.6,
            source_ids=[uuid4()],
        ),
    ]
    maps = await mapper.build(findings)
    assert len(maps) >= 1
    for m in maps:
        assert m.evidence_strength is not None
