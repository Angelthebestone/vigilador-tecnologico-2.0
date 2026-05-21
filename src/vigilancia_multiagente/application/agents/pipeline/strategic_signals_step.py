"""StrategicSignalsStep — spec 007 T119 (WS-D).

Step del pipeline que se inserta despues de DeepAnalysisStep. Ejecuta los 6
analizadores WS-D en paralelo y anade los resultados al BranchResult a traves
del ToolLoopContext.

Produce: ConvergenceCluster[], NarrativeShift[], IdeaLineage,
CollaborationNetwork, TalentMobility[], PatentingGap[].
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from vigilancia_multiagente.application.agents.pipeline.errors import (
    StepErrorSeverity,
    Workstream,
    add_step_error,
)
from vigilancia_multiagente.application.agents.pipeline.tool_loop_step import ToolLoopContext
from vigilancia_multiagente.application.evaluation.analytics.agglomerative_convergence import (
    SklearnAgglomerativeConvergenceDetector,
)
from vigilancia_multiagente.application.evaluation.analytics.vader_narrative_shift import (
    VaderNarrativeShiftDetector,
)
from vigilancia_multiagente.application.evaluation.ws_d.collaboration_network_builder import (
    CollaborationNetworkBuilderImpl,
)
from vigilancia_multiagente.application.evaluation.ws_d.patenting_gap_analyzer import (
    PatentingGapAnalyzerImpl,
)
from vigilancia_multiagente.application.evaluation.ws_d.talent_mobility_analyzer import (
    TalentMobilityAnalyzerImpl,
)
from vigilancia_multiagente.domain.evaluation_entities import (
    CollaborationNetwork,
    ConvergenceCluster,
    IdeaLineage,
    NarrativeShift,
    PatentingGap,
    TalentMobility,
)
from vigilancia_multiagente.domain.ports.collaboration_network import (
    CollaborationNetworkBuilder,
)
from vigilancia_multiagente.domain.ports.idea_lineage import IdeaLineageTracer
from vigilancia_multiagente.domain.ports.patenting_gap import PatentingGapAnalyzer
from vigilancia_multiagente.domain.ports.talent_mobility import TalentMobilityAnalyzer

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class StrategicSignalsOutput:
    convergence_clusters: list[ConvergenceCluster] = field(default_factory=list)
    narrative_shifts: list[NarrativeShift] = field(default_factory=list)
    idea_lineage: IdeaLineage | None = None
    collaboration_network: CollaborationNetwork | None = None
    talent_mobility: list[TalentMobility] = field(default_factory=list)
    patenting_gaps: list[PatentingGap] = field(default_factory=list)


class StrategicSignalsStep:
    """Ejecuta los 6 detectores WS-D y produce las senales estrategicas."""

    def __init__(
        self,
        convergence_detector: SklearnAgglomerativeConvergenceDetector | None = None,
        narrative_detector: VaderNarrativeShiftDetector | None = None,
        lineage_tracer: IdeaLineageTracer | None = None,
        collaboration_builder: CollaborationNetworkBuilder | None = None,
        mobility_analyzer: TalentMobilityAnalyzer | None = None,
        patenting_analyzer: PatentingGapAnalyzer | None = None,
    ) -> None:
        self._convergence_detector = convergence_detector
        self._narrative_detector = narrative_detector
        self._lineage_tracer = lineage_tracer
        self._collaboration_builder = collaboration_builder
        self._mobility_analyzer = mobility_analyzer
        self._patenting_analyzer = patenting_analyzer

    async def run(self, ctx: ToolLoopContext) -> ToolLoopContext:
        if not ctx.executions:
            return ctx

        output = await self._run_all(ctx)
        _attach_ws_d_signals(ctx, output)
        return ctx

    async def _run_all(self, ctx: ToolLoopContext) -> StrategicSignalsOutput:
        output = StrategicSignalsOutput()

        if self._convergence_detector:
            output.convergence_clusters = await self._safe_call(
                "convergence",
                self._detect_convergence(ctx),
                ctx,
            )
        if self._narrative_detector:
            output.narrative_shifts = await self._safe_call(
                "narrative",
                self._detect_narrative(ctx),
                ctx,
            )
        if self._lineage_tracer:
            output.idea_lineage = await self._safe_call(
                "lineage",
                self._trace_lineage(ctx),
                ctx,
            )
        if self._collaboration_builder:
            output.collaboration_network = await self._safe_call(
                "collaboration",
                self._build_collaboration_network(ctx),
                ctx,
            )
        if self._mobility_analyzer:
            output.talent_mobility = await self._safe_call(
                "mobility",
                self._analyze_mobility(ctx),
                ctx,
            )
        if self._patenting_analyzer:
            output.patenting_gaps = await self._safe_call(
                "patenting",
                self._analyze_patenting_gaps(ctx),
                ctx,
            )

        return output

    async def _detect_convergence(self, ctx: ToolLoopContext) -> list[ConvergenceCluster]:
        embeddings: list[tuple[str, list[float], datetime]] = []
        for execution in ctx.executions:
            payload = getattr(execution, "payload", {})
            if isinstance(payload, dict):
                query = str(payload.get("query", ""))
                vec = payload.get("embedding", payload.get("vector"))
                if isinstance(vec, list) and all(isinstance(v, (int, float)) for v in vec):
                    embeddings.append((query, [float(v) for v in vec], datetime.now()))
        return await self._convergence_detector.detect(embeddings) if embeddings else []

    async def _detect_narrative(self, ctx: ToolLoopContext) -> list[NarrativeShift]:
        timeline: list[tuple[datetime, str]] = []
        for iteration in ctx.iterations:
            src_text = getattr(iteration, "query", "")
            if src_text:
                timeline.append((datetime.now(), src_text))
            for finding in getattr(iteration, "findings", []):
                statement = getattr(finding, "statement", "")
                if statement:
                    timeline.append((datetime.now(), statement))
        topic = ctx.seed_query or "general"
        return await self._narrative_detector.detect(topic, timeline) if timeline else []

    async def _trace_lineage(self, ctx: ToolLoopContext) -> IdeaLineage | None:
        sources = _get_sources_from_ctx(ctx)
        idea = ctx.seed_query or "general"
        return await self._lineage_tracer.trace(idea, sources)

    async def _build_collaboration_network(self, ctx: ToolLoopContext) -> CollaborationNetwork | None:
        sources = _get_sources_from_ctx(ctx)
        return await self._collaboration_builder.build(sources)

    async def _analyze_mobility(self, ctx: ToolLoopContext) -> list[TalentMobility]:
        author_ids: list[str] = []
        for iteration in ctx.iterations:
            for finding in getattr(iteration, "findings", []):
                for tag in getattr(finding, "tags", []):
                    if tag not in author_ids:
                        author_ids.append(tag)
        return await self._mobility_analyzer.analyze(author_ids[:10]) if author_ids else []

    async def _analyze_patenting_gaps(self, ctx: ToolLoopContext) -> list[PatentingGap]:
        subdomains: list[str] = []
        for finding in _get_findings_from_ctx(ctx):
            for tag in getattr(finding, "tags", []):
                if tag not in subdomains:
                    subdomains.append(tag)
        if not subdomains and ctx.seed_query:
            subdomains = [ctx.seed_query]
        return await self._patenting_analyzer.analyze(subdomains[:5]) if subdomains else []

    async def _safe_call(
        self, step_name: str, coro: Any, ctx: ToolLoopContext
    ) -> Any:
        try:
            return await coro
        except Exception as exc:
            add_step_error(
                ctx.errors,
                workstream=Workstream.WS_D,
                step_name=f"StrategicSignalsStep.{step_name}",
                exc=exc,
                severity=StepErrorSeverity.WARNING,
            )
            return None


def _get_findings_from_ctx(ctx: ToolLoopContext) -> list:
    findings: list = []
    for iteration in ctx.iterations:
        findings.extend(getattr(iteration, "findings", []))
    br = getattr(ctx, "branch_result", None)
    if br is not None:
        findings.extend(getattr(br, "findings", []))
    return findings


def _get_sources_from_ctx(ctx: ToolLoopContext) -> list:
    sources: list = []
    for execution in ctx.executions:
        payload = getattr(execution, "payload", {})
        if isinstance(payload, dict):
            url = payload.get("url") or ""
        else:
            url = ""
        if url:
            from uuid import uuid4
            from vigilancia_multiagente.domain.models import SourceRef, BranchType

            sources.append(
                SourceRef(
                    id=uuid4(),
                    session_id=ctx.session.id,
                    url=str(url),
                    provider=str(payload.get("provider", "")),
                    branch_type=ctx.branch_config.branch_type,
                    accessed_at=datetime.now(),
                )
            )
    return sources


def _attach_ws_d_signals(ctx: ToolLoopContext, output: StrategicSignalsOutput) -> None:
    ctx.ws_d_signals = output
