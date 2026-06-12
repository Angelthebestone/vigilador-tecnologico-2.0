from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from vigilancia_multiagente.application.evaluation.audit.bias_auditor import BiasAuditor
from vigilancia_multiagente.domain.evaluation_entities import BiasThresholds
from vigilancia_multiagente.domain.models import BranchType, FinalReport, SourceRef


@pytest.mark.asyncio
async def test_bias_auditor_flags_geographic_overrepresentation() -> None:
    report = FinalReport(
        session_id=uuid4(),
        all_sources=[
            SourceRef(
                id=uuid4(),
                session_id=uuid4(),
                url=f"https://example{i}.com/article",
                provider="tavily",
                branch_type=BranchType.AVANCES,
                accessed_at=datetime.now(UTC),
            )
            for i in range(8)
        ]
        + [
            SourceRef(
                id=uuid4(),
                session_id=uuid4(),
                url="https://example.de/article",
                provider="tavily",
                branch_type=BranchType.AVANCES,
                accessed_at=datetime.now(UTC),
            )
            for _ in range(2)
        ],
    )

    audit = await BiasAuditor().audit(report, BiasThresholds())

    assert audit.critical_bias_detected is True
    assert "geographic" in audit.bias_categories
    assert audit.geographic_distribution["US"] == pytest.approx(0.8)
