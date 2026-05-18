"""Calibración de confianza con feedback.

Los prompts asignan confidence (0.7, 0.9...) pero nadie mide si esa confianza
es acertada. Si el sistema dice "0.9" pero solo acierta el 60%, está
sobreconfiado y sus números no son fiables — y un vigilador cuya confianza no
es confiable vale poco.

Aquí se registran observaciones (confidence_predicha, ¿se confirmó después?)
agrupadas en buckets, se mide el desvío real por bucket y se expone un factor
de corrección para recalibrar confidencias futuras.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Anchos de bucket sobre [0,1]. 0.0-0.2, 0.2-0.4, ... 0.8-1.0
_BUCKET_EDGES: tuple[float, ...] = (0.2, 0.4, 0.6, 0.8, 1.01)
# Mínimo de observaciones en un bucket para que su corrección sea fiable.
_MIN_SAMPLES = 5


@dataclass(slots=True)
class _Bucket:
    predicted_sum: float = 0.0
    confirmed: int = 0
    total: int = 0


@dataclass(slots=True)
class CalibrationReport:
    samples: int
    # Por bucket: (confianza_media_predicha, tasa_real_de_acierto, n)
    buckets: list[tuple[float, float, int]] = field(default_factory=list)
    overconfident: bool = False


class ConfidenceCalibrator:
    """Acumula evidencia de calibración y corrige confidencias futuras.

    No requiere LLM ni red: pura estadística sobre el feedback ya disponible
    (un claim se confirma si otra fuente/rama lo corrobora después).
    """

    def __init__(self) -> None:
        self._buckets: list[_Bucket] = [_Bucket() for _ in _BUCKET_EDGES]

    @staticmethod
    def _bucket_index(confidence: float) -> int:
        for i, edge in enumerate(_BUCKET_EDGES):
            if confidence < edge:
                return i
        return len(_BUCKET_EDGES) - 1

    def record(self, predicted_confidence: float, was_confirmed: bool) -> None:
        bucket = self._buckets[self._bucket_index(predicted_confidence)]
        bucket.predicted_sum += predicted_confidence
        bucket.confirmed += 1 if was_confirmed else 0
        bucket.total += 1

    def calibrate(self, raw_confidence: float) -> float:
        """Corrige una confianza cruda según el historial de su bucket.

        Si el bucket tiene suficientes muestras y el sistema acertó menos de
        lo que predijo, baja la confianza proporcionalmente (y viceversa).
        """
        bucket = self._buckets[self._bucket_index(raw_confidence)]
        if bucket.total < _MIN_SAMPLES:
            return raw_confidence
        mean_predicted = bucket.predicted_sum / bucket.total
        actual_rate = bucket.confirmed / bucket.total
        if mean_predicted == 0:
            return raw_confidence
        factor = actual_rate / mean_predicted
        return round(min(1.0, max(0.0, raw_confidence * factor)), 4)

    def report(self) -> CalibrationReport:
        rows: list[tuple[float, float, int]] = []
        total_samples = 0
        overconfident = False
        for bucket in self._buckets:
            if bucket.total == 0:
                continue
            total_samples += bucket.total
            mean_pred = bucket.predicted_sum / bucket.total
            actual = bucket.confirmed / bucket.total
            rows.append((round(mean_pred, 3), round(actual, 3), bucket.total))
            if bucket.total >= _MIN_SAMPLES and actual < mean_pred - 0.1:
                overconfident = True
        return CalibrationReport(samples=total_samples, buckets=rows, overconfident=overconfident)
