"""Tests para StepError y el helper add_step_error (spec 007 T017)."""

from __future__ import annotations

from vigilancia_multiagente.application.agents.pipeline.errors import add_step_error
from vigilancia_multiagente.domain.pipeline_errors import (
    StepError,
    StepErrorSeverity,
    Workstream,
)


def test_step_error_defaults_to_warning() -> None:
    errors: list[StepError] = []
    exc = RuntimeError("LLM timeout")

    error = add_step_error(
        errors,
        Workstream.WS_E,
        step_name="LlmStakeholderSimulator.simulate",
        exc=exc,
    )

    assert len(errors) == 1
    assert errors[0] is error
    assert error.severity is StepErrorSeverity.WARNING
    assert error.workstream is Workstream.WS_E
    assert error.exception_type == "RuntimeError"
    assert error.reason == "LLM timeout"


def test_step_error_uses_class_name_when_message_empty() -> None:
    errors: list[StepError] = []

    add_step_error(
        errors,
        Workstream.WS_A,
        step_name="OpenAlexAuthorReputationGateway.lookup",
        exc=ConnectionError(),
    )

    assert errors[0].reason == "ConnectionError"


def test_step_error_records_context_without_mutation() -> None:
    errors: list[StepError] = []
    ctx = {"author_id": "A123", "attempt": 2}

    error = add_step_error(
        errors,
        Workstream.WS_A,
        step_name="step",
        exc=ValueError("not found"),
        context=ctx,
    )

    ctx["attempt"] = 999  # mutar el original no debe afectar el StepError
    assert error.context == {"author_id": "A123", "attempt": 2}


def test_step_error_severity_can_be_promoted() -> None:
    errors: list[StepError] = []
    add_step_error(
        errors,
        Workstream.WS_B,
        step_name="ExtractionSchemaRegistry.validate",
        exc=ValueError("malformed payload"),
        severity=StepErrorSeverity.ERROR,
    )

    assert errors[0].severity is StepErrorSeverity.ERROR
