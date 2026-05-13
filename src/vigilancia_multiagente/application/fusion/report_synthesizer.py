import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from vigilancia_multiagente.domain.models import BranchResult, Finding, FinalReport, Recommendation, SourceRef
from vigilancia_multiagente.domain.system_base import MiniMaxMessage
from vigilancia_multiagente.infra.llm.minimax_client import MiniMaxClient
from vigilancia_multiagente.infra.prompts.loader import load_prompt


@dataclass(slots=True)
class SynthesizedReport:
    session_id: UUID
    generated_at: str
    executive_summary: str
    branch_sections: dict[str, str]
    contradictions: list[str] = field(default_factory=list)
    opportunities: list[str] = field(default_factory=list)
    recommendations: list[dict[str, str]] = field(default_factory=list)
    all_source_ids: list[str] = field(default_factory=list)
    markdown: str = ""


class ReportSynthesizer:
    async def synthesize(
        self,
        session_id: UUID,
        branch_results: list[BranchResult],
        linked_findings: list[Finding],
        all_sources: list[SourceRef],
        llm: MiniMaxClient | None = None,
    ) -> FinalReport:
        from vigilancia_multiagente.api.dependencies import event_log
        from vigilancia_multiagente.application.events.sse_publisher import SessionEvent, format_sse

        event_log[str(session_id)].append(format_sse(SessionEvent.now("FusionStarted", session_id, {
            "message": "Synthesizing cross-branch results...",
        })))
        branch_sections = {
            result.branch_type.value.lower(): "\n".join(f"- {item.statement}" for item in result.findings)
            for result in branch_results
        }
        opportunities = [item.statement for item in linked_findings[:3]]
        recommendations = [
            {"text": f"Investigate {item.topic}", "priority": "medium"}
            for item in linked_findings[:3]
        ]

        event_log[str(session_id)].append(format_sse(SessionEvent.now("FusionProgress", session_id, {
            "progress": 50,
            "current_analysis": "cross-branch correlations",
        })))

        if llm is not None:
            import json

            try:
                sections_text = "\n\n".join(
                    f"=== {key} ===\n{val}" for key, val in branch_sections.items()
                )
                prompt = load_prompt("orchestration/synthesis").format(
                    avances=branch_sections.get("avances", ""),
                    comercial=branch_sections.get("comercial", ""),
                    riesgo=branch_sections.get("riesgo", ""),
                    pi_normativa=branch_sections.get("pi_normativa", ""),
                    competitivo=branch_sections.get("competitivo", ""),
                    oportunidades=branch_sections.get("oportunidades", ""),
                )
                response = await llm.complete(messages=[MiniMaxMessage(role="user", content=prompt + "\n\n" + sections_text)])
                data = json.loads(response.content)
                if "executive_summary" in data:
                    return FinalReport(
                        session_id=session_id,
                        markdown=json.dumps(data, indent=2),
                        executive_summary=data.get("executive_summary", ""),
                        technical_section=data.get("technical_section", ""),
                        commercial_section=data.get("commercial_section", ""),
                        risk_section=data.get("risk_section", ""),
                        cross_analysis=data.get("cross_analysis", ""),
                        recommendations=[
                            Recommendation(text=r["text"], priority=r.get("priority", "medium"))
                            for r in (data.get("recommendations", []) if isinstance(data.get("recommendations"), list) else [])
                        ],
                        all_sources=all_sources,
                        total_sources_consulted=len(all_sources),
                        total_learnings=len(linked_findings),
                        confidence_score=float(data.get("confidence_score", 0.72)),
                    )
            except (json.JSONDecodeError, KeyError, TypeError, RuntimeError):
                pass

        markdown = _render_markdown(
            session_id=session_id,
            branch_sections=branch_sections,
            opportunities=opportunities,
            recommendations=recommendations,
        )
        return FinalReport(
            session_id=session_id,
            markdown=markdown,
            executive_summary=extract_section(markdown, "Resumen Ejecutivo"),
            technical_section=extract_section(markdown, "Avances"),
            commercial_section=extract_section(markdown, "Comercial"),
            risk_section=extract_section(markdown, "Riesgo"),
            cross_analysis="",
            recommendations=[],
            all_sources=all_sources,
            total_sources_consulted=len(all_sources),
            total_learnings=len(linked_findings),
            confidence_score=0.72,
        )


def _render_markdown(
    session_id: UUID,
    branch_sections: dict[str, str],
    opportunities: list[str],
    recommendations: list[dict[str, str]],
) -> str:
    lines = [f"# Final Report {session_id}", "", "## Branch Sections"]
    for branch, section in branch_sections.items():
        lines.append(f"### {branch}")
        lines.append(section or "- no findings")
    lines.extend(["", "## Opportunities"])
    lines.extend(f"- {item}" for item in opportunities)
    lines.extend(["", "## Recommendations"])
    lines.extend(f"- [{item['priority']}] {item['text']}" for item in recommendations)
    return "\n".join(lines) + "\n"


def extract_section(markdown: str, section_name: str) -> str:
    for name in (section_name, section_name.lower()):
        match = re.search(
            rf"^#{{2,3}}\s+{re.escape(name)}\s*$(.*?)(?=^#|\Z)",
            markdown,
            re.MULTILINE | re.DOTALL,
        )
        if match:
            return match.group(1).strip()
    return ""

