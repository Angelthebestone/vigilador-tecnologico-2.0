
# STATUS: MIGRATE -- migrar a spec 007
# DEPRECATED: migrar a spec 007
from dataclasses import dataclass

from vigilancia_multiagente.domain.models import BranchResult, BranchType

# STATUS: MIGRATE — migrar a spec 007 (componente de observabilidad/monitoreo)
# DEPRECATED: migrar a spec 007


@dataclass(slots=True, frozen=True)
class BranchKPI:
    branch_type: BranchType
    coverage_kpi: float
    precision_kpi: float
    latency_ms_kpi: int
    cost_kpi: float


class BranchKPIService:
    def compute(self, branch_result: BranchResult, latency_ms: int, cost_kpi: float) -> BranchKPI:
        coverage = branch_result.coverage_score or 0.0
        precision = branch_result.confidence_score or 0.0
        return BranchKPI(
            branch_type=branch_result.branch_type,
            coverage_kpi=round(coverage, 3),
            precision_kpi=round(precision, 3),
            latency_ms_kpi=latency_ms,
            cost_kpi=round(cost_kpi, 2),
        )
