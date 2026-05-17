from dataclasses import dataclass, field


@dataclass(slots=True)
class DecisionReport:
    question: str
    upside: list[str] = field(default_factory=list)
    downside: list[str] = field(default_factory=list)
    risks: list[dict] = field(default_factory=list)
    confidence: float = 0.0
    recommendation: str = ""


class DecisionAssistant:
    async def analyze(
        self,
        question: str,
        branch_results: list | None = None,
    ) -> DecisionReport:
        """Analyze a strategic question with risk/return framework.

        Without LLM: extracts upside/downside from branch_results findings.
        With LLM (future): deep narrative analysis.
        """
        report = DecisionReport(question=question)

        if branch_results:
            for result in branch_results:
                for finding in result.findings:
                    if finding.confidence >= 0.8:
                        report.upside.append(finding.statement)
                    elif finding.confidence < 0.5:
                        report.downside.append(finding.statement)
                    report.risks.append(
                        {
                            "finding": finding.statement,
                            "confidence": finding.confidence,
                            "topic": finding.topic,
                        }
                    )

            if report.upside or report.downside:
                total = len(report.upside) + len(report.downside)
                positive_ratio = len(report.upside) / max(total, 1)
                report.confidence = round(0.3 + (positive_ratio * 0.5), 2)

                if report.confidence >= 0.7:
                    report.recommendation = "Positive outlook based on high-confidence findings"
                elif report.confidence >= 0.4:
                    report.recommendation = "Mixed signals — consider deeper investigation"
                else:
                    report.recommendation = (
                        "Insufficient high-confidence findings for clear recommendation"
                    )
            else:
                report.recommendation = "No findings available for analysis"
        else:
            report.recommendation = "Provide branch_results for evidence-based analysis"

        return report
