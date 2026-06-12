"""Tests LlmConflictOfInterestAnalyzer — spec 007 T063."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest

from vigilancia_multiagente.application.evaluation.ws_a.llm_conflict_analyzer import (
    LlmConflictOfInterestAnalyzer,
)
from vigilancia_multiagente.domain.evaluation_entities import (
    FunderType,
    RiskLevel,
)
from vigilancia_multiagente.domain.models import BranchType, SourceRef


class DummyResponse:
    def __init__(self, content: str) -> None:
        self.content = content


class DummyLLM:
    def __init__(self, content: str) -> None:
        self.content = content

    async def complete(self, messages, **kwargs):
        del messages, kwargs
        return DummyResponse(self.content)


def _make_source() -> SourceRef:
    return SourceRef(
        id=uuid4(),
        session_id=uuid4(),
        url="https://example.com/paper",
        provider="arxiv",
        branch_type=BranchType.AVANCES,
        accessed_at=datetime.now(),
    )


@pytest.mark.asyncio
async def test_high_corporate_ratio() -> None:
    """Corporate ratio >= 0.7 should result in HIGH risk."""
    llm = DummyLLM(
        '{"funder_entity": "Big Pharma Corp", "funder_type": "corporate", "corporate_ratio": 0.85}'
    )
    analyzer = LlmConflictOfInterestAnalyzer(llm)
    source = _make_source()

    result = await analyzer.analyze(source)

    assert result is not None
    assert result.risk_level == RiskLevel.HIGH
    assert result.funder_type == FunderType.CORPORATE
    assert result.corporate_ratio == 0.85


@pytest.mark.asyncio
async def test_medium_corporate_ratio() -> None:
    """Corporate ratio >= 0.4 but < 0.7 should result in MEDIUM risk."""
    llm = DummyLLM(
        '{"funder_entity": "Mixed Funding Inc", "funder_type": "corporate", "corporate_ratio": 0.5}'
    )
    analyzer = LlmConflictOfInterestAnalyzer(llm)
    source = _make_source()

    result = await analyzer.analyze(source)

    assert result is not None
    assert result.risk_level == RiskLevel.MEDIUM


@pytest.mark.asyncio
async def test_low_corporate_ratio() -> None:
    """Corporate ratio < 0.4 should result in LOW risk."""
    llm = DummyLLM('{"funder_entity": "NIH", "funder_type": "government", "corporate_ratio": 0.1}')
    analyzer = LlmConflictOfInterestAnalyzer(llm)
    source = _make_source()

    result = await analyzer.analyze(source)

    assert result is not None
    assert result.risk_level == RiskLevel.LOW
    assert result.funder_type == FunderType.GOVERNMENT


@pytest.mark.asyncio
async def test_llm_failure_returns_low_risk() -> None:
    """LLM failure should fall back to LOW risk gracefully."""

    class BrokenLLM:
        async def complete(self, messages, **kwargs):
            del messages, kwargs
            raise RuntimeError("LLM connection timeout")

    analyzer = LlmConflictOfInterestAnalyzer(BrokenLLM())
    source = _make_source()

    result = await analyzer.analyze(source)

    assert result is not None
    assert result.risk_level == RiskLevel.LOW
    assert result.funder_type == FunderType.UNKNOWN
