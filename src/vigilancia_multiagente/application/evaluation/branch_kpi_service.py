"""KPIs por rama (cobertura, precision, latencia, costo).

Sub-componente de observabilidad que `ReportQualityGate` (WS-E) usa para
poblar `FinalReport.assurance.kpis`. Mantiene el API estable del spec 006.
"""

from __future__ import annotations

from dataclasses import dataclass

from vigilancia_multiagente.domain.models import BranchResult, BranchType


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
