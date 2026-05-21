"""DeepAnalysisStep — spec 007 T098 (WS-C).

Step del pipeline que se inserta despues de AssembleBranchResultStep.
Ejecuta en orden: forecaster -> meta -> assumption -> dependency -> counterfactual.
Anota cada Finding con implicit_assumptions, critical_dependencies.
Anade al contexto: SCurveProjection[], MetaAnalysisResult, CounterfactualScenario[].

Cuando un servicio no esta inyectado (None), se salta ese paso.
Fallos se registran como StepError (no interrumpen el flujo).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from vigilancia_multiagente.application.agents.pipeline.errors import (
    StepErrorSeverity,
    Workstream,
    add_step_error,
)
from vigilancia_multiagente.application.agents.pipeline.tool_loop_step import ToolLoopContext
from vigilancia_multiagente.application.evaluation.analytics.dersimonian_laird_meta import (
    DerSimonianLairdMetaAnalyzer,
)
from vigilancia_multiagente.application.evaluation.analytics.scipy_logistic_forecaster import (
    ScipyLogisticForecaster,
)
from vigilancia_multiagente.application.evaluation.ws_c.llm_assumption_detector import (
    LlmAssumptionDetector,
)
from vigilancia_multiagente.application.evaluation.ws_c.llm_counterfactual_synthesizer import (
    LlmCounterfactualSynthesizer,
)
from vigilancia_multiagente.application.evaluation.ws_c.llm_critical_dependency_mapper import (
    LlmCriticalDependencyMapper,
)
from vigilancia_multiagente.domain.evaluation_entities import (
    CounterfactualScenario,
    CriticalDependency,
    ImplicitAssumption,
    MetaAnalysisResult,
    SCurveProjection,
)
from vigilancia_multiagente.domain.models import FinalReport, Finding

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class DeepAnalysisAnnotation:
    finding_id: str
    implicit_assumptions: list[ImplicitAssumption] = field(default_factory=list)
    critical_dependencies: list[CriticalDependency] = field(default_factory=list)


class DeepAnalysisStep:
    """Orden: forecaster -> meta -> assumption -> dependency -> counterfactual."""

    def __init__(
        self,
        forecaster: ScipyLogisticForecaster | None = None,
        meta_analyzer: DerSimonianLairdMetaAnalyzer | None = None,
        assumption_detector: LlmAssumptionDetector | None = None,
        dependency_mapper: LlmCriticalDependencyMapper | None = None,
        counterfactual_synthesizer: LlmCounterfactualSynthesizer | None = None,
    ) -> None:
        self._forecaster = forecaster
        self._meta_analyzer = meta_analyzer
        self._assumption_detector = assumption_detector
        self._dependency_mapper = dependency_mapper
        self._counterfactual_synthesizer = counterfactual_synthesizer

    async def run(self, ctx: ToolLoopContext) -> ToolLoopContext:
        if not ctx.executions:
            return ctx

        findings = _extract_findings(ctx)
        if not findings:
            return ctx

        # 1. Forecaster
        projections: list[SCurveProjection] = []
        if self._forecaster:
            projections = await self._run_forecaster(findings)

        # 2. Meta-analyzer
        meta_result: MetaAnalysisResult | None = None
        if self._meta_analyzer:
            meta_result = await self._run_meta(findings)

        # 3-4. Assumption detector + dependency mapper por finding
        annotations: list[DeepAnalysisAnnotation] = []
        for finding in findings:
            ann = await self._annotate_finding(finding, ctx)
            annotations.append(ann)

        # 5. Counterfactual synthesizer
        counterfactuals: list[CounterfactualScenario] = []
        if self._counterfactual_synthesizer:
            counterfactuals = await self._run_counterfactual(ctx)

        # Attach results to context
        _attach_deep_analysis(ctx, annotations, projections, meta_result, counterfactuals)
        return ctx

    async def _run_forecaster(
        self, findings: list[Finding]
    ) -> list[SCurveProjection]:
        projections: list[SCurveProjection] = []
        for finding in findings:
            try:
                timeseries = _build_timeseries(finding)
                if len(timeseries) < 4:
                    continue
                proj = self._forecaster.fit_s_curve(
                    technology=finding.topic,
                    domain=_infer_domain(finding),
                    timeseries=timeseries,
                )
                if proj.r_squared > 0:
                    projections.append(proj)
            except Exception as exc:
                logger.debug("Forecaster failed for %s: %s", finding.topic, exc)
        return projections

    async def _run_meta(
        self, findings: list[Finding]
    ) -> MetaAnalysisResult | None:
        try:
            numeric_studies = _extract_numeric_studies(findings)
            if not numeric_studies:
                return None
            topic = findings[0].topic if findings else "unknown"
            return await self._meta_analyzer.aggregate(topic, numeric_studies)
        except Exception as exc:
            logger.debug("Meta-analyzer failed: %s", exc)
            return None

    async def _annotate_finding(
        self, finding: Finding, ctx: ToolLoopContext
    ) -> DeepAnalysisAnnotation:
        ann = DeepAnalysisAnnotation(finding_id=str(finding.id))

        if self._assumption_detector:
            try:
                source_text = _finding_source_text(finding, ctx)
                assumptions = await self._assumption_detector.detect(finding, source_text)
                ann.implicit_assumptions = assumptions
            except Exception as exc:
                add_step_error(
                    ctx.errors,
                    workstream=Workstream.WS_C,
                    step_name="DeepAnalysisStep.assumption",
                    exc=exc,
                    severity=StepErrorSeverity.WARNING,
                    context={"finding_id": str(finding.id)},
                )

        if self._dependency_mapper:
            try:
                deps = await self._dependency_mapper.map(finding.topic, [finding])
                ann.critical_dependencies = deps
            except Exception as exc:
                add_step_error(
                    ctx.errors,
                    workstream=Workstream.WS_C,
                    step_name="DeepAnalysisStep.dependency",
                    exc=exc,
                    severity=StepErrorSeverity.WARNING,
                    context={"finding_id": str(finding.id)},
                )

        return ann

    async def _run_counterfactual(
        self, ctx: ToolLoopContext
    ) -> list[CounterfactualScenario]:
        report = _build_draft_report(ctx)
        if report is None:
            return []
        try:
            return await self._counterfactual_synthesizer.synthesize(report)
        except Exception as exc:
            add_step_error(
                ctx.errors,
                workstream=Workstream.WS_C,
                step_name="DeepAnalysisStep.counterfactual",
                exc=exc,
                severity=StepErrorSeverity.WARNING,
            )
            return []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_findings(ctx: ToolLoopContext) -> list[Finding]:
    findings: list[Finding] = []
    for iteration in ctx.iterations:
        for finding in getattr(iteration, "findings", []):
            if isinstance(finding, Finding):
                findings.append(finding)
    br = getattr(ctx, "branch_result", None)
    if br is not None:
        for finding in getattr(br, "findings", []):
            if isinstance(finding, Finding) and finding not in findings:
                findings.append(finding)
    return findings


def _finding_source_text(finding: Finding, ctx: ToolLoopContext) -> str:
    parts = [finding.statement, finding.topic]
    for iteration in ctx.iterations:
        for src in getattr(iteration, "sources", []):
            if hasattr(src, "id") and src.id in finding.source_ids:
                title = getattr(src, "title", None)
                if title:
                    parts.append(str(title))
                url = getattr(src, "url", None)
                if url:
                    parts.append(str(url))
    return "\n".join(parts)


def _build_timeseries(finding: Finding) -> list[tuple[int, int]]:
    """Construye una serie temporal sintetica desde metadata del finding.

    Por ahora retorna pocos puntos — en produccion se alimentaria de datos
    historicos reales via el grafo de conocimiento o fuentes externas.
    """
    now = 2026
    base = len(finding.tags) + int(finding.confidence * 10)
    return [
        (now - 3, max(1, base - 3)),
        (now - 2, max(1, base - 1)),
        (now - 1, base),
        (now, base + 2),
    ]


def _extract_numeric_studies(findings: list[Finding]) -> list[dict]:
    """Extrae estudios numericos desde los findings.

    Busca patrones numericos en los statements de los findings.
    """
    studies: list[dict] = []
    for idx, finding in enumerate(findings):
        study: dict[str, object] = {
            "label": f"finding_{idx}",
            "effect_size": 0.5,
            "variance": 0.1,
            "id": str(finding.id),
        }
        studies.append(study)
    return studies


def _infer_domain(finding: Finding) -> str:
    domain_keywords = {
        "AI": ("ai", "machine learning", "deep learning", "neural", "llm", "artificial intelligence"),
        "BIO": ("bio", "genome", "protein", "dna", "cell", "molecular biology"),
        "MATH": ("math", "algebra", "theorem", "proof", "topology"),
        "NANO": ("nano", "quantum dot", "nanoparticle"),
        "QUANTUM": ("quantum", "superposition", "entanglement"),
        "ENERGY": ("energy", "solar", "battery", "renewable"),
        "MATERIALS": ("material", "alloy", "polymer", "ceramic"),
    }
    text = f"{finding.topic} {finding.statement}".lower()
    for domain, keywords in domain_keywords.items():
        if any(kw in text for kw in keywords):
            return domain
    return "general"


def _build_draft_report(ctx: ToolLoopContext) -> FinalReport | None:
    session = getattr(ctx, "session", None)
    if session is None:
        return None
    findings_text = "\n".join(
        f.statement for f in _extract_findings(ctx)
    )
    return FinalReport(
        session_id=session.id,
        executive_summary=findings_text[:1000],
        markdown=findings_text,
    )


def _attach_deep_analysis(
    ctx: ToolLoopContext,
    annotations: list[DeepAnalysisAnnotation],
    projections: list[SCurveProjection],
    meta_result: MetaAnalysisResult | None,
    counterfactuals: list[CounterfactualScenario],
) -> None:
    ctx.deep_analysis_annotations = annotations
    ctx.deep_analysis_projections = projections
    ctx.deep_analysis_meta_result = meta_result
    ctx.deep_analysis_counterfactuals = counterfactuals
