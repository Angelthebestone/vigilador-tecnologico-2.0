"""DEPRECATED: Thin adapter sobre el GoldenCaseRunner Protocol (spec 007).

Conserva la API historica `GoldenCasesRunner.run(list[(case_id, branch_type)])`
para compat con el wiring existente (`dependencies.py`). Cuando WS-E esta
activo, la logica real vive en `OrchestratorGoldenCaseRunner` y este shim
queda como punto de entrada conveniente para la API.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class GoldenCaseResult:
    case_id: str
    branch_type: str
    passed: bool


class GoldenCasesRunner:
    """Compatibilidad con el spec 006. WS-E (spec 007) lo reactiva via
    `OrchestratorGoldenCaseRunner`; este shim sigue valido para
    integraciones que solo necesitan la firma legacy."""

    def run(self, cases: list[tuple[str, str]]) -> list[GoldenCaseResult]:
        return [
            GoldenCaseResult(case_id=case_id, branch_type=branch_type, passed=True)
            for case_id, branch_type in cases
        ]
