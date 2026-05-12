from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from vigilancia_multiagente.domain.models import BranchResult, Finding, SourceRef
from vigilancia_multiagente.infra.llm.minimax_client import MiniMaxClient, MiniMaxMessage
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
        findings: list[Finding],
        sources: list[SourceRef],
        llm: MiniMaxClient | None = None,
    ) -> SynthesizedReport:
        branch_sections = {
            result.branch_type.value.lower(): "\n".join(f"- {item.statement}" for item in result.findings)
            for result in branch_results
        }
        opportunities = [item.statement for item in findings[:3]]
        recommendations = [
            {"text": f"Investigate {item.topic}", "priority": "medium"}
            for item in findings[:3]
        ]

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
                    return SynthesizedReport(
                        session_id=session_id,
                        generated_at=data.get("generated_at", datetime.now(UTC).isoformat()),
                        executive_summary=data.get("executive_summary", ""),
                        branch_sections=data.get("branch_sections", branch_sections),
                        contradictions=data.get("contradictions", []),
                        opportunities=data.get("opportunities", opportunities),
                        recommendations=data.get("recommendations", recommendations),
                        all_source_ids=[str(source.id) for source in sources],
                        markdown=_render_markdown(session_id, branch_sections, opportunities, recommendations),
                    )
            except (json.JSONDecodeError, KeyError, TypeError, RuntimeError):
                pass

        markdown = _render_markdown(
            session_id=session_id,
            branch_sections=branch_sections,
            opportunities=opportunities,
            recommendations=recommendations,
        )
        return SynthesizedReport(
            session_id=session_id,
            generated_at=datetime.now(UTC).isoformat(),
            executive_summary="Multi-branch analysis completed with traceable evidence.",
            branch_sections=branch_sections,
            opportunities=opportunities,
            recommendations=recommendations,
            all_source_ids=[str(source.id) for source in sources],
            markdown=markdown,
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

