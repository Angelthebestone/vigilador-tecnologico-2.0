from __future__ import annotations

from uuid import uuid4

import pytest

from vigilancia_multiagente.application.evaluation.ws_e.orchestrator_golden_case_runner import (
    OrchestratorGoldenCaseRunner,
)
from vigilancia_multiagente.domain.evaluation_entities import (
    ExpectedFinding,
    GoldenCase,
    GoldenCasePriority,
)


class MemoryGoldenCaseRepository:
    def __init__(self, cases: list[GoldenCase]) -> None:
        self.cases = cases
        self.runs = []

    async def list_active(self) -> list[GoldenCase]:
        return list(self.cases)

    async def record_run(self, run) -> None:
        self.runs.append(run)

    async def recent_runs(self, case_id, limit: int = 20):
        del case_id, limit
        return []


class Sandbox:
    async def run_seed_query(self, seed_query: str):
        query = seed_query.lower()
        if "alphafold" in query:
            return {
                "confidence": 0.71,
                "findings": [
                    {
                        "topic": "alphafold",
                        "statement": "structure prediction baseline remains strong",
                        "confidence_min": 0.7,
                        "confidence_max": 0.9,
                    }
                ],
            }
        if "chem" in query:
            return {
                "confidence": 0.69,
                "findings": [
                    {
                        "topic": "llm-chem",
                        "statement": "assistant-assisted chemistry claims need caution",
                        "confidence_min": 0.65,
                        "confidence_max": 0.85,
                    }
                ],
            }
        return {
            "confidence": 0.75,
            "findings": [
                {
                    "topic": "convergence",
                    "statement": "cross-domain convergence is plausible but noisy",
                    "confidence_min": 0.6,
                    "confidence_max": 0.82,
                }
            ],
        }


@pytest.fixture
def golden_case_repository() -> MemoryGoldenCaseRepository:
    return MemoryGoldenCaseRepository(
        [
            GoldenCase(
                id=uuid4(),
                name="alphafold-baseline",
                description="",
                seed_query="alphafold baseline claim",
                expected_findings=[
                    ExpectedFinding(
                        topic="alphafold",
                        statement="structure prediction baseline remains strong",
                        confidence_min=0.7,
                        confidence_max=0.9,
                    )
                ],
                expected_confidence=0.74,
                priority=GoldenCasePriority.P2_NORMAL,
            ),
            GoldenCase(
                id=uuid4(),
                name="llm-chem",
                description="",
                seed_query="llm chemistry claim",
                expected_findings=[
                    ExpectedFinding(
                        topic="llm-chem",
                        statement="assistant-assisted chemistry claims need caution",
                        confidence_min=0.65,
                        confidence_max=0.85,
                    )
                ],
                expected_confidence=0.72,
                priority=GoldenCasePriority.P2_NORMAL,
            ),
            GoldenCase(
                id=uuid4(),
                name="convergence-ai-bio",
                description="",
                seed_query="ai biology convergence claim",
                expected_findings=[
                    ExpectedFinding(
                        topic="convergence",
                        statement="cross-domain convergence is plausible but noisy",
                        confidence_min=0.6,
                        confidence_max=0.82,
                    )
                ],
                expected_confidence=0.78,
                priority=GoldenCasePriority.P2_NORMAL,
            ),
        ]
    )


@pytest.mark.asyncio
async def test_golden_suite_runs_all_active_cases(golden_case_repository) -> None:
    runner = OrchestratorGoldenCaseRunner(
        golden_case_repository,
        sandbox_orchestrator=Sandbox(),
    )

    cases = await golden_case_repository.list_active()
    runs = [await runner.run_case(case) for case in cases]

    assert len(runs) == len(cases)
    assert all(run.success for run in runs)
    assert all(abs(run.delta_vs_expected) <= 0.05 for run in runs)

