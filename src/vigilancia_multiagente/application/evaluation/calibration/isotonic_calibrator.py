"""IsotonicConfidenceCalibrator — spec 007 T022 (WS-E).

Reemplaza el `ConfidenceCalibrator` legacy (`buckets_fijos + actual_rate /
mean_predicted`) por una regresion isotonica empirica sobre golden case
runs. Persiste curvas via `CalibrationCurveRepository`.

Vive como clase concreta (sin Protocol) por YAGNI: unica implementacion
plausible, calculo puro sin frontera externa.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Protocol
from uuid import uuid4

import numpy as np
from sklearn.isotonic import IsotonicRegression

from vigilancia_multiagente.domain.evaluation_entities import (
    CalibrationCurve,
    GoldenCaseRun,
)


class CalibrationCurveStore(Protocol):
    """Puerto privado del calibrator. Vive aqui en vez de domain/ports porque
    es un detalle interno de WS-E y no se reusa fuera de este modulo (YAGNI)."""

    async def save(self, curve: CalibrationCurve) -> None: ...

    async def active(self) -> CalibrationCurve | None: ...

    async def activate(self, model_version: str) -> None: ...


_MIN_SAMPLES_FOR_FIT = 5
_GRID_POINTS = 11  # 0.0, 0.1, ..., 1.0


class IsotonicConfidenceCalibrator:
    """Curva isotonica empirica que reemplaza heuristicas de calibracion.

    - `calibrate(raw)`: aplica la curva activa. Si no hay curva todavia
      (samples < 5), retorna `raw` sin cambios (curva identidad).
    - `retrain(runs)`: ajusta una nueva curva con los runs historicos,
      persistida pero no activada automaticamente — el operador decide
      via `repository.activate()`.
    """

    def __init__(
        self,
        curve_repository: CalibrationCurveStore,
    ) -> None:
        self._repository = curve_repository
        self._cached: CalibrationCurve | None = None

    async def calibrate(self, raw_score: float) -> float:
        curve = await self._load_active()
        if curve is None or len(curve.mappings) < 2:
            return float(np.clip(raw_score, 0.0, 1.0))
        xs = np.array([m[0] for m in curve.mappings])
        ys = np.array([m[1] for m in curve.mappings])
        return float(np.clip(np.interp(raw_score, xs, ys), 0.0, 1.0))

    async def retrain(self, runs: list[GoldenCaseRun]) -> CalibrationCurve:
        if len(runs) < _MIN_SAMPLES_FOR_FIT:
            raise ValueError(
                f"need >= {_MIN_SAMPLES_FOR_FIT} runs to fit, got {len(runs)}"
            )
        predicted = np.array([
            float(np.clip(r.actual_confidence - r.delta_vs_expected, 0.0, 1.0))
            for r in runs
        ])
        observed = np.array([1.0 if r.success else 0.0 for r in runs])
        model = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        model.fit(predicted, observed)
        grid = np.linspace(0.0, 1.0, _GRID_POINTS)
        calibrated = model.predict(grid)
        mappings = [(float(g), float(c)) for g, c in zip(grid, calibrated, strict=True)]
        payload = "|".join(f"{x:.4f}:{y:.4f}" for x, y in mappings)
        version = hashlib.sha256(payload.encode()).hexdigest()[:16]
        curve = CalibrationCurve(
            id=uuid4(),
            model_version=version,
            created_at=datetime.now(),
            samples_count=len(runs),
            mappings=mappings,
        )
        await self._repository.save(curve)
        self._cached = None  # invalidate cache
        return curve

    async def active_curve(self) -> CalibrationCurve | None:
        return await self._load_active()

    async def _load_active(self) -> CalibrationCurve | None:
        if self._cached is None:
            self._cached = await self._repository.active()
        return self._cached
