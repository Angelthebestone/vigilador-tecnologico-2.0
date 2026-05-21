"""Tests LlmAssumptionDetector — spec 007 T107.

4 textos con asunciones explicitas vs implicitas.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from vigilancia_multiagente.application.evaluation.ws_c.llm_assumption_detector import (
    LlmAssumptionDetector,
)
from vigilancia_multiagente.domain.evaluation_entities import AssumptionSeverity
from vigilancia_multiagente.domain.models import Finding


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
        assert path == "evaluation/assumption_detection.txt"
        return "Detecta asunciones implicitas."


def _finding(text: str) -> Finding:
    return Finding(
        id=uuid4(),
        topic="test",
        statement=text,
        confidence=0.8,
        source_ids=[],
    )


@pytest.mark.asyncio
async def test_detects_explicit_assumptions() -> None:
    """Texto con asuncion explicita -> detectada."""
    llm = DummyLLM(
        '[{"text": "assumes linear growth", "severity": "warning", "affects_confidence": -0.2}]'
    )
    detector = LlmAssumptionDetector(llm, DummyPromptLoader())

    assumptions = await detector.detect(_finding("assuming linear growth"), "source text")

    assert len(assumptions) == 1
    assert assumptions[0].text == "assumes linear growth"
    assert assumptions[0].severity == AssumptionSeverity.WARNING
    assert assumptions[0].affects_confidence == -0.2


@pytest.mark.asyncio
async def test_detects_multiple_assumptions() -> None:
    """Multiples asunciones en un texto."""
    llm = DummyLLM(
        '[{"text": "laboratory conditions", "severity": "info", "affects_confidence": -0.05},'
        '{"text": "small sample size", "severity": "critical", "affects_confidence": -0.5}]'
    )
    detector = LlmAssumptionDetector(llm, DummyPromptLoader())

    assumptions = await detector.detect(_finding("under lab conditions"), "sample text")

    assert len(assumptions) == 2


@pytest.mark.asyncio
async def test_no_assumptions_detected() -> None:
    """LLM devuelve lista vacia -> sin asunciones."""
    llm = DummyLLM("[]")
    detector = LlmAssumptionDetector(llm, DummyPromptLoader())

    assumptions = await detector.detect(_finding("no assumptions"), "clean source")

    assert assumptions == []


@pytest.mark.asyncio
async def test_llm_failure_returns_empty_list() -> None:
    """Fallo de LLM -> StepError + lista vacia."""
    class FailingLLM:
        async def complete(self, messages):
            raise RuntimeError("LLM timeout")

    errors: list = []
    detector = LlmAssumptionDetector(FailingLLM(), DummyPromptLoader(), errors_sink=errors)

    assumptions = await detector.detect(_finding("any"), "any")

    assert assumptions == []
    assert len(errors) == 1
    assert errors[0].workstream.value == "WS-C"


@pytest.mark.asyncio
async def test_missing_prompt_file() -> None:
    """Prompt file faltante -> lista vacia."""
    class MissingPromptLoader:
        def load(self, path: str) -> str:
            raise FileNotFoundError(f"{path} not found")

    detector = LlmAssumptionDetector(DummyLLM("[]"), MissingPromptLoader())

    assumptions = await detector.detect(_finding("test"), "source")

    assert assumptions == []
