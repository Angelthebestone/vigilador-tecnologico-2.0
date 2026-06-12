"""SourceQualityStep — spec 007 T056.

Step del pipeline que enriquece cada Finding en el contexto con anotaciones
de calidad de fuente: reputacion de autor, conflicto de intereses,
validacion externa, estado de retractacion, reproducibilidad y peso de
decaimiento temporal.

Se ejecuta antes de AssembleBranchResultStep. Fallos en adapters externos
se registran como StepError (no interrumpen el flujo).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from vigilancia_multiagente.application.agents.pipeline.errors import (
    StepErrorSeverity,
    Workstream,
    add_step_error,
)
from vigilancia_multiagente.application.agents.pipeline.tool_loop_step import ToolLoopContext
from vigilancia_multiagente.domain.evaluation_entities import (
    AuthorReputation,
    ClaimExternalValidation,
    ConflictOfInterest,
    ReproducibilityScore,
    RetractionRecord,
)
from vigilancia_multiagente.domain.models import Finding, SourceRef
from vigilancia_multiagente.domain.ports.author_reputation import AuthorReputationGateway
from vigilancia_multiagente.domain.ports.conflict_of_interest import ConflictOfInterestAnalyzer
from vigilancia_multiagente.domain.ports.fact_checker import ExternalFactChecker
from vigilancia_multiagente.domain.ports.reproducibility import ReproducibilityChecker
from vigilancia_multiagente.domain.ports.retraction_monitor import RetractionMonitor
from vigilancia_multiagente.domain.ports.temporal_decay import TemporalDecayConfigStore

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SourceQualityAnnotation:
    finding_id: str
    author_reputation: AuthorReputation | None = None
    conflict_of_interest: ConflictOfInterest | None = None
    claim_external_validation: ClaimExternalValidation | None = None
    retraction_status: RetractionRecord | None = None
    reproducibility_score: ReproducibilityScore | None = None
    decay_weight: float = 1.0


class SourceQualityStep:
    def __init__(
        self,
        author_reputation_gateway: AuthorReputationGateway | None = None,
        conflict_analyzer: ConflictOfInterestAnalyzer | None = None,
        fact_checker: ExternalFactChecker | None = None,
        retraction_monitor: RetractionMonitor | None = None,
        reproducibility_checker: ReproducibilityChecker | None = None,
        temporal_decay_store: TemporalDecayConfigStore | None = None,
    ) -> None:
        self._author_gateway = author_reputation_gateway
        self._conflict_analyzer = conflict_analyzer
        self._fact_checker = fact_checker
        self._retraction_monitor = retraction_monitor
        self._reproducibility_checker = reproducibility_checker
        self._temporal_decay_store = temporal_decay_store

    async def run(self, ctx: ToolLoopContext) -> ToolLoopContext:
        if not ctx.executions:
            return ctx

        findings = _extract_findings(ctx)
        if not findings:
            return ctx

        annotations: list[SourceQualityAnnotation] = []
        for finding in findings:
            ann = await self._annotate_finding(finding, ctx)
            annotations.append(ann)

        ctx.branch_result = getattr(ctx, "branch_result", None)
        _attach_annotations(ctx, annotations)
        return ctx

    async def _annotate_finding(
        self, finding: Finding, ctx: ToolLoopContext
    ) -> SourceQualityAnnotation:
        ann = SourceQualityAnnotation(finding_id=str(finding.id))

        if self._author_gateway:
            ann.author_reputation = await self._safe_call(
                "author_reputation", self._author_gateway.lookup(str(finding.id)), ctx
            )

        source_ref = _find_source(ctx, finding)
        if source_ref and self._conflict_analyzer:
            ann.conflict_of_interest = await self._safe_call(
                "conflict_of_interest", self._conflict_analyzer.analyze(source_ref), ctx
            )

        if self._fact_checker:
            ann.claim_external_validation = await self._safe_call(
                "fact_checker", self._fact_checker.verify(finding.statement), ctx
            )

        if self._retraction_monitor and source_ref:
            doi = _extract_doi(source_ref.url)
            if doi:
                ann.retraction_status = await self._safe_call(
                    "retraction_monitor", self._retraction_monitor.is_retracted(doi), ctx
                )

        if self._reproducibility_checker:
            ann.reproducibility_score = await self._safe_call(
                "reproducibility", self._reproducibility_checker.score(finding), ctx
            )

        if self._temporal_decay_store and source_ref:
            domain = _infer_domain(finding)
            ann.decay_weight = await self._compute_decay(domain, source_ref)

        return ann

    async def _safe_call(self, step_name: str, coro: Any, ctx: ToolLoopContext) -> Any:
        try:
            return await coro
        except Exception as exc:
            add_step_error(
                ctx.errors,
                workstream=Workstream.WS_A,
                step_name=f"SourceQualityStep.{step_name}",
                exc=exc,
                severity=StepErrorSeverity.WARNING,
            )
            return None

    async def _compute_decay(self, domain: str, source: SourceRef) -> float:
        if self._temporal_decay_store is None:
            return 1.0
        try:
            config = await self._temporal_decay_store.get(domain, source.provider)
            return _half_life_to_weight(config.half_life_months)
        except Exception:
            return 1.0


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


def _find_source(ctx: ToolLoopContext, finding: Finding) -> SourceRef | None:
    sources: list[SourceRef] = []
    br = getattr(ctx, "branch_result", None)
    if br is not None:
        sources.extend(getattr(br, "sources", []))
    for iteration in ctx.iterations:
        sources.extend(getattr(iteration, "sources", []))
    if not finding.source_ids:
        return sources[0] if sources else None
    for s in sources:
        if s.id in finding.source_ids:
            return s
    return sources[0] if sources else None


def _extract_doi(url: str) -> str | None:
    if "doi.org" in url:
        idx = url.find("10.")
        if idx >= 0:
            return url[idx:].split("?")[0].split("#")[0].strip()
    return None


def _infer_domain(finding: Finding) -> str:
    domain_keywords = {
        "AI": (
            "ai",
            "machine learning",
            "deep learning",
            "neural",
            "llm",
            "artificial intelligence",
        ),
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


def _half_life_to_weight(half_life_months: int) -> float:
    if half_life_months <= 0:
        return 1.0
    return min(1.0, half_life_months / 60.0)


def _attach_annotations(ctx: ToolLoopContext, annotations: list[SourceQualityAnnotation]) -> None:
    if ctx.source_quality_annotations is None:
        ctx.source_quality_annotations = annotations
    else:
        ctx.source_quality_annotations.extend(annotations)
