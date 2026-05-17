import logging

from vigilancia_multiagente.domain.trend_projection import TrendProjection

logger = logging.getLogger(__name__)


class TrendForecasterService:
    def __init__(self):
        pass

    async def analyze(self, session_data: dict) -> list[TrendProjection]:
        series = self._extract_time_series(session_data)
        projections = []
        for s in series:
            projection = await self._compute_projection(s)
            projections.append(projection)
        return projections

    def _extract_time_series(self, data: dict) -> list[dict]:
        series = []
        findings = data.get("findings", [])
        for f in findings:
            content = f.get("content", "")
            years_values = self._parse_yearly_data(content)
            if years_values and len(years_values) >= 2:
                series.append(
                    {
                        "years": [y for y, v in years_values],
                        "values": [v for y, v in years_values],
                        "metric": f.get("title", "unknown"),
                        "source": f.get("source", "unknown"),
                    }
                )
        return series

    def _parse_yearly_data(self, text: str) -> list[tuple[int, float]]:
        import re

        patterns = [
            r"(\d{4})\s*:?\s*(\d+(?:\.\d+)?)",
            r"(\d{4})\s*\((\d+(?:\.\d+)?)\)",
        ]
        results = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for year, val in matches:
                y = int(year)
                v = float(val)
                if 1990 <= y <= 2030:
                    results.append((y, v))
        seen = {}
        for y, v in results:
            seen[y] = v
        return sorted(seen.items())

    async def _compute_projection(self, series: dict) -> TrendProjection:
        years = series["years"]
        values = series["values"]
        n = len(values)

        if n < 3:
            return TrendProjection(
                source_data=series,
                data_quality="insufficient",
            )

        data_quality = "low" if n == 3 else "sufficient"

        result = await self._project_via_sandbox(years, values)
        if result:
            return TrendProjection(
                source_data=series,
                projected_values=result["projected"],
                model_type=result.get("model", "polynomial"),
                data_quality=data_quality,
                inflection_points=result.get("inflections", []),
            )

        return self._simple_linear_projection(years, values, series, data_quality)

    async def _project_via_sandbox(self, years: list[int], values: list[float]) -> dict | None:
        """Compute polynomial projection using numpy directly."""
        try:
            import numpy as np

            years_arr = np.array(years, dtype=float)
            values_arr = np.array(values, dtype=float)

            coeffs = np.polyfit(years_arr, values_arr, min(2, len(years) - 1))
            poly = np.poly1d(coeffs)

            future_years = np.arange(years[-1] + 1, years[-1] + 3, 0.25)
            projected = poly(future_years)

            result = {
                "projected": [
                    {
                        "period": f"{int(y)}-Q{int((y % 1) * 4 + 1)}",
                        "value": round(float(v), 1),
                        "lower_bound": round(float(v * 0.8), 1),
                        "upper_bound": round(float(v * 1.2), 1),
                    }
                    for y, v in zip(future_years, projected, strict=True)
                ],
                "model": "polynomial",
            }

            if len(coeffs) >= 3 and abs(coeffs[0]) > 0.001:
                inflection_year = -coeffs[1] / (2 * coeffs[0])
                result["inflections"] = [{"period": str(inflection_year), "type": "inflection"}]
            else:
                result["inflections"] = []

            return result
        except Exception:
            return None

    def _simple_linear_projection(self, years, values, series, data_quality) -> TrendProjection:
        n = len(years)
        x_mean = sum(years) / n
        y_mean = sum(values) / n

        num = sum((y - x_mean) * (v - y_mean) for y, v in zip(years, values, strict=True))
        den = sum((y - x_mean) ** 2 for y in years)
        slope = num / den if den != 0 else 0
        intercept = y_mean - slope * x_mean

        future_years = list(range(years[-1] + 1, years[-1] + 3))
        projected = []
        for y in future_years:
            v = slope * y + intercept
            projected.append(
                {
                    "period": str(y),
                    "value": round(max(0, v), 1),
                    "lower_bound": round(max(0, v * 0.8), 1),
                    "upper_bound": round(v * 1.2, 1),
                }
            )

        return TrendProjection(
            source_data=series,
            projected_values=projected,
            model_type="linear",
            data_quality=data_quality,
        )
