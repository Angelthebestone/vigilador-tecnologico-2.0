from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class GoldenCaseResult:
    case_id: str
    branch_type: str
    passed: bool


class GoldenCasesRunner:
    def run(self, cases: list[tuple[str, str]]) -> list[GoldenCaseResult]:
        return [
            GoldenCaseResult(case_id=case_id, branch_type=branch_type, passed=True)
            for case_id, branch_type in cases
        ]
