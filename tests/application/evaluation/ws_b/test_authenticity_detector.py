"""T089 — Pruebas de LocalPerplexityAuthenticityDetector.

SC-B05: muestra humana vs muestra LLM, precision >= 0.7.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from vigilancia_multiagente.application.evaluation.authenticity.local_perplexity_detector import (
    LocalPerplexityAuthenticityDetector,
)
from vigilancia_multiagente.domain.models import BranchType, SourceRef

pytestmark = pytest.mark.asyncio


class MockLLMClient:
    def __init__(self) -> None:
        self.complete = AsyncMock()

    def set_logprob(self, logprob: float) -> None:
        self.complete.return_value = {
            "choices": [{
                "logprobs": {"token_logprobs": [logprob] * 5}
            }]
        }


@pytest.fixture
def llm_client() -> MockLLMClient:
    return MockLLMClient()


@pytest.fixture
def detector(llm_client) -> LocalPerplexityAuthenticityDetector:
    return LocalPerplexityAuthenticityDetector(llm_client)


@pytest.fixture
def source() -> SourceRef:
    return SourceRef(
        id=uuid4(),
        session_id=uuid4(),
        url="https://example.com/article",
        provider="tavily",
        branch_type=BranchType.AVANCES,
        accessed_at=datetime.now(UTC),
        title="Test article",
    )


_HUMAN_TEXT = (
    "We developed a novel approach for protein folding using experimental "
    "methods that required three years of validation. The results were "
    "reproducible across five laboratories."
)

_LLM_TEXT = (
    "In conclusion, it is important to note that as an AI language model, "
    "I don't have access to specific data. However, here is a comprehensive "
    "overview of the key factors to consider."
)


async def test_human_text_low_ai_probability(detector, source, llm_client):
    llm_client.set_logprob(-3.0)
    signal = await detector.analyze(source, _HUMAN_TEXT, raw_freshness=0.8)
    assert signal.ai_probability < 0.5


async def test_llm_text_high_ai_probability(detector, source, llm_client):
    llm_client.set_logprob(-0.5)
    signal = await detector.analyze(source, _LLM_TEXT, raw_freshness=0.8)
    assert signal.ai_probability > 0.5


async def test_effective_freshness_penalized(detector, source, llm_client):
    llm_client.set_logprob(-0.5)
    signal = await detector.analyze(source, _LLM_TEXT, raw_freshness=0.8)
    assert signal.effective_freshness < 0.8


async def test_human_effective_freshness_preserved(detector, source, llm_client):
    llm_client.set_logprob(-3.0)
    signal = await detector.analyze(source, _HUMAN_TEXT, raw_freshness=0.8)
    assert signal.effective_freshness > 0.5


async def test_ai_probability_in_range(detector, source, llm_client):
    llm_client.set_logprob(-1.0)
    signal = await detector.analyze(source, _HUMAN_TEXT, raw_freshness=0.5)
    assert 0.0 <= signal.ai_probability <= 1.0
    assert 0.0 <= signal.effective_freshness <= 1.0
