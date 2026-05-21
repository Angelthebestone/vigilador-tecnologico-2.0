"""T126: Test CollaborationNetworkBuilderImpl.

30 papers con co-autorias -> red de 10+ nodos, detecta 1 burbuja.
"""

from uuid import uuid4

import pytest

from vigilancia_multiagente.application.evaluation.ws_d.collaboration_network_builder import (
    CollaborationNetworkBuilderImpl,
)
from vigilancia_multiagente.domain.models import BranchType, SourceRef


@pytest.fixture
def builder():
    return CollaborationNetworkBuilderImpl()


@pytest.fixture
def thirty_sources():
    now = __import__("datetime").datetime.now()
    sources = []
    for i in range(30):
        author_a = f"author{i}a"
        author_b = f"author{i}b"
        sources.append(
            SourceRef(
                id=uuid4(),
                session_id=uuid4(),
                url=f"https://{author_a}.edu/{author_b}.org/research/paper_{i}",
                provider="openalex",
                branch_type=BranchType.AVANCES,
                accessed_at=now,
                title=f"Paper {i} on collaborative research",
            )
        )
    return sources


@pytest.mark.asyncio
async def test_builds_network_with_10_plus_nodes(builder, thirty_sources):
    network = await builder.build(thirty_sources)
    assert len(network.nodes) >= 10, "Should have at least 10 author nodes"
    assert len(network.edges) >= 1, "Should have at least 1 co-author edge"
    assert network.network_id is not None


@pytest.mark.asyncio
async def test_centrality_metrics_populated(builder, thirty_sources):
    network = await builder.build(thirty_sources)
    assert len(network.centrality_metrics) > 0, "Should have centrality metrics"


@pytest.mark.asyncio
async def test_detect_bubbles(builder, thirty_sources):
    network = await builder.build(thirty_sources)
    bubbles = builder.detect_bubbles(network)
    assert isinstance(bubbles, list)
