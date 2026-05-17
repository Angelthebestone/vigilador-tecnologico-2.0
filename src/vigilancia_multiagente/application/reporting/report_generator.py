"""Multi-stakeholder report generator. Produces report variants from research findings."""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ReportGenerator:
    """
    Generates multiple report variants from the same research findings,
    each tailored to a specific stakeholder audience.
    """

    def __init__(self):
        self._templates = {
            "technical": self._build_technical_report,
            "executive": self._build_executive_brief,
            "risk": self._build_risk_report,
        }

    async def generate(self, findings: dict, report_type: str) -> dict:
        builder = self._templates.get(report_type)
        if not builder:
            return {"error": f"Unknown report type: {report_type}"}
        return await builder(findings)

    async def generate_all(self, findings: dict) -> dict[str, dict]:
        results = {}
        for rtype in ["technical", "executive", "risk"]:
            results[rtype] = await self.generate(findings, rtype)
        return results

    async def _build_technical_report(self, findings: dict) -> dict:
        sections = []

        sections.append(
            self._section(
                "Methodology",
                f"Research conducted on: {findings.get('query', 'N/A')}\n\n"
                f"Branches used: {', '.join(findings.get('branches', []))}\n"
                f"Sources consulted: {len(findings.get('sources', []))} unique providers\n"
                f"Total findings collected: {len(findings.get('findings', []))}",
            )
        )

        sources = findings.get("sources", [])
        source_text = "\n".join(
            f"- {s.get('name', s)} (confidence: {s.get('score', 'N/A')})" for s in sources[:20]
        )
        sections.append(self._section("Data Sources", source_text or "No sources recorded."))

        analytics = findings.get("analytics", {})
        bio_text = (
            f"Novelty scores computed for {len(analytics.get('novelty_scores', []))} papers\n"
        )
        bio_text += f"Emerging clusters identified: {len(analytics.get('clusters', []))}\n"
        bio_text += f"Co-authorship network: {analytics.get('network_stats', 'N/A')}"
        sections.append(self._section("Bibliometric Analysis", bio_text))

        trends = findings.get("trend_projections", [])
        trend_text = (
            "\n\n".join(
                f"**{t.get('metric', 'Trend')}**: {t.get('model_type', 'N/A')} model, "
                f"{len(t.get('projected_values', []))} projected periods"
                for t in trends[:5]
            )
            or "No trend projections available."
        )
        sections.append(self._section("Trend Projections", trend_text))

        return {
            "type": "technical",
            "title": f"Technical Report: {findings.get('query', 'Research')}",
            "sections": sections,
            "generated_at": datetime.utcnow().isoformat(),
        }

    async def _build_executive_brief(self, findings: dict) -> dict:
        sections = []

        branches = findings.get("branch_summaries", {})
        takeaways = (
            "\n".join(
                f"- **{b}**: {s.get('summary', 'No summary available')[:200]}"
                for b, s in branches.items()
            )
            or "No key takeaways available."
        )
        sections.append(self._section("Key Takeaways", takeaways))

        recs = findings.get("recommendations", [])
        rec_text = (
            "\n".join(f"- {r}" for r in recs[:10])
            or "Generate recommendations from branch findings."
        )
        sections.append(self._section("Strategic Recommendations", rec_text))

        comp = findings.get("competitive", {})
        comp_text = f"Competitors identified: {len(comp.get('competitors', []))}\n"
        comp_text += (
            f"Market positioning: {comp.get('overview', 'Analysis available in findings.')}"
        )
        sections.append(self._section("Competitive Landscape", comp_text))

        opps = findings.get("opportunities", [])
        risks = findings.get("risks", [])
        or_text = "**Opportunities:**\n" + "\n".join(f"- {o}" for o in opps[:5]) + "\n\n"
        or_text += "**Risks:**\n" + "\n".join(f"- {r}" for r in risks[:5])
        sections.append(self._section("Opportunities & Risks", or_text))

        return {
            "type": "executive",
            "title": f"Executive Brief: {findings.get('query', 'Research')}",
            "sections": sections,
            "generated_at": datetime.utcnow().isoformat(),
        }

    async def _build_risk_report(self, findings: dict) -> dict:
        sections = []

        regs = findings.get("regulatory", [])
        reg_text = "\n".join(
            f"- {r.get('title', r)} [Source: {r.get('source', 'N/A')}]" for r in regs[:20]
        )
        reg_text = reg_text or "No regulatory mentions detected."
        sections.append(self._section("Regulatory Mentions", reg_text))

        patents = findings.get("patents", [])
        patent_text = f"Patents analyzed: {len(patents)}\n"
        patent_text += "\n".join(
            f"- {p.get('title', 'Unknown')} ({p.get('year', 'N/A')}) - {p.get('jurisdiction', 'N/A')}"
            for p in patents[:15]
        )
        sections.append(self._section("Patent Landscape", patent_text))

        compliance = findings.get("compliance", [])
        comp_text = (
            "\n".join(f"- {c}" for c in compliance[:10])
            or "Review branch findings for compliance-related content."
        )
        sections.append(self._section("Compliance Recommendations", comp_text))

        return {
            "type": "risk",
            "title": f"Risk & Compliance Report: {findings.get('query', 'Research')}",
            "sections": sections,
            "generated_at": datetime.utcnow().isoformat(),
        }

    def _section(self, heading: str, content: str) -> dict:
        return {"heading": heading, "content": content}
