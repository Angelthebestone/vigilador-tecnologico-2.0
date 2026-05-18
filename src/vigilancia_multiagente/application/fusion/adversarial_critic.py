"""Auto-crítica adversarial del reporte (reflexion).

El prompt de síntesis incluye un bloque <self_verification>, pero eso solo
*pide* al LLM que se revise y el LLM tiende a aprobar su propio trabajo. Aquí
los mismos checks se aplican en código, de forma determinística e
inapelable: afirmaciones sin fuente, recomendaciones sin respaldo,
contradicciones silenciadas. Si el reporte falla, se devuelven los defectos
para anotarlos o forzar una re-síntesis.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from vigilancia_multiagente.domain.models import Finding


def _rec_text(rec: object) -> str:
    """Acepta tanto Recommendation (atributo .text) como dict {"text": ...}."""
    if isinstance(rec, dict):
        return str(rec.get("text", ""))
    return str(getattr(rec, "text", ""))


@dataclass(slots=True)
class CritiqueIssue:
    kind: str  # "unsourced_finding" | "unsupported_recommendation" | "silenced_contradiction"
    detail: str


@dataclass(slots=True)
class CritiqueReport:
    issues: list[CritiqueIssue] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.issues


class AdversarialCritic:
    """Ataca el reporte buscando lo que el sintetizador debió justificar."""

    def critique(
        self,
        findings: list[Finding],
        recommendations: list[object],
        markdown: str,
    ) -> CritiqueReport:
        report = CritiqueReport()

        # 1. Toda afirmación debe tener al menos una fuente.
        for finding in findings:
            if not finding.source_ids:
                report.issues.append(
                    CritiqueIssue(
                        kind="unsourced_finding",
                        detail=f"Finding sin fuente: «{finding.statement[:90]}»",
                    )
                )

        # 2. Toda recomendación debe apoyarse en un finding (por solapamiento
        #    léxico con algún statement).
        finding_terms = {
            term
            for finding in findings
            for term in finding.statement.lower().split()
            if len(term) > 4
        }
        for rec in recommendations:
            text = _rec_text(rec)
            rec_terms = {t for t in text.lower().split() if len(t) > 4}
            if rec_terms and not (rec_terms & finding_terms):
                report.issues.append(
                    CritiqueIssue(
                        kind="unsupported_recommendation",
                        detail=f"Recomendación sin respaldo en hallazgos: «{text[:90]}»",
                    )
                )

        # 3. Si hay findings contradictorios sobre un mismo topic pero el
        #    reporte no menciona la disputa, está silenciada.
        if self._has_contradiction(findings) and "disputa" not in markdown.lower():
            report.issues.append(
                CritiqueIssue(
                    kind="silenced_contradiction",
                    detail="Hay hallazgos contradictorios no reflejados como disputa.",
                )
            )

        return report

    @staticmethod
    def _has_contradiction(findings: list[Finding]) -> bool:
        from vigilancia_multiagente.application.evaluation.claim_polarity import (
            claims_overlap,
            polarity_conflict,
        )

        for i, a in enumerate(findings):
            for b in findings[i + 1 :]:
                if claims_overlap(a.statement, b.statement) and polarity_conflict(
                    a.statement, b.statement
                ):
                    return True
        return False

    @staticmethod
    def render_section(report: CritiqueReport) -> str:
        if report.passed:
            return ""
        lines = ["## Verificación adversarial", ""]
        lines.append(
            f"El control automático detectó {len(report.issues)} debilidad(es) "
            "que el lector debe considerar:"
        )
        lines.append("")
        for issue in report.issues:
            lines.append(f"- **[{issue.kind}]** {issue.detail}")
        lines.append("")
        return "\n".join(lines)
