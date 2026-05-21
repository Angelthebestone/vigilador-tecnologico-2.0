"""Evalua regresion de prompts en branches.

Sub-componente del `GoldenCaseRunner` (WS-E): cuando un golden case define
`expected_prompts`, este servicio compara salidas LLM contra baseline
historico y reporta deltas.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class PromptRegressionResult:
    branch_type: str
    passed: bool
    coverage_delta: float
    precision_delta: float


class PromptRegressionService:
    def evaluate(
        self, branch_type: str, coverage_delta: float, precision_delta: float
    ) -> PromptRegressionResult:
        passed = coverage_delta >= -0.05 and precision_delta >= -0.05
        return PromptRegressionResult(
            branch_type=branch_type,
            passed=passed,
            coverage_delta=coverage_delta,
            precision_delta=precision_delta,
        )
