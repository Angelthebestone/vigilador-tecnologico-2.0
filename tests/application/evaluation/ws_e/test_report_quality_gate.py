from __future__ import annotations

from uuid import uuid4

import pytest

from vigilancia_multiagente.application.evaluation.report_quality_gate import ReportQualityGate
from vigilancia_multiagente.domain.evaluation_entities import (
    BiasAudit,
    FalsificationScenario,
    StakeholderSimulation,
    StakeholderType,
)
from vigilancia_multiagente.domain.models import FinalReport

pytestmark = pytest.mark.asyncio


class FakeBiasAuditor:
    async def audit(self, report, thresholds):
        return BiasAudit(
            report_id=report.session_id,
            geographic_distribution={},
            gender_distribution={},
            institutional_distribution={},
            critical_bias_detected=False,
            bias_categories=[],
        )


class FakeFalsificationProber:
    async def probe(self, conclusion: str):
        return [
            FalsificationScenario(
                conclusion_id=uuid4(),
                hypothetical_evidence=f"counter {conclusion}",
                plausibility=0.5,
                falsifiable=True,
            )
        ]


class FakeStakeholderSimulator:
    async def simulate(self, report, stakeholder: str):
        return StakeholderSimulation(
            report_id=report.session_id,
            stakeholder_type=StakeholderType(stakeholder),
            critique=stakeholder,
            counterpoints=[],
        )


class FakeCalibrator:
    async def calibrate(self, value: float) -> float:
        return 0.55


class FakeTraceWriter:
    def __init__(self) -> None:
        self.finalized = []

    async def finalize(self, claim_id):
        self.finalized.append(claim_id)

        class Trace:
            chain: list = [object()]  # noqa: RUF012 — test fixture, intentional

        return Trace()


async def test_quality_gate_populates_assurance_kpis():
    writer = FakeTraceWriter()
    gate = ReportQualityGate(
        bias_auditor=FakeBiasAuditor(),
        falsification_prober=FakeFalsificationProber(),
        stakeholder_simulator=FakeStakeholderSimulator(),
        calibrator=FakeCalibrator(),
        forensic_trace_writer=writer,
    )
    report = FinalReport(
        session_id=uuid4(),
        markdown="## Conclusion\n\nFirst conclusion.\n\nSecond conclusion.",
        executive_summary="First conclusion.\n\nSecond conclusion.",
        confidence_score=0.8,
        total_sources_consulted=3,
        total_learnings=2,
    )

    assurance = await gate.run(report)

    assert writer.finalized == [report.session_id]
    assert assurance.forensic_trace_count == 1
    assert assurance.calibrated_confidence == 0.55
    assert assurance.kpis["falsification_scenarios_count"] == 2.0
    assert assurance.kpis["stakeholder_simulations_count"] == 4.0
