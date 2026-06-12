"""Assurance services — WS-E Output Assurance."""

from __future__ import annotations

from typing import Any

from vigilancia_multiagente.config.settings import get_settings
from vigilancia_multiagente.domain.ports.llm_client import LLMClient
from vigilancia_multiagente.domain.ports.prompt_loader import PromptLoader


def build_assurance_services(s: dict[str, Any], e: dict[str, Any]) -> dict[str, Any]:
    """ReportQualityGate + dependencias WS-E."""
    settings_local = get_settings()
    errors_sink: list[Any] = []
    if not settings_local.eval_ws_e_enabled:
        return {"gate": None, "calibrator": None, "errors_sink": errors_sink}

    from vigilancia_multiagente.application.evaluation.audit.bias_auditor import BiasAuditor
    from vigilancia_multiagente.application.evaluation.calibration.isotonic_calibrator import (
        IsotonicConfidenceCalibrator,
    )
    from vigilancia_multiagente.application.evaluation.forensic.jsonb_trace_writer import (
        JsonbForensicTraceWriter,
    )
    from vigilancia_multiagente.application.evaluation.report_quality_gate import ReportQualityGate
    from vigilancia_multiagente.application.evaluation.ws_e.llm_falsification_prober import (
        LlmFalsificationProber,
    )
    from vigilancia_multiagente.application.evaluation.ws_e.llm_stakeholder_simulator import (
        LlmStakeholderSimulator,
    )
    from vigilancia_multiagente.infra.persistence.calibration_curve_repository import (
        PostgresCalibrationCurveRepository,
    )

    curve_repo = PostgresCalibrationCurveRepository(s["database"])
    calibrator = IsotonicConfidenceCalibrator(curve_repository=curve_repo)
    bias_auditor = BiasAuditor()
    forensic_writer = JsonbForensicTraceWriter()
    llm: LLMClient = s["llm_client"]
    prompt_loader: PromptLoader = s["prompt_loader"]
    stakeholder_simulator = LlmStakeholderSimulator(
        llm=llm, prompt_loader=prompt_loader, errors_sink=errors_sink
    )
    falsification_prober = LlmFalsificationProber(
        llm=llm, prompt_loader=prompt_loader, errors_sink=errors_sink
    )
    gate = ReportQualityGate(
        bias_auditor=bias_auditor,
        falsification_prober=falsification_prober,
        stakeholder_simulator=stakeholder_simulator,
        calibrator=calibrator,
        forensic_trace_writer=forensic_writer,
    )
    return {
        "gate": gate,
        "calibrator": calibrator,
        "errors_sink": errors_sink,
        "curve_repository": curve_repo,
    }
