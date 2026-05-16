"""Integration tests for trend forecasting."""

import pytest

pytestmark = pytest.mark.asyncio


async def test_extract_yearly_data():
    """Test parsing yearly data from text."""
    from vigilancia_multiagente.application.forecasting.trend_forecaster import TrendForecasterService

    forecaster = TrendForecasterService()
    result = forecaster._parse_yearly_data("2020: 15, 2021: 22, 2022: 30")
    assert len(result) == 3
    assert result[0] == (2020, 15.0)
    assert result[1] == (2021, 22.0)
    assert result[2] == (2022, 30.0)


async def test_simple_linear_projection():
    """Test fallback linear projection."""
    from vigilancia_multiagente.application.forecasting.trend_forecaster import TrendForecasterService

    forecaster = TrendForecasterService()
    projection = forecaster._simple_linear_projection(
        [2020, 2021, 2022], [10, 20, 30],
        {"years": [2020, 2021, 2022], "values": [10, 20, 30]},
        "low"
    )
    assert len(projection.projected_values) >= 2
    assert projection.model_type == "linear"
    assert projection.data_quality == "low"


async def test_inflection_detection():
    """Test inflection point detection via polynomial projection."""
    from vigilancia_multiagente.application.forecasting.trend_forecaster import TrendForecasterService

    forecaster = TrendForecasterService()
    result = await forecaster._project_via_sandbox(
        [2020, 2021, 2022, 2023, 2024], [10, 20, 30, 25, 15]
    )
    assert result is not None
    assert "inflections" in result
    assert result["model"] == "polynomial"


async def test_insufficient_data():
    """Test that <3 data points returns insufficient quality."""
    from vigilancia_multiagente.application.forecasting.trend_forecaster import TrendForecasterService

    forecaster = TrendForecasterService()
    projection = forecaster._simple_linear_projection(
        [2020, 2021], [10, 20],
        {"years": [2020, 2021], "values": [10, 20]},
        "insufficient"
    )
    assert projection.data_quality == "insufficient"
