"""ScipyLogisticForecaster — spec 007 T093 (WS-C, FR-C02).

Clase concreta (sin Protocol — YAGNI). Ajusta curvas-S logisticas
sobre series temporales usando scipy.optimize.curve_fit.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

from vigilancia_multiagente.domain.evaluation_entities import SCurveProjection

logger = logging.getLogger(__name__)

try:
    from scipy.optimize import curve_fit

    _SCIPY_AVAILABLE = True
except ImportError:
    _SCIPY_AVAILABLE = False

    def curve_fit(*args, **kwargs):  # type: ignore[misc,no-untyped-def]
        raise RuntimeError("scipy not available")


def _logistic(t: np.ndarray, L: float, k: float, t0: float) -> np.ndarray:
    """Funcion logistica: L / (1 + exp(-k*(t - t0)))."""
    return L / (1.0 + np.exp(-k * (t - t0)))


@dataclass(slots=True)
class ScipyLogisticForecaster:
    """Sin Protocol — calculo puro con scipy/numpy.

    fit_s_curve: ajusta curva-S logistica a una serie temporal.
    detect_inflection: calcula el punto de inflexion a partir de una proyeccion.
    """

    def fit_s_curve(
        self,
        technology: str,
        domain: str,
        timeseries: list[tuple[int, int]],
    ) -> SCurveProjection:
        """Ajusta curva logistica a la serie temporal.

        Args:
            technology: Nombre de la tecnologia.
            domain: Dominio tecnologico.
            timeseries: Lista de (year, value) ordenada cronologicamente.

        Returns:
            SCurveProjection con los parametros ajustados.
        """
        if not _SCIPY_AVAILABLE:
            logger.warning("scipy not available, returning empty projection for %s", technology)
            return self._empty(technology, domain)

        if len(timeseries) < 4:
            logger.warning("Too few data points (%d) for curve fit on %s", len(timeseries), technology)
            return self._empty(technology, domain, samples=len(timeseries))

        sorted_ts = sorted(timeseries, key=lambda item: item[0])
        years = np.array([item[0] for item in sorted_ts], dtype=float)
        values = np.array([item[1] for item in sorted_ts], dtype=float)

        year_min = years.min()
        years_norm = years - year_min

        L0 = float(max(values)) * 1.2 or 100.0
        k0 = 0.5
        t0_0 = float(years_norm.mean())

        try:
            popt, _ = curve_fit(
                _logistic,
                years_norm,
                values,
                p0=[L0, k0, t0_0],
                bounds=(
                    [max(values) * 0.5, 0.001, 0.0],
                    [max(values) * 10.0, 5.0, float(years_norm.max()) + 20.0],
                ),
                maxfev=5000,
            )  # type: ignore[call-overload]
            L_fit, k_fit, t0_fit = popt
            predicted = _logistic(years_norm, L_fit, k_fit, t0_fit)
            ss_res = float(np.sum((values - predicted) ** 2))
            ss_tot = float(np.sum((values - np.mean(values)) ** 2))
            r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
            r_squared = max(0.0, min(1.0, r_squared))

            inflection_year = round(t0_fit + year_min)

            return SCurveProjection(
                technology=technology,
                domain=domain,
                growth_rate=round(float(k_fit), 4),
                inflection_year=inflection_year,
                ceiling=round(float(L_fit), 2),
                r_squared=round(r_squared, 4),
                samples_count=len(timeseries),
            )
        except Exception as exc:
            logger.warning("curve_fit failed for %s: %s", technology, exc)
            return self._empty(technology, domain, samples=len(timeseries))

    @staticmethod
    def detect_inflection(projection: SCurveProjection) -> int | None:
        """Retorna el ano de inflexion de la curva-S, o None si no es
        calculable (growth_rate muy bajo o negativo).
        """
        if projection.growth_rate <= 0.001:
            return None
        return projection.inflection_year

    @staticmethod
    def _empty(
        technology: str,
        domain: str,
        *,
        samples: int = 0,
    ) -> SCurveProjection:
        return SCurveProjection(
            technology=technology,
            domain=domain,
            growth_rate=0.0,
            inflection_year=0,
            ceiling=0.0,
            r_squared=0.0,
            samples_count=samples,
        )
