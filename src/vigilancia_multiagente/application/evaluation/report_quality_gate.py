"""ReportQualityGate — spec 007 T027 (WS-E).

Orquesta los servicios WS-E en orden:
  1. ForensicTraceWriter.finalize por cada finding.
  2. BiasAuditor.audit -> si critical_bias_detected -> QualityGateBlocked.
  3. FalsificationProber.probe por cada conclusion del executive_summary.
  4. StakeholderSimulator.simulate para los 4 perfiles.
  5. IsotonicConfidenceCalibrator.calibrate ajusta confidence_score final.

Output anexado a FinalReport.assurance (campo nuevo, default None).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from vigilancia_multiagente.domain.evaluation_entities import (
    BiasAudit,
    BiasThresholds,
    FalsificationScenario,
    ReportAssurance,
    StakeholderSimulation,
    StakeholderType,
)
from vigilancia_multiagente.domain.models import BranchResult, FinalReport

if TYPE_CHECKING:
    from vigilancia_multiagente.application.evaluation.audit.bias_auditor import (
        BiasAuditor,
    )
    from vigilancia_multiagente.application.evaluation.calibration.isotonic_calibrator import (
        IsotonicConfidenceCalibrator,
    )
    from vigilancia_multiagente.application.evaluation.forensic.jsonb_trace_writer import (
        JsonbForensicTraceWriter,
    )
    from vigilancia_multiagente.application.evaluation.branch_kpi_service import BranchKPIService
    from vigilancia_multiagente.domain.ports.falsification import FalsificationProber
    from vigilancia_multiagente.domain.ports.stakeholder_simulator import (
        StakeholderSimulator,
    )

logger = logging.getLogger(__name__)

_STAKEHOLDERS = (
    StakeholderType.INVESTOR,
    StakeholderType.REGULATOR,
    StakeholderType.COMPETITOR,
    StakeholderType.ACADEMIC,
)


class QualityGateBlocked(Exception):
    """Levantada cuando el bias audit detecta un sesgo critico.

    Captura el `BiasAudit` para que la capa API pueda exponerlo en el
    cuerpo del HTTP 409 sin acceder al gate.
    """

    def __init__(self, audit: BiasAudit) -> None:
        super().__init__(
            f"critical bias detected: {', '.join(audit.bias_categories) or 'unknown'}"
        )
        self.audit = audit


class ReportQualityGate:
    def __init__(
        self,
        bias_auditor: BiasAuditor,
        falsification_prober: FalsificationProber,
        stakeholder_simulator: StakeholderSimulator,
        calibrator: IsotonicConfidenceCalibrator,
        forensic_trace_writer: JsonbForensicTraceWriter | None = None,
        branch_kpi_service: BranchKPIService | None = None,
        thresholds: BiasThresholds | None = None,
    ) -> None:
        self._bias_auditor = bias_auditor
        self._falsification_prober = falsification_prober
        self._stakeholder_simulator = stakeholder_simulator
        self._calibrator = calibrator
        self._forensic_trace_writer = forensic_trace_writer
        self._branch_kpi_service = branch_kpi_service
        self._thresholds = thresholds or BiasThresholds()

    async def run(
        self,
        report: FinalReport,
        branch_results: list[BranchResult] | None = None,
    ) -> ReportAssurance:
        forensic_count = 0
        if self._forensic_trace_writer is not None:
            # El modelo actual no expone claim_ids, asi que cerramos una traza
            # por reporte usando el session_id como clave estable.
            forensic_trace = await self._forensic_trace_writer.finalize(report.session_id)
            forensic_count = len(forensic_trace.chain)

        audit = await self._bias_auditor.audit(report, self._thresholds)
        if audit.critical_bias_detected:
            raise QualityGateBlocked(audit)

        scenarios: list[FalsificationScenario] = []
        for conclusion in _split_conclusions(report.executive_summary or report.markdown):
            scenarios.extend(await self._falsification_prober.probe(conclusion))

        simulations: list[StakeholderSimulation] = []
        for stakeholder in _STAKEHOLDERS:
            simulations.append(
                await self._stakeholder_simulator.simulate(report, stakeholder.value)
            )

        calibrated = await self._calibrator.calibrate(report.confidence_score)
        kpis: dict[str, float] = {
            "forensic_trace_count": float(forensic_count),
            "falsification_scenarios_count": float(len(scenarios)),
            "stakeholder_simulations_count": float(len(simulations)),
            "calibrated_confidence": float(calibrated),
            "sources_consulted": float(report.total_sources_consulted),
            "learnings": float(report.total_learnings),
        }
        if self._branch_kpi_service is not None and branch_results is not None:
            for result in branch_results:
                branch_kpi = self._branch_kpi_service.compute(
                    result, latency_ms=500, cost_kpi=0.0
                )
                prefix = result.branch_type.value.lower()
                kpis[f"{prefix}_coverage_kpi"] = branch_kpi.coverage_kpi
                kpis[f"{prefix}_precision_kpi"] = branch_kpi.precision_kpi
                kpis[f"{prefix}_latency_ms_kpi"] = float(branch_kpi.latency_ms_kpi)
                kpis[f"{prefix}_cost_kpi"] = branch_kpi.cost_kpi

        return ReportAssurance(
            bias_audit=audit,
            stakeholder_simulations=simulations,
            falsification_scenarios=scenarios,
            calibrated_confidence=calibrated,
            forensic_trace_count=forensic_count,
            kpis=kpis,
        )


def _split_conclusions(text: str) -> list[str]:
    """Heuristica: cada parrafo del executive_summary es una conclusion."""
    if not text:
        return []
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    return paragraphs[:5]  # techo defensivo para no disparar coste LLM
