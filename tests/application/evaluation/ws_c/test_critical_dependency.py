"""Tests LlmCriticalDependencyMapper — spec 007 T109.

3 tecnologias con dependencias conocidas.
"""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from vigilancia_multiagente.application.evaluation.ws_c.llm_critical_dependency_mapper import (
    LlmCriticalDependencyMapper,
)
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


@pytest.fixture
def mock_graph_service():
    return MagicMock()


def _finding(topic: str, text: str) -> Finding:
    return Finding(
        id=uuid4(),
        topic=topic,
        statement=text,
        confidence=0.8,
        source_ids=[],
    )


@pytest.mark.asyncio
async def test_maps_dependencies_for_ai_chip(mock_graph_service) -> None:
    """Tecnologia AI chip -> dependencias de materiales y librerias."""
    llm = DummyLLM(
        '[{"name": "Rare earth minerals", "dependency_kind": "material", "risk_level": "high"},'
        '{"name": "CUDA", "dependency_kind": "library", "risk_level": "medium"},'
        '{"name": "TSMC fab capacity", "dependency_kind": "vendor", "risk_level": "high"}]'
    )
    mapper = LlmCriticalDependencyMapper(llm, mock_graph_service)
    findings = [_finding("AI Chip", "Next-gen AI accelerators need advanced fabrication")]

    deps = await mapper.map("AI Chip", findings)

    assert len(deps) >= 3
    assert any(d.dependency_kind.value == "material" for d in deps)
    assert any(d.dependency_kind.value == "library" for d in deps)
    assert any(d.dependency_kind.value == "vendor" for d in deps)


@pytest.mark.asyncio
async def test_maps_dependencies_for_quantum(mock_graph_service) -> None:
    """Tecnologia quantum computing -> dependencias de regulacion y materiales."""
    llm = DummyLLM(
        '[{"name": "Cryogenic cooling", "dependency_kind": "material", "risk_level": "high"},'
        '{"name": "Export controls", "dependency_kind": "regulation", "risk_level": "medium"}]'
    )
    mapper = LlmCriticalDependencyMapper(llm, mock_graph_service)
    findings = [_finding("Quantum", "Quantum computing requires extreme cooling")]

    deps = await mapper.map("Quantum Computing", findings)

    assert len(deps) >= 2
    assert any(d.dependency_kind.value == "regulation" for d in deps)


@pytest.mark.asyncio
async def test_returns_empty_on_llm_failure(mock_graph_service) -> None:
    """Fallo de LLM -> lista vacia + StepError."""

    class FailingLLM:
        async def complete(self, messages):
            raise RuntimeError("LLM error")

    errors: list = []
    mapper = LlmCriticalDependencyMapper(FailingLLM(), mock_graph_service, errors_sink=errors)
    findings = [_finding("Test", "Test statement")]

    deps = await mapper.map("Test", findings)

    assert deps == []
    assert len(errors) == 1
    assert errors[0].workstream.value == "WS-C"
