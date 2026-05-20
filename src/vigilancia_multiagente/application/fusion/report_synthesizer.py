import logging
import re
from typing import Any, cast
from uuid import UUID

from vigilancia_multiagente.application.evaluation.causal_timeline import CausalTimelineBuilder
from vigilancia_multiagente.application.evaluation.contradiction_analyzer import (
    ContradictionAnalyzer,
)
from vigilancia_multiagente.application.evaluation.finding_impact_scorer import FindingImpactScorer
from vigilancia_multiagente.application.evaluation.hype_detector import HypeDetector
from vigilancia_multiagente.application.evaluation.weak_signal_detector import WeakSignalDetector
from vigilancia_multiagente.application.fusion.adversarial_critic import AdversarialCritic
from vigilancia_multiagente.domain.ports.event_publisher import EventPublisher
from vigilancia_multiagente.domain.models import (
    BranchResult,
    FinalReport,
    Finding,
    Recommendation,
    SourceRef,
)
from vigilancia_multiagente.domain.system_base import MiniMaxMessage
from vigilancia_multiagente.domain.ports.llm_client import LLMClient
from vigilancia_multiagente.infra.prompts.loader import load_prompt

logger = logging.getLogger(__name__)


def _build_intelligence_sections(
    branch_results: list[BranchResult],
    recurring_entities: list[str] | None = None,
    recommendations: list[Recommendation] | None = None,
    source_scorer: object | None = None,
) -> str:
    """Genera secciones de inteligencia derivada (madurez tecnológica,
    contradicciones, señales débiles, trayectoria causal, ranking por impacto)
    de forma determinística.

    Se calcula siempre, independientemente de si hay LLM, porque la evidencia
    para estas secciones ya está en los branch_results.

    ``source_scorer`` (un :class:`SourceScorer` con el snapshot de
    source_trust ya cargado) inyecta la reputación de dominio aprendida en el
    ranking por impacto. Sin él, la autoridad es neutra.
    """
    all_findings = [f for result in branch_results for f in result.findings]

    contradiction_report = ContradictionAnalyzer().analyze(all_findings)
    weak_report = WeakSignalDetector().detect(branch_results, recurring_entities)
    timeline = CausalTimelineBuilder().build(branch_results)
    scored = FindingImpactScorer(cast(Any, source_scorer)).score(branch_results)
    maturity = HypeDetector.infer_from_branch_results(branch_results)

    parts: list[str] = []
    section = HypeDetector.render_section(maturity)
    if section:
        parts.append(section)
    if scored:
        parts.append("## Hallazgos priorizados por impacto")
        parts.append("")
        for item in scored[:10]:
            parts.append(
                f"- `{item.impact:.3f}` **{item.finding.topic}** — "
                f"{item.finding.statement} "
                f"(autoridad {item.authority}, novedad {item.novelty}, "
                f"convergencia {item.convergence})"
            )
        parts.append("")

    section = ContradictionAnalyzer.render_section(contradiction_report)
    if section:
        parts.append(section)
    section = WeakSignalDetector.render_section(weak_report)
    if section:
        parts.append(section)
    section = CausalTimelineBuilder.render_section(timeline)
    if section:
        parts.append(section)

    # Crítica adversarial: ataca lo ya ensamblado buscando afirmaciones sin
    # fuente, recomendaciones sin respaldo o disputas silenciadas.
    assembled = "\n".join(parts)
    critique = AdversarialCritic().critique(all_findings, cast(list[object], recommendations or []), assembled)
    section = AdversarialCritic.render_section(critique)
    if section:
        parts.append(section)

    return "\n".join(parts).strip()


class ReportSynthesizer:
    def __init__(
        self,
        event_publisher: EventPublisher | None = None,
        source_scorer: object | None = None,
    ) -> None:
        self._event_publisher = event_publisher
        self._source_scorer = source_scorer

    async def synthesize(
        self,
        session_id: UUID,
        branch_results: list[BranchResult],
        linked_findings: list[Finding],
        all_sources: list[SourceRef],
        llm: LLMClient | None = None,
    ) -> FinalReport:
        from vigilancia_multiagente.application.events.sse_publisher import SessionEvent, format_sse

        if self._event_publisher is not None:
            await self._event_publisher.publish(
                session_id,
                format_sse(
                    SessionEvent.now(
                        "FusionStarted",
                        session_id,
                        {"message": "Synthesizing cross-branch results..."},
                    )
                ),
            )
        source_scorer = self._source_scorer
        branch_sections = {
            result.branch_type.value.lower(): "\n".join(
                f"- {item.statement}" for item in result.findings
            )
            for result in branch_results
        }
        opportunities = [item.statement for item in linked_findings[:3]]
        recommendations = [
            {"text": f"Investigate {item.topic}", "priority": "medium"}
            for item in linked_findings[:3]
        ]
        intelligence = _build_intelligence_sections(
        branch_results,
        recommendations=cast(list[Any], recommendations),
        source_scorer=source_scorer,
    )

        if self._event_publisher is not None:
            await self._event_publisher.publish(
                session_id,
                format_sse(
                    SessionEvent.now(
                        "FusionProgress",
                        session_id,
                        {
                            "progress": 50,
                            "current_analysis": "cross-branch correlations",
                        },
                    )
                ),
            )

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
                response = await llm.complete(
                    messages=[MiniMaxMessage(role="user", content=prompt + "\n\n" + sections_text)]
                )
                data = json.loads(response.content)
                if "executive_summary" in data:
                    raw_recommendations = data.get("recommendations")
                    if not isinstance(raw_recommendations, list):
                        raw_recommendations = []
                    markdown = json.dumps(data, indent=2)
                    if intelligence:
                        markdown = f"{markdown}\n\n{intelligence}\n"
                    return FinalReport(
                        session_id=session_id,
                        markdown=markdown,
                        executive_summary=data.get("executive_summary", ""),
                        technical_section=data.get("technical_section", ""),
                        commercial_section=data.get("commercial_section", ""),
                        risk_section=data.get("risk_section", ""),
                        cross_analysis=data.get("cross_analysis", ""),
                        recommendations=[
                            Recommendation(text=r["text"], priority=r.get("priority", "medium"))
                            for r in raw_recommendations
                        ],
                        all_sources=all_sources,
                        total_sources_consulted=len(all_sources),
                        total_learnings=len(linked_findings),
                        confidence_score=float(data.get("confidence_score", 0.72)),
                    )
            except (json.JSONDecodeError, KeyError, TypeError, RuntimeError) as exc:
                logger.warning("MiniMax synthesis failed, using template fallback: %s", exc)

        markdown = _render_markdown(
            session_id=session_id,
            branch_sections=branch_sections,
            opportunities=opportunities,
            recommendations=recommendations,
            intelligence=intelligence,
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
    intelligence: str = "",
) -> str:
    lines = [f"# Final Report {session_id}", "", "## Branch Sections"]
    for branch, section in branch_sections.items():
        lines.append(f"### {branch}")
        lines.append(section or "- no findings")
    lines.extend(["", "## Opportunities"])
    lines.extend(f"- {item}" for item in opportunities)
    lines.extend(["", "## Recommendations"])
    lines.extend(f"- [{item['priority']}] {item['text']}" for item in recommendations)
    if intelligence:
        lines.extend(["", intelligence])
    return "\n".join(lines) + "\n"


def extract_section(markdown: str, section_name: str) -> str:
    for name in (section_name, section_name.lower()):
        match = re.search(
            rf"^#{{2,3}}\s+{re.escape(name)}\s*$(.*?)(?=^##\s|\Z)",
            markdown,
            re.MULTILINE | re.DOTALL,
        )
        if match:
            return match.group(1).strip()
    return ""
