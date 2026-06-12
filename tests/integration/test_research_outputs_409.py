from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import HTTPException

from vigilancia_multiagente.api.routes import research_outputs
from vigilancia_multiagente.domain.evaluation_entities import (
    BiasAudit,
    ReportAssurance,
)
from vigilancia_multiagente.domain.models import FinalReport


class FakeReportRepository:
    def __init__(self, report: FinalReport) -> None:
        self._report = report

    async def get(self, session_id):
        if session_id == self._report.session_id:
            return self._report
        return None


@pytest.mark.asyncio
async def test_research_outputs_returns_409_on_critical_bias(monkeypatch) -> None:
    session_id = uuid4()
    report = FinalReport(
        session_id=session_id,
        generated_at=datetime.now(UTC),
        assurance=ReportAssurance(
            bias_audit=BiasAudit(
                report_id=session_id,
                geographic_distribution={"US": 1.0},
                gender_distribution={},
                institutional_distribution={"industry": 1.0},
                critical_bias_detected=True,
                bias_categories=["geographic"],
            )
        ),
    )
    monkeypatch.setattr(research_outputs, "report_repository", FakeReportRepository(report))

    with pytest.raises(HTTPException) as exc_info:
        await research_outputs.get_report(report.session_id)

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["reason"] == "critical_bias_detected"
