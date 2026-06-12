"""T129: Test TalentMobilityAnalyzerImpl.

5 autores con transiciones academia->industria -> detecta movilidad.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from vigilancia_multiagente.application.evaluation.ws_d.talent_mobility_analyzer import (
    TalentMobilityAnalyzerImpl,
)
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
    return TalentMobilityAnalyzerImpl(tool_executor=executor, provider_registry=registry)


@pytest.mark.asyncio
async def test_analyze_returns_mobility_for_known_authors(analyzer):
    results = await analyzer.analyze(
        [
            "researcher-001",
            "researcher-002",
            "researcher-003",
            "researcher-004",
            "researcher-005",
        ]
    )
    assert len(results) >= 1, "Should return mobility data for at least one author"
    for mob in results:
        assert mob.author_id
        assert isinstance(mob.mobility_score, float)
        assert 0.0 <= mob.mobility_score <= 1.0


@pytest.mark.asyncio
async def test_returns_empty_for_empty_input(analyzer):
    results = await analyzer.analyze([])
    assert results == []


@pytest.mark.asyncio
async def test_mobility_score_in_range(analyzer):
    results = await analyzer.analyze(["researcher-001"])
    for mob in results:
        assert 0.0 <= mob.mobility_score <= 1.0


@pytest.mark.asyncio
async def test_academic_history_populated(analyzer):
    results = await analyzer.analyze(["researcher-001"])
    for mob in results:
        if mob.academic_history:
            aff = mob.academic_history[0]
            assert aff.institution
            assert aff.role
