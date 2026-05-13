from dataclasses import dataclass, field


@dataclass(slots=True)
class HypeReport:
    tech: str
    hype_ratio: float = 0.0
    verdict: str = "unknown"
    signals: dict[str, int] = field(default_factory=dict)
    analysis: str = ""


class HypeDetector:
    async def analyze(
        self,
        tech_name: str,
        arxiv_papers: list | None = None,
        exa_companies: list | None = None,
        firecrawl_prototypes: list | None = None,
        serper_patents: list | None = None,
    ) -> HypeReport:
        report = HypeReport(tech=tech_name)
        signals: dict[str, int] = {}

        if arxiv_papers is not None:
            signals["academic_papers"] = len(arxiv_papers)
        if exa_companies is not None:
            signals["companies_with_funding"] = len(exa_companies)
        if firecrawl_prototypes is not None:
            signals["working_prototypes"] = len(firecrawl_prototypes)
        if serper_patents is not None:
            signals["patents"] = len(serper_patents)

        report.signals = signals

        if not signals:
            report.hype_ratio = 0.0
            report.verdict = "insufficient_data"
            report.analysis = f"Connect MCP providers (arxiv, exa, firecrawl, serper) to analyze {tech_name}"
            return report

        substance = sum(signals.values())
        buzz = max(0, substance // 2)

        report.hype_ratio = round(buzz / (substance + 1), 2)

        if report.hype_ratio > 0.7:
            report.verdict = "exagerada"
            report.analysis = f"{tech_name} appears overhyped: {substance} substance signals vs estimated buzz"
        elif report.hype_ratio > 0.3:
            report.verdict = "real"
            report.analysis = f"{tech_name} shows substantive signals ({substance} evidence points)"
        else:
            report.verdict = "real"
            report.analysis = f"{tech_name} appears grounded in real research/companies"

        return report
