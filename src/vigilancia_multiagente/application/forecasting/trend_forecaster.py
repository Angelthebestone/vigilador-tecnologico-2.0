import asyncio
import json
import logging

from vigilancia_multiagente.domain.trend_projection import TrendProjection

logger = logging.getLogger(__name__)


class TrendForecasterService:
    """Proyección de tendencias con degradación en 3 niveles:

    1. Subproceso Python aislado (numpy en proceso separado, cwd/env acotado)
    2. numpy polinómico en el proceso actual (si el subproceso falla)
    3. regresión lineal pura sin numpy (último recurso)
    """

    def __init__(self) -> None:
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
        if result is None:
            result = self._project_polynomial_inproc(years, values)
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
        """Ejecuta la proyección polinómica en un subproceso Python aislado.

        El cálculo numpy corre en un proceso separado (``subprocess.run`` en
        un hilo, vía ``asyncio.to_thread``) con entorno y cwd acotados: aísla
        la ejecución de código numérico del proceso del backend. No usa el
        servidor MCP sandbox — su transporte STDIO cuelga en Windows con
        tareas lentas; el subproceso directo logra el mismo aislamiento y es
        portable. El script imprime el resultado como JSON en stdout.
        Devuelve None si algo falla — el caller cae a numpy en proceso.
        """
        import os
        import subprocess
        import sys
        import tempfile

        code = _SANDBOX_PROJECTION_TEMPLATE.format(
            years=json.dumps(years), values=json.dumps(values)
        )

        def _run() -> str | None:
            with tempfile.TemporaryDirectory(prefix="trend_") as tmpdir:
                script = os.path.join(tmpdir, "proj.py")
                with open(script, "w", encoding="utf-8") as f:
                    f.write(code)
                env = {"PATH": os.environ.get("PATH", ""), "HOME": tmpdir}
                for key in ("SYSTEMROOT", "SYSTEMDRIVE", "PATHEXT", "WINDIR", "TEMP", "TMP"):
                    val = os.environ.get(key)
                    if val:
                        env[key] = val
                proc = subprocess.run(
                    [sys.executable, "-u", script],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    env=env,
                    cwd=tmpdir,
                    check=False,
                )
                return proc.stdout if proc.returncode == 0 else None

        try:
            stdout = await asyncio.to_thread(_run)
        except (subprocess.TimeoutExpired, OSError) as exc:
            logger.warning("Sandbox projection failed, falling back: %s", exc)
            return None

        if not stdout:
            return None
        try:
            parsed = json.loads(stdout.strip())
        except (ValueError, TypeError):
            return None
        return parsed if isinstance(parsed, dict) and "projected" in parsed else None

    def _project_polynomial_inproc(self, years: list[int], values: list[float]) -> dict | None:
        """Proyección polinómica con numpy en el proceso actual.

        Fallback cuando el sandbox MCP no está disponible. Mismo cálculo que
        el sandbox pero sin aislamiento.
        """
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


# Script autocontenido ejecutado en el MCP sandbox aislado. Mismo cálculo
# polinómico que _project_polynomial_inproc; imprime el resultado como JSON
# en stdout (único canal de retorno del sandbox). {years}/{values} se
# inyectan como literales JSON (listas de números, no input arbitrario).
_SANDBOX_PROJECTION_TEMPLATE = """\
import json
import numpy as np

years = np.array({years}, dtype=float)
values = np.array({values}, dtype=float)

coeffs = np.polyfit(years, values, min(2, len(years) - 1))
poly = np.poly1d(coeffs)

future = np.arange(years[-1] + 1, years[-1] + 3, 0.25)
projected = poly(future)

out = {{
    "projected": [
        {{
            "period": f"{{int(y)}}-Q{{int((y % 1) * 4 + 1)}}",
            "value": round(float(v), 1),
            "lower_bound": round(float(v * 0.8), 1),
            "upper_bound": round(float(v * 1.2), 1),
        }}
        for y, v in zip(future, projected)
    ],
    "model": "polynomial",
}}

if len(coeffs) >= 3 and abs(coeffs[0]) > 0.001:
    infl = -coeffs[1] / (2 * coeffs[0])
    out["inflections"] = [{{"period": str(infl), "type": "inflection"}}]
else:
    out["inflections"] = []

print(json.dumps(out))
"""
