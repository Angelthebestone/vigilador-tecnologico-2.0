
# STATUS: MIGRATE -- migrar a spec 007
# DEPRECATED: migrar a spec 007
# STATUS: MIGRATE — migrar a spec 007 (evaluación de regresión de prompts, pertenece a QA)
# DEPRECATED: migrar a spec 007

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
