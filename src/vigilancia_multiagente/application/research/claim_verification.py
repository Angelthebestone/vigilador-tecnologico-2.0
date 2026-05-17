"""Verificación activa de afirmaciones con una sola fuente.

Una afirmación clave sostenida por una única fuente es frágil: puede ser un
error, un rumor o propaganda. Vigilancia tecnológica seria necesita
triangular. Este planner detecta esos findings y emite queries de
verificación ("¿quién más dice esto? ¿hay refutación?") para que el loop de
seguimiento las investigue.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from vigilancia_multiagente.domain.models import Finding

# Por debajo de esta confianza el finding ya es débil y no merece gastar una
# iteración de verificación; por encima de single-source es suficientemente
# relevante para confirmarlo.
_MIN_CONFIDENCE_TO_VERIFY = 0.5


@dataclass(slots=True)
class VerificationTask:
    finding_id: str
    claim: str
    verification_query: str
    reason: str


@dataclass(slots=True)
class VerificationPlan:
    tasks: list[VerificationTask] = field(default_factory=list)

    @property
    def has_tasks(self) -> bool:
        return bool(self.tasks)


class ClaimVerificationPlanner:
    def plan(self, findings: list[Finding]) -> VerificationPlan:
        plan = VerificationPlan()
        for finding in findings:
            if len(finding.source_ids) > 1:
                continue  # ya triangulado
            if finding.confidence < _MIN_CONFIDENCE_TO_VERIFY:
                continue  # demasiado débil, no vale la iteración
            plan.tasks.append(
                VerificationTask(
                    finding_id=str(finding.id),
                    claim=finding.statement,
                    verification_query=(
                        f"independent confirmation or refutation of: {finding.statement}"
                    ),
                    reason="Afirmación relevante sostenida por una sola fuente.",
                )
            )
        return plan
