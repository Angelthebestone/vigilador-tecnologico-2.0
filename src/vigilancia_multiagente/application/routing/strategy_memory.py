"""Memoria de estrategias que funcionan.

source_scorer aprende qué *fuentes* son fiables. El siguiente nivel: aprender
qué *secuencia de tools* produjo findings de alta confianza para cada tipo de
query, y sesgar el smart_router con ello. El sistema mejora su propia
estrategia de búsqueda con cada sesión, en vez de usar siempre el orden
estático.
"""

from __future__ import annotations

from dataclasses import dataclass

# Una estrategia necesita al menos esto para considerarse evidencia, no ruido.
_MIN_OBSERVATIONS = 3
# Confianza media por debajo de la cual la estrategia no se recomienda.
_MIN_MEAN_CONFIDENCE = 0.6


@dataclass(slots=True)
class _StrategyStats:
    confidence_sum: float = 0.0
    count: int = 0

    @property
    def mean(self) -> float:
        return self.confidence_sum / self.count if self.count else 0.0


class StrategyMemory:
    """Registra (tipo_query, orden_tools) → confianza y recomienda el mejor.

    Clave por (query_type, tupla de tools) para no mezclar estrategias de
    dominios distintos. Pura acumulación en memoria; persistible después.
    """

    def __init__(self) -> None:
        self._stats: dict[tuple[str, tuple[str, ...]], _StrategyStats] = {}

    def record(
        self,
        query_type: str,
        tool_order: tuple[str, ...],
        achieved_confidence: float,
    ) -> None:
        key = (query_type, tuple(tool_order))
        stats = self._stats.setdefault(key, _StrategyStats())
        stats.confidence_sum += achieved_confidence
        stats.count += 1

    def best_tool_order(self, query_type: str) -> tuple[str, ...] | None:
        """Mejor orden de tools observado para *query_type*, o None si no hay
        evidencia suficiente (el caller cae al orden estático)."""
        best_key: tuple[str, ...] | None = None
        best_mean = _MIN_MEAN_CONFIDENCE
        for (qtype, tools), stats in self._stats.items():
            if qtype != query_type or stats.count < _MIN_OBSERVATIONS:
                continue
            if stats.mean > best_mean:
                best_mean = stats.mean
                best_key = tools
        return best_key
