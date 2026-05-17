from dataclasses import dataclass
from datetime import UTC, datetime

from vigilancia_multiagente.domain.models import BranchType


@dataclass(slots=True, frozen=True)
class TemporalWindow:
    start_year: int
    end_year: int
    basis: str


def resolve_temporal_window(
    branch_type: BranchType, years_back_override: int | None = None
) -> TemporalWindow:
    now_year = datetime.now(UTC).year
    years_back_by_branch = {
        BranchType.AVANCES: 5,
        BranchType.COMERCIAL: 3,
        BranchType.RIESGO: 5,
        BranchType.PI_NORMATIVA: 8,
        BranchType.COMPETITIVO: 3,
        BranchType.OPORTUNIDADES: 4,
    }
    years_back = years_back_override or years_back_by_branch[branch_type]
    return TemporalWindow(
        start_year=now_year - years_back,
        end_year=now_year,
        basis=f"dynamic-{branch_type.value.lower()}",
    )
