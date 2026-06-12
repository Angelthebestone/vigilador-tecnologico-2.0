"""Golden test for WS-C Deep Analysis — spec 007 T111.

Golden case 'alphafold-baseline' valida curva-S y meta-analisis.
"""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

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
from vigilancia_multiagente.domain.models import FinalReport, Finding


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
        return "prompt template"


def _alphafold_finding() -> Finding:
    return Finding(
        id=uuid4(),
        topic="AlphaFold",
        statement="AlphaFold achieved high accuracy structure prediction for proteins",
        confidence=0.85,
        source_ids=[],
        tags=["AI", "BIO", "protein"],
    )


@pytest.mark.asyncio
async def test_alphafold_s_curve_projection() -> None:
    """Curva-S para AlphaFold: R^2 >= 0.8, growth_rate > 0."""
    forecaster = ScipyLogisticForecaster()
    timeseries = [
        (2016, 1),
        (2017, 2),
        (2018, 5),
        (2019, 12),
        (2020, 30),
        (2021, 65),
        (2022, 100),
        (2023, 130),
        (2024, 145),
        (2025, 152),
        (2026, 155),
    ]

    proj = forecaster.fit_s_curve("AlphaFold", "BIO", timeseries)

    assert proj.technology == "AlphaFold"
    assert proj.domain == "BIO"
    assert proj.r_squared >= 0.8
    assert proj.growth_rate > 0
    assert proj.inflection_year > 0
    assert proj.samples_count == 11


@pytest.mark.asyncio
async def test_alphafold_meta_analysis() -> None:
    """Meta-analisis de estudios sobre AlphaFold."""
    analyzer = DerSimonianLairdMetaAnalyzer()
    studies = [
        {"label": "CASP14", "effect_size": 0.92, "variance": 0.01},
        {"label": "CASP15", "effect_size": 0.88, "variance": 0.015},
        {"label": "Independent_validation", "effect_size": 0.85, "variance": 0.02},
        {"label": "Benchmark_A", "effect_size": 0.90, "variance": 0.01},
        {"label": "Benchmark_B", "effect_size": 0.87, "variance": 0.025},
    ]

    result = await analyzer.aggregate("alphafold_structure_prediction", studies)

    assert result.topic == "alphafold_structure_prediction"
    assert result.studies_count == 5
    assert result.consensus_value >= 0.8
    assert 0 <= result.i_squared <= 1.0


@pytest.mark.asyncio
async def test_alphafold_assumptions() -> None:
    """Deteccion de asunciones para AlphaFold."""
    llm = DummyLLM(
        '[{"text": "assumes high-quality PDB templates", "severity": "warning",'
        ' "affects_confidence": -0.15},'
        '{"text": "assumes single-domain protein structure", "severity": "info",'
        ' "affects_confidence": -0.05}]'
    )
    detector = LlmAssumptionDetector(llm, DummyPromptLoader())

    assumptions = await detector.detect(
        _alphafold_finding(),
        "AlphaFold uses deep learning for protein structure prediction",
    )

    assert len(assumptions) >= 2
    for a in assumptions:
        assert a.text
        assert isinstance(a.affects_confidence, float)


@pytest.mark.asyncio
async def test_alphafold_counterfactuals() -> None:
    """Escenarios contrafactuales."""
    llm = DummyLLM(
        '[{"question": "What if PDB data becomes unavailable?", "probability": 0.3,'
        ' "impact_summary": "Retraining would require synthetic data"},'
        '{"question": "What if compute cost rises 10x?", "probability": 0.5,'
        ' "impact_summary": "Access would be limited to large labs"}]'
    )
    synthesizer = LlmCounterfactualSynthesizer(llm, DummyPromptLoader())

    report = FinalReport(session_id=uuid4(), executive_summary="AlphaFold impact assessment")
    scenarios = await synthesizer.synthesize(report, scenarios_n=2)

    assert len(scenarios) == 2
    for s in scenarios:
        assert s.question
        assert 0 <= s.probability <= 1


@pytest.mark.asyncio
async def test_alphafold_dependencies() -> None:
    """Dependencias criticas de AlphaFold."""
    findings = [_alphafold_finding()]
    mapper = LlmCriticalDependencyMapper(
        DummyLLM(
            '[{"name": "PDB database", "dependency_kind": "vendor", "risk_level": "high"},'
            '{"name": "TPU availability", "dependency_kind": "vendor", "risk_level": "medium"}]'
        ),
        MagicMock(),
    )

    deps = await mapper.map("AlphaFold", findings)

    assert len(deps) >= 2
    assert any("PDB" in d.name for d in deps)
    assert any("TPU" in d.name for d in deps)
