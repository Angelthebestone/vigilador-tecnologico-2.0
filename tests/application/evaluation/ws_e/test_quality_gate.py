from __future__ import annotations

from uuid import uuid4

import pytest

from vigilancia_multiagente.application.evaluation.report_quality_gate import (
    QualityGateBlocked,
    ReportQualityGate,
)
from vigilancia_multiagente.domain.evaluation_entities import (
    BiasAudit,
    FalsificationScenario,
    StakeholderSimulation,
    StakeholderType,
    TraceStep,
    TraceStepType,
)
from vigilancia_multiagente.domain.models import FinalReport


class FakeForensicWriter:
    def __init__(self, order: list[str]) -> None:
        self.order = order

    async def finalize(self, claim_id):
        self.order.append("finalize")
        return type(
            "Trace",
            (),
            {
                "chain": [
                    TraceStep(
                        step_type=TraceStepType.SOURCE_FETCH,
                        input_ref="in",
                        output_ref="out",
                        applied_rule="rule",
                    )
                ]
            },
        )()


class FakeBiasAuditor:
    def __init__(self, order: list[str], audit: BiasAudit) -> None:
        self.order = order
        self.audit_result = audit

    async def audit(self, report, thresholds):
        del report, thresholds
        self.order.append("audit")
        return self.audit_result


class FakeFalsificationProber:
    def __init__(self, order: list[str]) -> None:
        self.order = order

    async def probe(self, conclusion: str):
        del conclusion
        self.order.append("probe")
        return [
            FalsificationScenario(
                conclusion_id=uuid4(),
                hypothetical_evidence="counter-evidence",
                plausibility=0.6,
                falsifiable=True,
            )
        ]


class FakeStakeholderSimulator:
    def __init__(self, order: list[str]) -> None:
        self.order = order

    async def simulate(self, report, stakeholder: str):
        del report
        self.order.append(f"simulate:{stakeholder}")
        return StakeholderSimulation(
            report_id=uuid4(),
            stakeholder_type=StakeholderType(stakeholder),
            critique="critique",
        )


class FakeCalibrator:
    def __init__(self, order: list[str]) -> None:
        self.order = order

    async def calibrate(self, raw_score: float) -> float:
        self.order.append("calibrate")
        return raw_score + 0.1


@pytest.mark.asyncio
async def test_quality_gate_runs_in_order() -> None:
    order: list[str] = []
    report = FinalReport(
        session_id=uuid4(),
        executive_summary="first conclusion",
        confidence_score=0.6,
    )
    gate = ReportQualityGate(
        bias_auditor=FakeBiasAuditor(
            order,
            BiasAudit(
                report_id=report.session_id,
                geographic_distribution={"US": 0.5},
                gender_distribution={},
                institutional_distribution={"industry": 0.5},
                critical_bias_detected=False,
            ),
        ),
        falsification_prober=FakeFalsificationProber(order),
        stakeholder_simulator=FakeStakeholderSimulator(order),
        calibrator=FakeCalibrator(order),
        forensic_trace_writer=FakeForensicWriter(order),
    )

    assurance = await gate.run(report)

    assert order == [
        "finalize",
        "audit",
        "probe",
        "simulate:investor",
        "simulate:regulator",
        "simulate:competitor",
        "simulate:academic",
        "calibrate",
    ]
    assert assurance.calibrated_confidence == pytest.approx(0.7)
    assert assurance.forensic_trace_count == 1
    assert len(assurance.falsification_scenarios) == 1
    assert len(assurance.stakeholder_simulations) == 4


@pytest.mark.asyncio
async def test_quality_gate_blocks_on_critical_bias() -> None:
    report = FinalReport(session_id=uuid4(), executive_summary="first conclusion")
    gate = ReportQualityGate(
        bias_auditor=FakeBiasAuditor(
            [],
            BiasAudit(
                report_id=report.session_id,
                geographic_distribution={"US": 1.0},
                gender_distribution={},
                institutional_distribution={"industry": 1.0},
                critical_bias_detected=True,
                bias_categories=["geographic"],
            ),
        ),
        falsification_prober=FakeFalsificationProber([]),
        stakeholder_simulator=FakeStakeholderSimulator([]),
        calibrator=FakeCalibrator([]),
    )

    with pytest.raises(QualityGateBlocked) as exc_info:
        await gate.run(report)

    assert exc_info.value.audit.bias_categories == ["geographic"]

