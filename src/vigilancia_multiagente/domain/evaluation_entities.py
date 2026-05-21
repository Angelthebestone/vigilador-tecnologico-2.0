"""Entities de dominio del spec 007 (Sistema de Evaluacion Inteligente).

Todos los value objects estan declarados frozen para garantizar inmutabilidad
desde la capa de aplicacion. Las enums viven aqui para evitar referencias
cruzadas a `infra/` o `application/`.

Referencia: `specs/007-evaluacion-inteligente/data-model.md`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID

# ----------------------------------------------------------------------------
# WS-A — Source Quality
# ----------------------------------------------------------------------------


class AffiliationType(StrEnum):
    ACADEMIC = "academic"
    INDUSTRY = "industry"
    GOVERNMENT = "government"
    INDEPENDENT = "independent"


class FunderType(StrEnum):
    CORPORATE = "corporate"
    ACADEMIC = "academic"
    GOVERNMENT = "government"
    UNKNOWN = "unknown"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SourceType(StrEnum):
    PAPER = "paper"
    PATENT = "patent"
    NEWS = "news"
    BLOG = "blog"


class ExternalValidationStatus(StrEnum):
    VERIFIED = "verified"
    CONTRADICTED = "contradicted"
    NOT_FOUND = "not_found"


@dataclass(slots=True, frozen=True)
class AuthorReputation:
    author_id: str
    display_name: str
    h_index: int
    total_citations: int
    retraction_count: int
    primary_affiliation: str | None
    affiliation_type: AffiliationType
    domain_weights: dict[str, float] = field(default_factory=dict)
    last_refreshed: datetime = field(default_factory=datetime.now)


@dataclass(slots=True, frozen=True)
class ConflictOfInterest:
    source_id: UUID
    funder_entity: str
    funder_type: FunderType
    corporate_ratio: float
    risk_level: RiskLevel


@dataclass(slots=True, frozen=True)
class TemporalDecayConfig:
    domain: str
    half_life_months: int
    source_type: SourceType


@dataclass(slots=True, frozen=True)
class ClaimExternalValidation:
    claim_id: UUID
    external_db: str
    status: ExternalValidationStatus
    evidence_url: str | None = None


@dataclass(slots=True, frozen=True)
class RetractionRecord:
    source_doi: str
    retracted_at: datetime
    reason: str
    dependent_findings: list[UUID] = field(default_factory=list)


@dataclass(slots=True, frozen=True)
class ReproducibilityScore:
    finding_id: UUID
    has_public_repo: bool
    has_open_data: bool
    has_reproducible_env: bool
    score: float


# ----------------------------------------------------------------------------
# WS-B — Data Intelligence
# ----------------------------------------------------------------------------


class EvidenceStrength(StrEnum):
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"


@dataclass(slots=True, frozen=True)
class HybridSearchQuery:
    text: str
    vector: list[float]
    keywords: list[str]
    vector_weight: float = 0.6
    keyword_weight: float = 0.4


@dataclass(slots=True, frozen=True)
class DedupedSource:
    canonical_url: str
    duplicate_urls: list[str]
    similarity_score: float


@dataclass(slots=True, frozen=True)
class ExtractionSchema:
    source_type: SourceType
    domain: str
    json_schema: dict[str, object]
    version: int = 1


@dataclass(slots=True, frozen=True)
class ContentAuthenticitySignal:
    source_id: UUID
    ai_probability: float
    perplexity: float
    burstiness: float
    boilerplate_hits: int
    effective_freshness: float
    penalty_factor: float


@dataclass(slots=True, frozen=True)
class ConsensusDisputeMap:
    claim: str
    supporting_sources: list[UUID]
    contradicting_sources: list[UUID]
    evidence_strength: EvidenceStrength
    resolution: str | None = None


# ----------------------------------------------------------------------------
# WS-C — Deep Analysis
# ----------------------------------------------------------------------------


class AssumptionSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class DependencyKind(StrEnum):
    MATERIAL = "material"
    LIBRARY = "library"
    VENDOR = "vendor"
    REGULATION = "regulation"


@dataclass(slots=True, frozen=True)
class ImplicitAssumption:
    finding_id: UUID
    text: str
    severity: AssumptionSeverity
    affects_confidence: float


@dataclass(slots=True, frozen=True)
class SCurveProjection:
    technology: str
    domain: str
    growth_rate: float
    inflection_year: int
    ceiling: float
    r_squared: float
    samples_count: int


@dataclass(slots=True, frozen=True)
class CriticalDependency:
    technology: str
    dependency_kind: DependencyKind
    name: str
    risk_level: RiskLevel


@dataclass(slots=True, frozen=True)
class CounterfactualScenario:
    id: UUID
    question: str
    probability: float
    impact_summary: str


@dataclass(slots=True, frozen=True)
class MetaAnalysisResult:
    topic: str
    studies_count: int
    effect_size_range: tuple[float, float]
    consensus_value: float
    i_squared: float
    q_test_pvalue: float
    outliers: list[str] = field(default_factory=list)


# ----------------------------------------------------------------------------
# WS-D — Strategic Signals
# ----------------------------------------------------------------------------


class PatentingClassification(StrEnum):
    BLUE_OCEAN = "blue_ocean"
    RED_OCEAN = "red_ocean"
    BALANCED = "balanced"


@dataclass(slots=True, frozen=True)
class ConvergenceCluster:
    id: UUID
    domains: list[str]
    representative_terms: list[str]
    growth_trend: float
    first_detected: datetime


@dataclass(slots=True, frozen=True)
class CollaborationNode:
    node_id: str
    label: str
    role: str  # "author" | "inventor" | "both"
    centrality: float


@dataclass(slots=True, frozen=True)
class CollaborationNetwork:
    network_id: UUID
    nodes: list[CollaborationNode]
    edges: list[tuple[str, str, int]]
    centrality_metrics: dict[str, float] = field(default_factory=dict)
    bubble_clusters: list[list[str]] = field(default_factory=list)


@dataclass(slots=True, frozen=True)
class IdeaLineage:
    idea: str
    seminal_publication_id: UUID
    citation_chain: list[UUID]
    circularity_detected: bool = False


@dataclass(slots=True, frozen=True)
class NarrativeShift:
    topic: str
    window_start: datetime
    window_end: datetime
    sentiment_pre: float
    sentiment_post: float
    change_point: datetime
    change_magnitude: float


@dataclass(slots=True, frozen=True)
class Affiliation:
    institution: str
    role: str
    started_at: datetime
    ended_at: datetime | None = None


@dataclass(slots=True, frozen=True)
class TalentMobility:
    author_id: str
    academic_history: list[Affiliation]
    industry_transitions: list[Affiliation]
    mobility_score: float


@dataclass(slots=True, frozen=True)
class PatentingGap:
    subdomain: str
    publication_density: float
    patent_density: float
    gap_score: float
    classification: PatentingClassification


# ----------------------------------------------------------------------------
# WS-E — Output Assurance
# ----------------------------------------------------------------------------


class GoldenCasePriority(StrEnum):
    P0_CRITICAL = "p0_critical"
    P1_HIGH = "p1_high"
    P2_NORMAL = "p2_normal"


class StakeholderType(StrEnum):
    INVESTOR = "investor"
    REGULATOR = "regulator"
    COMPETITOR = "competitor"
    ACADEMIC = "academic"


class TraceStepType(StrEnum):
    SOURCE_FETCH = "source_fetch"
    EXTRACTION = "extraction"
    REASONING = "reasoning"
    SYNTHESIS = "synthesis"


@dataclass(slots=True, frozen=True)
class ExpectedFinding:
    topic: str
    statement: str
    confidence_min: float
    confidence_max: float


@dataclass(slots=True, frozen=True)
class GoldenCase:
    id: UUID
    name: str
    description: str
    seed_query: str
    expected_findings: list[ExpectedFinding]
    expected_confidence: float
    priority: GoldenCasePriority


@dataclass(slots=True, frozen=True)
class GoldenCaseRun:
    id: UUID
    case_id: UUID
    run_at: datetime
    success: bool
    actual_confidence: float
    delta_vs_expected: float
    failure_details: str | None = None


@dataclass(slots=True, frozen=True)
class StakeholderSimulation:
    report_id: UUID
    stakeholder_type: StakeholderType
    critique: str
    counterpoints: list[str] = field(default_factory=list)


@dataclass(slots=True, frozen=True)
class FalsificationScenario:
    conclusion_id: UUID
    hypothetical_evidence: str
    plausibility: float
    falsifiable: bool


@dataclass(slots=True, frozen=True)
class BiasThresholds:
    geographic_max_share: float = 0.7
    gender_max_share: float = 0.9
    institutional_max_share: float = 0.8


@dataclass(slots=True, frozen=True)
class BiasAudit:
    report_id: UUID
    geographic_distribution: dict[str, float]
    gender_distribution: dict[str, float]
    institutional_distribution: dict[str, float]
    critical_bias_detected: bool
    bias_categories: list[str] = field(default_factory=list)


@dataclass(slots=True, frozen=True)
class TraceStep:
    step_type: TraceStepType
    input_ref: str
    output_ref: str
    applied_rule: str


@dataclass(slots=True, frozen=True)
class ForensicTrace:
    claim_id: UUID
    chain: list[TraceStep]
    confidence_at_each_step: list[float]


@dataclass(slots=True, frozen=True)
class CalibrationCurve:
    id: UUID
    model_version: str
    created_at: datetime
    samples_count: int
    mappings: list[tuple[float, float]]


@dataclass(slots=True, frozen=True)
class ReportAssurance:
    """Output del `ReportQualityGate` anexado al FinalReport (spec 007 T028).

    Se materializa solo cuando `VT_EVAL_WS_E_ENABLED=true`. Si el flag esta
    off, `FinalReport.assurance` es None y el comportamiento del vigilador
    es identico al previo al spec 007.
    """

    bias_audit: BiasAudit | None = None
    stakeholder_simulations: list[StakeholderSimulation] = field(default_factory=list)
    falsification_scenarios: list[FalsificationScenario] = field(default_factory=list)
    calibrated_confidence: float | None = None
    forensic_trace_count: int = 0
    kpis: dict[str, float] = field(default_factory=dict)


__all__ = [
    # Enums WS-A
    "AffiliationType",
    "FunderType",
    "RiskLevel",
    "SourceType",
    "ExternalValidationStatus",
    # Entities WS-A
    "AuthorReputation",
    "ConflictOfInterest",
    "TemporalDecayConfig",
    "ClaimExternalValidation",
    "RetractionRecord",
    "ReproducibilityScore",
    # Enums WS-B
    "EvidenceStrength",
    # Entities WS-B
    "HybridSearchQuery",
    "DedupedSource",
    "ExtractionSchema",
    "ContentAuthenticitySignal",
    "ConsensusDisputeMap",
    # Enums WS-C
    "AssumptionSeverity",
    "DependencyKind",
    # Entities WS-C
    "ImplicitAssumption",
    "SCurveProjection",
    "CriticalDependency",
    "CounterfactualScenario",
    "MetaAnalysisResult",
    # Enums WS-D
    "PatentingClassification",
    # Entities WS-D
    "ConvergenceCluster",
    "CollaborationNode",
    "CollaborationNetwork",
    "IdeaLineage",
    "NarrativeShift",
    "Affiliation",
    "TalentMobility",
    "PatentingGap",
    # Enums WS-E
    "GoldenCasePriority",
    "StakeholderType",
    "TraceStepType",
    # Entities WS-E
    "ExpectedFinding",
    "GoldenCase",
    "GoldenCaseRun",
    "StakeholderSimulation",
    "FalsificationScenario",
    "BiasThresholds",
    "BiasAudit",
    "TraceStep",
    "ForensicTrace",
    "CalibrationCurve",
    "ReportAssurance",
]
