"""Tests DerSimonianLairdMetaAnalyzer — spec 007 T106.

5 estudios sinteticos, valida i_squared y consensus_value.
"""

from __future__ import annotations

import pytest

from vigilancia_multiagente.application.evaluation.analytics.dersimonian_laird_meta import (
    DerSimonianLairdMetaAnalyzer,
)


@pytest.fixture
def analyzer() -> DerSimonianLairdMetaAnalyzer:
    return DerSimonianLairdMetaAnalyzer()


@pytest.mark.asyncio
async def test_aggregate_five_studies(analyzer: DerSimonianLairdMetaAnalyzer) -> None:
    """5 estudios con efecto consistente -> I^2 bajo, consensus cercano a la media."""
    studies = [
        {"label": "study_A", "effect_size": 0.45, "variance": 0.02},
        {"label": "study_B", "effect_size": 0.52, "variance": 0.03},
        {"label": "study_C", "effect_size": 0.48, "variance": 0.025},
        {"label": "study_D", "effect_size": 0.55, "variance": 0.04},
        {"label": "study_E", "effect_size": 0.50, "variance": 0.02},
    ]

    result = await analyzer.aggregate("drug_effect", studies)

    assert result.topic == "drug_effect"
    assert result.studies_count == 5
    assert 0.45 <= result.consensus_value <= 0.55
    assert 0 <= result.i_squared <= 1.0
    assert 0 <= result.q_test_pvalue <= 1.0
    assert len(result.effect_size_range) == 2
    assert result.effect_size_range[0] <= result.effect_size_range[1]


@pytest.mark.asyncio
async def test_aggregate_heterogeneous(analyzer: DerSimonianLairdMetaAnalyzer) -> None:
    """Estudios muy dispares -> I^2 alto, outliers identificados."""
    studies = [
        {"label": "study_A", "effect_size": 0.10, "variance": 0.01},
        {"label": "study_B", "effect_size": 0.85, "variance": 0.01},
        {"label": "study_C", "effect_size": 0.12, "variance": 0.01},
        {"label": "study_D", "effect_size": 0.88, "variance": 0.01},
        {"label": "study_E", "effect_size": 0.11, "variance": 0.01},
    ]

    result = await analyzer.aggregate("mixed_effect", studies)

    assert result.i_squared > 0.5
    assert len(result.outliers) >= 1


@pytest.mark.asyncio
async def test_aggregate_single_study(analyzer: DerSimonianLairdMetaAnalyzer) -> None:
    """Un solo estudio -> resultado minimo."""
    studies = [{"label": "only_study", "effect_size": 0.5, "variance": 0.1}]

    result = await analyzer.aggregate("lonely_topic", studies)

    assert result.studies_count == 1
    assert result.i_squared == 0.0
    assert result.q_test_pvalue == 1.0


@pytest.mark.asyncio
async def test_aggregate_empty(analyzer: DerSimonianLairdMetaAnalyzer) -> None:
    """Sin estudios -> todo cero."""
    result = await analyzer.aggregate("empty", [])

    assert result.studies_count == 0
    assert result.i_squared == 0.0
    assert result.q_test_pvalue == 1.0


@pytest.mark.asyncio
async def test_aggregate_with_n_instead_of_variance(
    analyzer: DerSimonianLairdMetaAnalyzer,
) -> None:
    """Usa n para estimar variance si no se provee."""
    studies = [
        {"label": "A", "effect_size": 0.5, "n": 100},
        {"label": "B", "effect_size": 0.6, "n": 80},
        {"label": "C", "effect_size": 0.55, "n": 120},
    ]

    result = await analyzer.aggregate("test", studies)

    assert result.studies_count == 3
    assert result.consensus_value > 0
