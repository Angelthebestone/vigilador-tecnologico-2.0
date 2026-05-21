"""Contradicciones entre findings expuestas como sección del reporte.

Donde las fuentes no concuerdan está la incertidumbre real, así que esa señal
es un producto explícito y no un cálculo descartado en el source scoring.
"""
# STATUS: ACTIVE

# STATUS: ACTIVE — consumer: report_synthesizer (ContradictionAnalyzer.render_section)

from __future__ import annotations

from dataclasses import dataclass, field

from vigilancia_multiagente.application.evaluation._markdown import markdown_section
from vigilancia_multiagente.application.evaluation.claim_polarity import polarity_conflict
from vigilancia_multiagente.domain.models import Finding


@dataclass(slots=True)
class DisputedPoint:
    topic: str
    statement_a: str
    statement_b: str
    confidence_a: float
    confidence_b: float
    explanation: str


@dataclass(slots=True)
class ContradictionReport:
    disputed_points: list[DisputedPoint] = field(default_factory=list)

    @property
    def has_disputes(self) -> bool:
        return bool(self.disputed_points)


class ContradictionAnalyzer:
    def analyze(self, findings: list[Finding]) -> ContradictionReport:
        report = ContradictionReport()
        word_sets = [set(f.statement.lower().split()) for f in findings]
        for i, finding_a in enumerate(findings):
            for offset, finding_b in enumerate(findings[i + 1 :]):
                j = i + 1 + offset
                if not self._topics_overlap(finding_a, finding_b, word_sets[i], word_sets[j]):
                    continue
                if polarity_conflict(finding_a.statement, finding_b.statement):
                    report.disputed_points.append(
                        DisputedPoint(
                            topic=finding_a.topic,
                            statement_a=finding_a.statement,
                            statement_b=finding_b.statement,
                            confidence_a=finding_a.confidence,
                            confidence_b=finding_b.confidence,
                            explanation=(
                                "Las fuentes difieren en polaridad sobre un tema "
                                "compartido; revisar evidencia antes de concluir."
                            ),
                        )
                    )
        return report

    @staticmethod
    def _topics_overlap(
        finding_a: Finding,
        finding_b: Finding,
        words_a: set[str],
        words_b: set[str],
    ) -> bool:
        if finding_a.topic == finding_b.topic:
            return True
        return len(words_a & words_b) >= 3

    @staticmethod
    def render_section(report: ContradictionReport) -> str:
        body: list[str] = []
        for point in report.disputed_points:
            body.append(f"### {point.topic}")
            body.append(f"- **A** (conf. {point.confidence_a:.2f}): {point.statement_a}")
            body.append(f"- **B** (conf. {point.confidence_b:.2f}): {point.statement_b}")
            body.append(f"- _{point.explanation}_")
            body.append("")
        return markdown_section("Puntos en disputa", body)
