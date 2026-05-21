"""T130: Test PatentingGapAnalyzerImpl.

Subdominio con pub/patent ratio 5:1 -> blue_ocean.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from vigilancia_multiagente.application.evaluation.ws_d.patenting_gap_analyzer import (
    PatentingGapAnalyzerImpl,
)
from vigilancia_multiagente.domain.evaluation_entities import PatentingClassification
from vigilancia_multiagente.domain.ports.provider_registry import ProviderConfig


@pytest.fixture
def analyzer():
    executor = AsyncMock()

    async def fake_execute_tool(provider, tool_name, arguments):
        return MagicMock(payload={"results": [], "items": [], "organic": []})

    executor.execute_tool = fake_execute_tool
    registry = MagicMock()
    provider_config = MagicMock(spec=ProviderConfig)
    provider_config.enabled_tools = ["google_search_patents"]
    registry.get.return_value = provider_config
    return PatentingGapAnalyzerImpl(
        tool_executor=executor, provider_registry=registry
    )


@pytest.mark.asyncio
async def test_blue_ocean_classification(analyzer):
    gaps = await analyzer.analyze(["quantum computing", "AI biology"])
    assert len(gaps) >= 1
    for gap in gaps:
        assert gap.subdomain
        assert gap.publication_density > 0
        assert gap.patent_density >= 0
        assert gap.gap_score > 0
        assert gap.classification in PatentingClassification


@pytest.mark.asyncio
async def test_returns_empty_for_empty_input(analyzer):
    gaps = await analyzer.analyze([])
    assert gaps == []


@pytest.mark.asyncio
async def test_classification_enum_coverage(analyzer):
    gaps = await analyzer.analyze(["machine learning", "blockchain", "nuclear fusion"])
    classifications = {g.classification for g in gaps}
    assert len(classifications) >= 1, "Should have at least one classification"
    all_valid = all(c in PatentingClassification for c in classifications)
    assert all_valid, "All classifications should be valid PatentingClassification values"
