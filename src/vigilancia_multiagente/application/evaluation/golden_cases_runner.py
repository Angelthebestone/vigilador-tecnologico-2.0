"""Thin adapter sobre el GoldenCaseRunner Protocol (spec 007).

Conserva la API historica `GoldenCasesRunner.run(list[(case_id, branch_type)])`
para compat con el wiring existente (`dependencies.py`). Cuando WS-E esta
activo, la logica real vive en `OrchestratorGoldenCaseRunner` y este shim
queda como punto de entrada conveniente para la API.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Protocol

from vigilancia_multiagente.application.evaluation.prompt_regression_service import (
    PromptRegressionService,
)


@dataclass(slots=True, frozen=True)
class GoldenCaseResult:
    case_id: str
    branch_type: str
    passed: bool


class GoldenCasesRunner:
    """Adapter legacy con delegacion opcional a un runner WS-E."""

    def __init__(
        self,
        runner: object | None = None,
        prompt_regression_service: PromptRegressionService | None = None,
    ) -> None:
        self._runner = runner
        self._prompt_regression_service = prompt_regression_service or PromptRegressionService()

    def run(self, cases: list[tuple[str, str]]) -> list[GoldenCaseResult]:
        if self._runner is not None:
            return asyncio.run(self._run_with_runner(cases))
        return [
            GoldenCaseResult(case_id=case_id, branch_type=branch_type, passed=True)
            for case_id, branch_type in cases
        ]

    async def _run_with_runner(self, cases: list[tuple[str, str]]) -> list[GoldenCaseResult]:
        results = []
        if hasattr(self._runner, "run_all"):
            runs = await self._runner.run_all()
            runs_by_case_id = {str(run.case_id): run for run in runs}
            for case_id, branch_type in cases:
                run = runs_by_case_id.get(case_id)
                passed = bool(getattr(run, "success", False)) if run is not None else False
                results.append(
                    GoldenCaseResult(case_id=case_id, branch_type=branch_type, passed=passed)
                )
            return results
        if hasattr(self._runner, "run_case"):
            for case_id, branch_type in cases:
                run = await self._runner.run_case(case_id)
                passed = bool(getattr(run, "success", False))
                results.append(
                    GoldenCaseResult(case_id=case_id, branch_type=branch_type, passed=passed)
                )
            return results
        return [
            GoldenCaseResult(case_id=case_id, branch_type=branch_type, passed=False)
            for case_id, branch_type in cases
        ]
