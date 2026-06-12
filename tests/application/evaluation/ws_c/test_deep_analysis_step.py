"""Tests DeepAnalysisStep — spec 007 T110.

Integracion del step completo con servicios mockeados.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from vigilancia_multiagente.application.agents.pipeline.deep_analysis_step import (
    DeepAnalysisStep,
)
from vigilancia_multiagente.application.agents.pipeline.tool_loop_step import ToolLoopContext
from vigilancia_multiagente.application.evaluation.analytics.dersimonian_laird_meta import (
    DerSimonianLairdMetaAnalyzer,
)
from vigilancia_multiagente.application.evaluation.analytics.scipy_logistic_forecaster import (
    ScipyLogisticForecaster,
)
from vigilancia_multiagente.application.evaluation.ws_c.llm_assumption_detector import (
    LlmAssumptionDetector,
)
from vigilancia_multiagente.application.evaluation.ws_c.llm_counterfactual_synthesizer import (
    LlmCounterfactualSynthesizer,
)
from vigilancia_multiagente.application.evaluation.ws_c.llm_critical_dependency_mapper import (
    LlmCriticalDependencyMapper,
)
from vigilancia_multiagente.domain.models import BranchType, Finding, SourceRef


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
        return "prompt"


@pytest.fixture
def forecaster() -> ScipyLogisticForecaster:
    return ScipyLogisticForecaster()


@pytest.fixture
def meta_analyzer() -> DerSimonianLairdMetaAnalyzer:
    return DerSimonianLairdMetaAnalyzer()


@pytest.fixture
def assumption_detector() -> LlmAssumptionDetector:
    llm = DummyLLM(
        '[{"text": "assumes linear growth", "severity": "warning", "affects_confidence": -0.2}]'
    )
    return LlmAssumptionDetector(llm, DummyPromptLoader())


@pytest.fixture
def dependency_mapper() -> LlmCriticalDependencyMapper:
    llm = DummyLLM(
        '[{"name": "Rare minerals", "dependency_kind": "material", "risk_level": "high"}]'
    )
    return LlmCriticalDependencyMapper(llm, MagicMock())


@pytest.fixture
def counterfactual() -> LlmCounterfactualSynthesizer:
    llm = DummyLLM(
        '[{"question": "What if regulation tightens?", "probability": 0.6,'
        ' "impact_summary": "Slower adoption"}]'
    )
    return LlmCounterfactualSynthesizer(llm, DummyPromptLoader())


def _source() -> SourceRef:
    return SourceRef(
        id=uuid4(),
        session_id=uuid4(),
        url="https://example.com/paper",
        provider="arxiv",
        branch_type=BranchType.AVANCES,
        accessed_at=datetime.now(),
    )


def _finding() -> Finding:
    return Finding(
        id=uuid4(),
        topic="AI Training",
        statement="Neural network training requires significant compute",
        confidence=0.8,
        source_ids=[],
        tags=["AI", "compute"],
    )


class MockIteration:
    def __init__(self, findings: list, sources: list):
        self.findings = findings
        self.sources = sources


@pytest.mark.asyncio
async def test_deep_analysis_step_full_pipeline(
    forecaster,
    meta_analyzer,
    assumption_detector,
    dependency_mapper,
    counterfactual,
) -> None:
    """Step completo produce anotaciones, proyecciones y meta-analisis."""
    finding = _finding()
    source = _source()
    iteration = MockIteration(findings=[finding], sources=[source])

    session = AsyncMock()
    session.id = uuid4()
    session.user_query = "AI training"

    ctx = ToolLoopContext(
        session=session,
        branch_config=AsyncMock(),
        policy=AsyncMock(),
        branch_overlay=AsyncMock(),
        iterations=[iteration],
        executions=["exec1"],
    )
    ctx.errors = []

    step = DeepAnalysisStep(
        forecaster=forecaster,
        meta_analyzer=meta_analyzer,
        assumption_detector=assumption_detector,
        dependency_mapper=dependency_mapper,
        counterfactual_synthesizer=counterfactual,
    )

    result = await step.run(ctx)

    assert result.deep_analysis_annotations is not None
    assert len(result.deep_analysis_annotations) == 1
    ann = result.deep_analysis_annotations[0]
    assert len(ann.implicit_assumptions) >= 1
    assert len(ann.critical_dependencies) >= 1

    assert result.deep_analysis_projections is not None
    assert len(result.deep_analysis_projections) >= 1

    assert result.deep_analysis_meta_result is not None

    assert result.deep_analysis_counterfactuals is not None
    assert len(result.deep_analysis_counterfactuals) >= 1


@pytest.mark.asyncio
async def test_deep_analysis_step_no_services() -> None:
    """Sin servicios -> no falla, contexto vacio."""
    finding = _finding()
    iteration = MockIteration(findings=[finding], sources=[])

    session = AsyncMock()
    session.id = uuid4()
    session.user_query = "test"

    ctx = ToolLoopContext(
        session=session,
        branch_config=AsyncMock(),
        policy=AsyncMock(),
        branch_overlay=AsyncMock(),
        iterations=[iteration],
        executions=["exec1"],
    )
    ctx.errors = []

    step = DeepAnalysisStep()

    result = await step.run(ctx)

    assert result.deep_analysis_annotations is not None
    assert result.deep_analysis_projections == []
    assert result.deep_analysis_meta_result is None
    assert result.deep_analysis_counterfactuals == []


@pytest.mark.asyncio
async def test_deep_analysis_step_no_executions() -> None:
    """Sin ejecuciones -> retorna contexto intacto."""
    session = AsyncMock()
    session.id = uuid4()

    ctx = ToolLoopContext(
        session=session,
        branch_config=AsyncMock(),
        policy=AsyncMock(),
        branch_overlay=AsyncMock(),
        iterations=[],
        executions=[],
    )
    ctx.errors = []

    step = DeepAnalysisStep(
        forecaster=ScipyLogisticForecaster(),
        meta_analyzer=DerSimonianLairdMetaAnalyzer(),
    )

    result = await step.run(ctx)

    assert result.deep_analysis_annotations is None
