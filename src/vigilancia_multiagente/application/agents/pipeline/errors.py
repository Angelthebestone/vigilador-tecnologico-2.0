"""Helper de aplicacion para registrar StepErrors en el contexto del pipeline.

El value object `StepError` vive en `domain/pipeline_errors.py` (puede ser
referenciado por `FinalReport`). Aqui solo vive el helper `add_step_error`
que captura una excepcion y la transforma en `StepError` en el contexto del
step que la origino — es logica de aplicacion, no de dominio.
"""

from __future__ import annotations

from typing import Any

from vigilancia_multiagente.domain.pipeline_errors import (
    StepError,
    StepErrorSeverity,
    Workstream,
)

__all__ = ["StepError", "StepErrorSeverity", "Workstream", "add_step_error"]


def add_step_error(
    errors: list[StepError],
    workstream: Workstream,
    step_name: str,
    exc: BaseException,
    *,
    severity: StepErrorSeverity = StepErrorSeverity.WARNING,
    context: dict[str, Any] | None = None,
) -> StepError:
    """Helper para crear un StepError desde una excepcion y registrarlo.

    Captura el tipo de excepcion y su mensaje accionable (no el traceback,
    el traceback queda en los logs del step). Devuelve el StepError creado.
    """
    error = StepError(
        workstream=workstream,
        step_name=step_name,
        reason=str(exc) or exc.__class__.__name__,
        exception_type=exc.__class__.__name__,
        context=dict(context) if context else {},
        severity=severity,
    )
    errors.append(error)
    return error
