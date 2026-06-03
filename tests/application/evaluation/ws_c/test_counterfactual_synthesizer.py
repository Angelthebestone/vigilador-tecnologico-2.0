"""Tests LlmCounterfactualSynthesizer — spec 007 T108.

Genera >= 3 escenarios.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from vigilancia_multiagente.application.evaluation.ws_c.llm_counterfactual_synthesizer import (
    LlmCounterfactualSynthesizer,
)
from vigilancia_multiagente.domain.models import FinalReport


class DummyResponse:
    def __init__(self, content: str) -> None:
        self.content = content


class DummyLLM:
    def __init__(self, content: str) -> None:
        self.content = content

    async def complete(self, messages):
        del messages
        return DummyResponse(self.content)


class DummyPromptLoader:
    def load(self, path: str) -> str:
        assert path.startswith("evaluation/counterfactual")
        return "counterfactual prompt"


def _report() -> FinalReport:
    return FinalReport(
        session_id=uuid4(),
        executive_summary="AI technology impact assessment",
        markdown="AI is transforming healthcare and finance.",
    )


@pytest.mark.asyncio
async def test_generates_three_scenarios() -> None:
    """Genera 3 escenarios contrafactuales."""
    llm = DummyLLM(
        '[{"question": "What if regulation changes?", "probability": 0.6,'
        ' "impact_summary": "Stricter rules would slow adoption"},'
        '{"question": "What if funding stops?", "probability": 0.3,'
        ' "impact_summary": "Development would stall"},'
        '{"question": "What if competitor enters?", "probability": 0.7,'
        ' "impact_summary": "Market would fragment"}]'
    )
    synthesizer = LlmCounterfactualSynthesizer(llm, DummyPromptLoader())

    scenarios = await synthesizer.synthesize(_report(), scenarios_n=3)

    assert len(scenarios) == 3
    for sc in scenarios:
        assert sc.question
        assert 0 <= sc.probability <= 1
        assert sc.impact_summary


@pytest.mark.asyncio
async def test_scenarios_n_parameter() -> None:
    """scenarios_n=1 devuelve solo 1 escenario."""
    llm = DummyLLM(
        '[{"question": "What if X?", "probability": 0.5, "impact_summary": "ImpactX"},'
        '{"question": "What if Y?", "probability": 0.4, "impact_summary": "ImpactY"}]'
    )
    synthesizer = LlmCounterfactualSynthesizer(llm, DummyPromptLoader())

    scenarios = await synthesizer.synthesize(_report(), scenarios_n=1)

    assert len(scenarios) == 1


@pytest.mark.asyncio
async def test_llm_failure_returns_empty() -> None:
    """Fallo de LLM -> lista vacia + StepError."""
    class FailingLLM:
        async def complete(self, messages):
            raise RuntimeError("LLM down")

    errors: list = []
    synthesizer = LlmCounterfactualSynthesizer(FailingLLM(), DummyPromptLoader(), errors_sink=errors)

    scenarios = await synthesizer.synthesize(_report())

    assert scenarios == []
    assert len(errors) == 1


@pytest.mark.asyncio
async def test_default_scenarios_n() -> None:
    """Usa scenarios_n del constructor (default 3)."""
    llm = DummyLLM(
        '[{"question": "Q1", "probability": 0.5, "impact_summary": "I1"},'
        '{"question": "Q2", "probability": 0.5, "impact_summary": "I2"},'
        '{"question": "Q3", "probability": 0.5, "impact_summary": "I3"},'
        '{"question": "Q4", "probability": 0.5, "impact_summary": "I4"}]'
    )
    synthesizer = LlmCounterfactualSynthesizer(llm, DummyPromptLoader(), scenarios_n=2)

    scenarios = await synthesizer.synthesize(_report())

    assert len(scenarios) == 2
