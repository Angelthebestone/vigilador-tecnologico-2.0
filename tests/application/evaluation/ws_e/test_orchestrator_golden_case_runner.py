from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest

from vigilancia_multiagente.application.evaluation.ws_e.orchestrator_golden_case_runner import (
    OrchestratorGoldenCaseRunner,
)
from vigilancia_multiagente.domain.evaluation_entities import ExpectedFinding, GoldenCase, GoldenCasePriority

pytestmark = pytest.mark.asyncio


class MemoryGoldenCaseRepository:
    def __init__(self) -> None:
        self.recorded = []

    async def list_active(self):  # pragma: no cover - not used here
        return []

    async def record_run(self, run):
        self.recorded.append(run)

    async def recent_runs(self, case_id, limit: int = 20):  # pragma: no cover - not used
        return []


class SandboxOk:
    async def run_seed_query(self, seed_query: str):
        return {
            "confidence": 0.72,
            "findings": [
                {
                    "topic": "baseline",
                    "statement": f"Result for {seed_query}",
                    "confidence_min": 0.6,
                    "confidence_max": 0.8,
                }
            ],
        }


async def test_run_case_matches_expected_findings_and_confidence():
    repo = MemoryGoldenCaseRepository()
    runner = OrchestratorGoldenCaseRunner(repo, SandboxOk())
    case = GoldenCase(
        id=uuid4(),
        name="baseline",
        description="",
        seed_query="query",
        expected_findings=[
            ExpectedFinding(
                topic="baseline",
                statement="Result for query",
                confidence_min=0.6,
                confidence_max=0.8,
            )
        ],
        expected_confidence=0.7,
        priority=GoldenCasePriority.P2_NORMAL,
    )

    run = await runner.run_case(case)

    assert run.success is True
    assert run.actual_confidence == 0.72
    assert repo.recorded[-1] == run

