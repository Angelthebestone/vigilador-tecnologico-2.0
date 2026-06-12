"""DataIntelligenceStep — spec 007 T076.

Step concreto del pipeline que ejecuta WS-B como sub-fase post-extraccion.
Orden: hybrid_search -> dedup -> schema_validate -> authenticity -> multilingual -> consensus_dispute.
Fallos registrados como StepError sin interrumpir.
"""

from __future__ import annotations

import logging

from vigilancia_multiagente.application.agents.pipeline.errors import (
    StepErrorSeverity,
    Workstream,
    add_step_error,
)
from vigilancia_multiagente.application.agents.pipeline.tool_loop_step import ToolLoopContext
from vigilancia_multiagente.application.evaluation.authenticity.local_perplexity_detector import (
    LocalPerplexityAuthenticityDetector,
)
from vigilancia_multiagente.application.evaluation.ws_b.consensus_dispute_mapper import (
    ConsensusDisputeMapperImpl,
)
from vigilancia_multiagente.application.evaluation.ws_b.embedding_dedup import (
    EmbeddingBasedDeduplicator,
)
from vigilancia_multiagente.application.evaluation.ws_b.llm_multilingual import (
    LlmMultilingualNormalizer,
)
from vigilancia_multiagente.application.evaluation.ws_b.pydantic_schema_registry import (
    PydanticExtractionSchemaRegistry,
)
from vigilancia_multiagente.domain.evaluation_entities import (
    ContentAuthenticitySignal,
    DedupedSource,
)
from vigilancia_multiagente.domain.models import SourceRef
from vigilancia_multiagente.domain.ports.hybrid_search import HybridSearchEngine

logger = logging.getLogger(__name__)


class DataIntelligenceStep:
    def __init__(
        self,
        hybrid_search: HybridSearchEngine | None = None,
        deduplicator: EmbeddingBasedDeduplicator | None = None,
        schema_registry: PydanticExtractionSchemaRegistry | None = None,
        multilingual: LlmMultilingualNormalizer | None = None,
        authenticity_detector: LocalPerplexityAuthenticityDetector | None = None,
        consensus_dispute: ConsensusDisputeMapperImpl | None = None,
    ) -> None:
        self._hybrid_search = hybrid_search
        self._deduplicator = deduplicator
        self._schema_registry = schema_registry
        self._multilingual = multilingual
        self._authenticity_detector = authenticity_detector
        self._consensus_dispute = consensus_dispute

    async def run(self, ctx: ToolLoopContext) -> ToolLoopContext:
        if not ctx.executions:
            return ctx

        sources = _collect_sources(ctx)
        if not sources:
            return ctx

        ctx = await self._run_hybrid_search(ctx, sources)
        ctx = await self._run_dedup(ctx, sources)
        ctx = await self._run_schema_validate(ctx)
        ctx = await self._run_authenticity(ctx, sources)
        ctx = await self._run_multilingual(ctx, sources)
        return await self._run_consensus_dispute(ctx)

    async def _run_hybrid_search(
        self, ctx: ToolLoopContext, sources: list[SourceRef]
    ) -> ToolLoopContext:
        if self._hybrid_search is None:
            return ctx
        query_text = ctx.seed_query or str(getattr(ctx, "query", ""))
        if not query_text:
            return ctx
        try:
            from vigilancia_multiagente.domain.evaluation_entities import (
                HybridSearchQuery,
            )

            hq = HybridSearchQuery(text=query_text, vector=[], keywords=query_text.lower().split())
            ranked = await self._hybrid_search.search(hq, sources)
            _annotate_ranking(ctx, ranked)
        except Exception as exc:
            add_step_error(
                ctx.errors,
                workstream=Workstream.WS_B,
                step_name="DataIntelligenceStep.hybrid_search",
                exc=exc,
                severity=StepErrorSeverity.WARNING,
            )
        return ctx

    async def _run_dedup(self, ctx: ToolLoopContext, sources: list[SourceRef]) -> ToolLoopContext:
        if self._deduplicator is None:
            return ctx
        try:
            groups = await self._deduplicator.deduplicate(sources)
            ctx.branch_result = getattr(ctx, "branch_result", None)
            _annotate_dedup(ctx, groups)
        except Exception as exc:
            add_step_error(
                ctx.errors,
                workstream=Workstream.WS_B,
                step_name="DataIntelligenceStep.dedup",
                exc=exc,
                severity=StepErrorSeverity.WARNING,
            )
        return ctx

    async def _run_schema_validate(self, ctx: ToolLoopContext) -> ToolLoopContext:
        if self._schema_registry is None:
            return ctx
        for execution in getattr(ctx, "executions", []):
            payload = getattr(execution, "payload", None)
            if not isinstance(payload, dict):
                continue
            try:
                schema = self._schema_registry.get_schema("news", "general")
                validated = self._schema_registry.validate(payload, schema)
                execution.payload = validated
            except Exception as exc:
                add_step_error(
                    ctx.errors,
                    workstream=Workstream.WS_B,
                    step_name="DataIntelligenceStep.schema_validate",
                    exc=exc,
                    severity=StepErrorSeverity.WARNING,
                )
        return ctx

    async def _run_authenticity(
        self, ctx: ToolLoopContext, sources: list[SourceRef]
    ) -> ToolLoopContext:
        if self._authenticity_detector is None:
            return ctx
        signals: list[ContentAuthenticitySignal] = []
        for src in sources:
            try:
                raw_text = src.title or src.url
                signal = await self._authenticity_detector.analyze(src, raw_text, raw_freshness=1.0)
                signals.append(signal)
            except Exception as exc:
                add_step_error(
                    ctx.errors,
                    workstream=Workstream.WS_B,
                    step_name="DataIntelligenceStep.authenticity",
                    exc=exc,
                    severity=StepErrorSeverity.WARNING,
                )
        ctx._authenticity_signals = signals
        return ctx

    async def _run_multilingual(
        self, ctx: ToolLoopContext, sources: list[SourceRef]
    ) -> ToolLoopContext:
        if self._multilingual is None:
            return ctx
        try:
            dist = await self._multilingual.language_distribution(sources)
            ctx._language_distribution = dist
        except Exception as exc:
            add_step_error(
                ctx.errors,
                workstream=Workstream.WS_B,
                step_name="DataIntelligenceStep.multilingual",
                exc=exc,
                severity=StepErrorSeverity.WARNING,
            )
        return ctx

    async def _run_consensus_dispute(self, ctx: ToolLoopContext) -> ToolLoopContext:
        if self._consensus_dispute is None:
            return ctx
        findings = _collect_findings(ctx)
        if not findings:
            return ctx
        try:
            maps = await self._consensus_dispute.build(findings)
            ctx._consensus_dispute_maps = maps
        except Exception as exc:
            add_step_error(
                ctx.errors,
                workstream=Workstream.WS_B,
                step_name="DataIntelligenceStep.consensus_dispute",
                exc=exc,
                severity=StepErrorSeverity.WARNING,
            )
        return ctx


def _collect_sources(ctx: ToolLoopContext) -> list[SourceRef]:
    sources: list[SourceRef] = []
    if ctx.sources:
        sources.extend(ctx.sources)
    br = getattr(ctx, "branch_result", None)
    if br is not None:
        sources.extend(getattr(br, "sources", []))
    for iteration in getattr(ctx, "iterations", []):
        sources.extend(getattr(iteration, "sources", []))
    return sources


def _collect_findings(ctx: ToolLoopContext) -> list:
    findings: list = []
    br = getattr(ctx, "branch_result", None)
    if br is not None:
        findings.extend(getattr(br, "findings", []))
    for iteration in getattr(ctx, "iterations", []):
        findings.extend(getattr(iteration, "findings", []))
    return findings


def _annotate_ranking(ctx: ToolLoopContext, ranked: list[SourceRef]) -> None:
    if not hasattr(ctx, "_hybrid_ranking") or ctx._hybrid_ranking is None:
        ctx._hybrid_ranking = {}
    for rank, src in enumerate(ranked):
        ctx._hybrid_ranking[str(src.id)] = rank


def _annotate_dedup(ctx: ToolLoopContext, groups: list[DedupedSource]) -> None:
    if not hasattr(ctx, "_dedup_groups") or ctx._dedup_groups is None:
        ctx._dedup_groups = []
    ctx._dedup_groups.extend(groups)
