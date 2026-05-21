from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import HTTPException

from vigilancia_multiagente.domain.evaluation_entities import BiasAudit, ReportAssurance
from vigilancia_multiagente.domain.models import FinalReport

pytestmark = pytest.mark.asyncio


class _BlockedReportRepository:
    def __init__(self, report: FinalReport) -> None:
        self._report = report

    async def get(self, session_id):
        return self._report


async def test_get_report_returns_409_for_blocked_assurance(monkeypatch):
    from vigilancia_multiagente.api.routes import research_outputs

    report = FinalReport(
        session_id=uuid4(),
        assurance=ReportAssurance(
            bias_audit=BiasAudit(
                report_id=uuid4(),
                geographic_distribution={"US": 1.0},
                gender_distribution={},
                institutional_distribution={"industry": 1.0},
                critical_bias_detected=True,
                bias_categories=["geographic"],
            )
        ),
    )
    monkeypatch.setattr(research_outputs, "report_repository", _BlockedReportRepository(report))

    with pytest.raises(HTTPException) as exc_info:
        await research_outputs.get_report(report.session_id)

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["reason"] == "critical_bias_detected"
