from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from vigilancia_multiagente.domain.session_state import SessionStatus


class BranchType(StrEnum):
    AVANCES = "AVANCES"
    COMERCIAL = "COMERCIAL"
    RIESGO = "RIESGO"
    PI_NORMATIVA = "PI_NORMATIVA"
    COMPETITIVO = "COMPETITIVO"
    OPORTUNIDADES = "OPORTUNIDADES"


class BranchStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


@dataclass(slots=True)
class ResearchSession:
    id: UUID
    created_at: datetime
    updated_at: datetime
    status: SessionStatus
    user_query: str
    scope: dict[str, str] | None = None
    clarification_set_id: UUID | None = None
    approved_plan_id: UUID | None = None
    final_report_id: UUID | None = None
    execution_time_seconds: float | None = None
    error_code: str | None = None
    error_message: str | None = None


@dataclass(slots=True)
class BranchConfig:
    branch_type: BranchType
    focus_queries: list[str]
    mcp_providers: list[str]
    mcp_tool_profile: str | None = None
    priority_weight: int | None = None
    status: BranchStatus = BranchStatus.PENDING
    overlay_ref: str | None = None  # Optional reference to a custom overlay version


@dataclass(slots=True)
class ResearchPlan:
    id: UUID
    session_id: UUID
    version: int
    branches: list[BranchConfig]
    system_base_version: str = "1.0.0"  # Reference to canonical system base
    global_constraints: dict[str, str | int | float] = field(default_factory=dict)
    requires_approval: bool = True
    approved_at: datetime | None = None


@dataclass(slots=True)
class Finding:
    id: UUID
    topic: str
    statement: str
    confidence: float
    source_ids: list[UUID]
    tags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SourceRef:
    id: UUID
    session_id: UUID
    url: str
    provider: str
    branch_type: BranchType
    accessed_at: datetime
    title: str | None = None
    content_hash: str | None = None


@dataclass(slots=True)
class GraphCentrality:
    node_id: str
    degree: float
    betweenness: float
    pagerank: float


@dataclass(slots=True)
class GraphCluster:
    cluster_id: str
    node_ids: list[str]
    score: float


@dataclass(slots=True)
class GraphPathResult:
    source_node_id: str
    target_node_id: str
    node_ids: list[str]
    edge_ids: list[str]
    total_cost: float


@dataclass(slots=True)
class GraphSearchHit:
    node_id: str
    label: str
    score: float
    explanation: str


@dataclass(slots=True)
class BranchResult:
    id: UUID
    session_id: UUID
    branch_type: BranchType
    queries_executed: list[str]
    findings: list[Finding]
    sources: list[SourceRef]
    started_at: datetime | None = None
    completed_at: datetime | None = None
    coverage_score: float | None = None
    confidence_score: float | None = None
    errors: list[str] = field(default_factory=list)

