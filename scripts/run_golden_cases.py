#!/usr/bin/env python3
"""Run WS-E golden cases and print their deltas."""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass

from vigilancia_multiagente.application.evaluation.ws_e.orchestrator_golden_case_runner import (
    OrchestratorGoldenCaseRunner,
)
from vigilancia_multiagente.infra.db.connection import Database
from vigilancia_multiagente.infra.persistence.golden_case_repository import (
    PostgresGoldenCaseRepository,
)


@dataclass(slots=True)
class _SandboxOrchestrator:
    async def run_seed_query(self, seed_query: str) -> dict[str, object]:
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


async def _run(case_name: str | None) -> None:
    database = Database()
    repository = PostgresGoldenCaseRepository(database)
    runner = OrchestratorGoldenCaseRunner(repository, sandbox_orchestrator=_SandboxOrchestrator())
    cases = await repository.list_active()
    if case_name is not None:
        cases = [case for case in cases if case.name == case_name]
    if not cases:
        raise SystemExit("No matching golden cases found.")

    for case in cases:
        run = await runner.run_case(case)
        status = "PASS" if run.success else "FAIL"
        print(
            f"{status} {case.name}: actual={run.actual_confidence:.3f} "
            f"expected={case.expected_confidence:.3f} delta={run.delta_vs_expected:+.3f}"
        )
        if run.failure_details:
            print(f"  {run.failure_details}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run WS-E golden cases")
    parser.add_argument("--case", dest="case_name", help="Run a single golden case")
    args = parser.parse_args()
    asyncio.run(_run(args.case_name))


if __name__ == "__main__":
    main()
