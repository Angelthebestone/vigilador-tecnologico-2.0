from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from vigilancia_multiagente.application.evaluation.calibration.isotonic_calibrator import (
    IsotonicConfidenceCalibrator,
)
from vigilancia_multiagente.domain.evaluation_entities import CalibrationCurve, GoldenCaseRun


class MemoryCurveStore:
    def __init__(self) -> None:
        self.saved: list[CalibrationCurve] = []
        self._active: CalibrationCurve | None = None

    async def save(self, curve: CalibrationCurve) -> None:
        self.saved.append(curve)

    async def active(self) -> CalibrationCurve | None:
        return self._active

    async def activate(self, model_version: str) -> None:
        self._active = next(curve for curve in self.saved if curve.model_version == model_version)


def _run(actual: float, delta: float, success: bool) -> GoldenCaseRun:
    return GoldenCaseRun(
        id=uuid4(),
        case_id=uuid4(),
        run_at=datetime.now(UTC),
        success=success,
        actual_confidence=actual,
        delta_vs_expected=delta,
    )


@pytest.mark.asyncio
async def test_calibrate_is_identity_with_under_50_samples() -> None:
    store = MemoryCurveStore()
    calibrator = IsotonicConfidenceCalibrator(store)

    result = await calibrator.calibrate(0.73)

    assert result == pytest.approx(0.73)


@pytest.mark.asyncio
async def test_retrain_builds_curve_and_recovers_after_activation() -> None:
    store = MemoryCurveStore()
    calibrator = IsotonicConfidenceCalibrator(store)
    runs = [
        _run(0.10, -0.10, False),
        _run(0.20, -0.10, False),
        _run(0.30, -0.10, False),
        _run(0.40, -0.05, False),
        *[_run(0.50 + index * 0.01, 0.0, True) for index in range(46)],
    ]

    curve = await calibrator.retrain(runs)
    await store.activate(curve.model_version)

    calibrated = await calibrator.calibrate(0.2)
    active_curve = await calibrator.active_curve()

    assert curve.samples_count == 50
    assert active_curve is not None
    assert active_curve.model_version == curve.model_version
    assert calibrated != pytest.approx(0.2)

