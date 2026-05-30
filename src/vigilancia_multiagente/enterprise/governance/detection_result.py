"""DetectionResult — resultado de análisis del detector PI (FR-004)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class DetectionResult:
    """Resultado inmutable del análisis de prompt injection.

    Attributes:
        is_suspicious: True si se detectaron patrones de inyección.
        patterns_matched: Lista de patrones que dispararon la detección.
        severity: Nivel de severidad (HIGH/MEDIUM/LOW) según FR-005.
        confidence: Float 0.0-1.0 informativo para audit/logging.
        source: Identificador del origen del contenido analizado.
    """

    is_suspicious: bool
    patterns_matched: list[str]
    severity: Literal["LOW", "MEDIUM", "HIGH"]
    confidence: float
    source: str
