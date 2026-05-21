"""Tests ScipyLogisticForecaster — spec 007 T105.

3 dominios con series sinteticas, R^2 >= 0.8.
"""

from __future__ import annotations

import pytest

from vigilancia_multiagente.application.evaluation.analytics.scipy_logistic_forecaster import (
    ScipyLogisticForecaster,
)


def _make_timeseries(start: int, values: list[int]) -> list[tuple[int, int]]:
    return [(start + i, v) for i, v in enumerate(values)]


@pytest.fixture
def forecaster() -> ScipyLogisticForecaster:
    return ScipyLogisticForecaster()


@pytest.mark.asyncio
async def test_fit_ai_domain(forecaster: ScipyLogisticForecaster) -> None:
    """Curva-S para dominio AI con crecimiento logistico."""
    ts = _make_timeseries(2015, [1, 2, 3, 5, 8, 15, 28, 50, 70, 85, 95, 100])
    proj = forecaster.fit_s_curve("Transformers", "AI", ts)

    assert proj.technology == "Transformers"
    assert proj.domain == "AI"
    assert proj.r_squared >= 0.8
    assert proj.samples_count == 12
    assert proj.growth_rate > 0
    assert proj.inflection_year > 0


@pytest.mark.asyncio
async def test_fit_bio_domain(forecaster: ScipyLogisticForecaster) -> None:
    """Curva-S para dominio BIO."""
    ts = _make_timeseries(2010, [1, 1, 2, 3, 4, 6, 10, 18, 30, 50, 72, 88, 96, 99])
    proj = forecaster.fit_s_curve("CRISPR", "BIO", ts)

    assert proj.domain == "BIO"
    assert proj.r_squared >= 0.8
    assert proj.samples_count == 14


@pytest.mark.asyncio
async def test_fit_energy_domain(forecaster: ScipyLogisticForecaster) -> None:
    """Curva-S para dominio ENERGY."""
    ts = _make_timeseries(2000, [1, 2, 3, 5, 7, 10, 15, 22, 30, 38, 45, 52])
    proj = forecaster.fit_s_curve("Solar Cells", "ENERGY", ts)

    assert proj.domain == "ENERGY"
    assert proj.r_squared >= 0.8
    assert proj.samples_count == 12


@pytest.mark.asyncio
async def test_fit_insufficient_data(forecaster: ScipyLogisticForecaster) -> None:
    """Menos de 4 puntos -> proyeccion vacia."""
    ts = [ (2020, 1), (2021, 2), (2022, 3) ]
    proj = forecaster.fit_s_curve("WeakSignal", "AI", ts)

    assert proj.samples_count == 3
    assert proj.r_squared == 0.0
    assert proj.growth_rate == 0.0


@pytest.mark.asyncio
async def test_detect_inflection(forecaster: ScipyLogisticForecaster) -> None:
    """Detecta punto de inflexion en curva creciente."""
    ts = _make_timeseries(2015, [1, 2, 4, 8, 16, 32, 64, 80, 90, 95])
    proj = forecaster.fit_s_curve("GrowthTech", "AI", ts)
    inflection = forecaster.detect_inflection(proj)

    assert inflection is not None
    assert inflection > 0


@pytest.mark.asyncio
async def test_detect_inflection_flat(forecaster: ScipyLogisticForecaster) -> None:
    """Growth_rate muy bajo -> None."""
    from vigilancia_multiagente.domain.evaluation_entities import SCurveProjection

    proj = SCurveProjection(
        technology="Flat", domain="general", growth_rate=0.0,
        inflection_year=0, ceiling=0.0, r_squared=0.0, samples_count=0,
    )
    inflection = forecaster.detect_inflection(proj)

    assert inflection is None
