"""OrchestratorGoldenCaseRunner — spec 007 T021 (WS-E).

Ejecuta los golden cases invocando un orquestador inyectado en modo sandbox
y compara la confianza obtenida contra la `expected_confidence`. Persiste
cada ejecucion via `GoldenCaseRepository.record_run`.

Contrato: el orquestador inyectado debe exponer una corutina
`async run_seed_query(seed_query: str) -> float` que devuelva la confianza
final del reporte (sin persistirlo en prod). Se inyecta via duck-typing
para no acoplar el runner al orquestador concreto del 006.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Protocol
from uuid import uuid4

from vigilancia_multiagente.domain.evaluation_entities import (
    ExpectedFinding,
    GoldenCase,
    GoldenCaseRun,
)
from vigilancia_multiagente.domain.ports.golden_case_repository import (
    GoldenCaseRepository,
)

logger = logging.getLogger(__name__)


class SandboxOrchestrator(Protocol):
    """Contrato minimo del orquestador en modo sandbox.

    Vive aqui (no en domain/ports) porque es un puerto privado del runner —
    no expone capacidades reutilizables fuera de WS-E (YAGNI).
    """

    async def run_seed_query(self, seed_query: str) -> float | dict[str, Any]: ...


class OrchestratorGoldenCaseRunner:
    def __init__(
        self,
        repository: GoldenCaseRepository,
        sandbox_orchestrator: SandboxOrchestrator | None = None,
    ) -> None:
        self._repository = repository
        self._sandbox = sandbox_orchestrator

    async def run_case(self, case: GoldenCase) -> GoldenCaseRun:
        if self._sandbox is None:
            return _skipped(case, reason="sandbox_orchestrator not injected")

        try:
            sandbox_result = await self._sandbox.run_seed_query(case.seed_query)
        except Exception as exc:  # noqa: BLE001 — runner tolera fallos del flujo
            logger.warning(
                "OrchestratorGoldenCaseRunner: case %s failed with %s",
                case.name,
                exc,
            )
            run = GoldenCaseRun(
                id=uuid4(),
                case_id=case.id,
                run_at=datetime.now(),
                success=False,
                actual_confidence=0.0,
                delta_vs_expected=-case.expected_confidence,
                failure_details=f"{exc.__class__.__name__}: {exc}",
            )
            await self._repository.record_run(run)
            return run

        actual_confidence = _extract_confidence(sandbox_result)
        actual_findings = _extract_findings(sandbox_result)
        delta = actual_confidence - case.expected_confidence
        findings_match = _match_expected_findings(case.expected_findings, actual_findings)
        # Tolerancia 0.05 sobre la confianza esperada — criterio del plan
        # (Phase 3 Independent Test Criteria).
        success = abs(delta) <= 0.05 and findings_match is not False
        failure_details: str | None = None
        if not success:
            reasons: list[str] = []
            if abs(delta) > 0.05:
                reasons.append(f"delta {delta:+.3f} exceeds tolerance 0.05")
            if findings_match is False:
                reasons.append("expected_findings do not match sandbox output")
            failure_details = "; ".join(reasons) if reasons else None
        run = GoldenCaseRun(
            id=uuid4(),
            case_id=case.id,
            run_at=datetime.now(),
            success=success,
            actual_confidence=actual_confidence,
            delta_vs_expected=delta,
            failure_details=failure_details,
        )
        await self._repository.record_run(run)
        return run

    async def run_all(self) -> list[GoldenCaseRun]:
        cases = await self._repository.list_active()
        runs: list[GoldenCaseRun] = []
        for case in cases:
            runs.append(await self.run_case(case))
        return runs


def _skipped(case: GoldenCase, *, reason: str) -> GoldenCaseRun:
    return GoldenCaseRun(
        id=uuid4(),
        case_id=case.id,
        run_at=datetime.now(),
        success=False,
        actual_confidence=0.0,
        delta_vs_expected=-case.expected_confidence,
        failure_details=f"skipped: {reason}",
    )


def _extract_confidence(result: float | dict[str, Any]) -> float:
    if isinstance(result, (int, float)):
        return float(result)
    for key in ("actual_confidence", "confidence", "confidence_score"):
        value = result.get(key)
        if value is not None:
            return float(value)
    raise ValueError("sandbox_orchestrator returned no confidence value")


def _extract_findings(result: float | dict[str, Any]) -> list[dict[str, Any]] | None:
    if isinstance(result, dict):
        raw_findings = result.get("findings")
        if isinstance(raw_findings, list):
            findings: list[dict[str, Any]] = []
            for item in raw_findings:
                if isinstance(item, dict):
                    findings.append(item)
            return findings
    return None


def _match_expected_findings(
    expected: list[ExpectedFinding], actual: list[dict[str, Any]] | None
) -> bool | None:
    if actual is None:
        return None
    expected_norm = [
        (
            finding.topic,
            finding.statement,
            round(finding.confidence_min, 4),
            round(finding.confidence_max, 4),
        )
        for finding in expected
    ]
    actual_norm = [
        (
            str(item.get("topic", "")),
            str(item.get("statement", "")),
            round(float(item.get("confidence_min", 0.0)), 4),
            round(float(item.get("confidence_max", 1.0)), 4),
        )
        for item in actual
    ]
    return expected_norm == actual_norm
