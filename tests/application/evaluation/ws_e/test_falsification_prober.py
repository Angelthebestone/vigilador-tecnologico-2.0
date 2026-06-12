from __future__ import annotations

import pytest

from vigilancia_multiagente.application.evaluation.ws_e.llm_falsification_prober import (
    LlmFalsificationProber,
)


class DummyPromptLoader:
    def load(self, path: str) -> str:
        assert path.startswith("evaluation/falsification")
        return "prompt"


class DummyResponse:
    def __init__(self, content: str) -> None:
        self.content = content


class DummyLLM:
    def __init__(self, content: str) -> None:
        self.content = content

    async def complete(self, messages):
        del messages
        return DummyResponse(self.content)


@pytest.mark.asyncio
async def test_falsification_prober_returns_empty_list_when_llm_returns_no_scenarios() -> None:
    prober = LlmFalsificationProber(DummyLLM("[]"), DummyPromptLoader())

    scenarios = await prober.probe("sample conclusion")

    assert scenarios == []


@pytest.mark.asyncio
async def test_falsification_prober_marks_scenarios_as_falsifiable() -> None:
    prober = LlmFalsificationProber(
        DummyLLM(
            '[{"hypothetical_evidence": "contradictory replicated evidence", "plausibility": 0.8}]'
        ),
        DummyPromptLoader(),
    )

    scenarios = await prober.probe("sample conclusion")

    assert len(scenarios) == 1
    assert scenarios[0].falsifiable is True
    assert scenarios[0].hypothetical_evidence == "contradictory replicated evidence"
