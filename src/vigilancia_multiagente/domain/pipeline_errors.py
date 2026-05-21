"""Errores trazables del pipeline de evaluacion (spec 007).

Value objects puros para errores de pasos del pipeline. Viven en `domain/`
para poder formar parte de `FinalReport` sin violar DIP (`application/` no
puede ser importada desde `domain/`).

Cada PipelineStep que falla en una operacion no-critica (LLM down, API
externa no responde, schema invalido) construye un `StepError` y lo anade
al contexto en vez de propagar la excepcion. El siguiente step lee la
lista y decide degradacion vs aborto segun la severidad.

Cumple Manejo de Errores Estricto: cada error se propaga o se transforma
con contexto util, ninguno se silencia.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class Workstream(StrEnum):
    WS_A = "WS-A"
    WS_B = "WS-B"
    WS_C = "WS-C"
    WS_D = "WS-D"
    WS_E = "WS-E"


class StepErrorSeverity(StrEnum):
    """`warning` permite continuar; `error` aborta el pipeline."""

    WARNING = "warning"
    ERROR = "error"


@dataclass(slots=True, frozen=True)
class StepError:
    workstream: Workstream
    step_name: str
    reason: str
    exception_type: str
    context: dict[str, Any] = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=datetime.now)
    severity: StepErrorSeverity = StepErrorSeverity.WARNING
