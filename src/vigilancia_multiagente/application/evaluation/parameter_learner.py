"""Records branch execution outcomes and suggests optimal parameters."""

from dataclasses import dataclass, field

from vigilancia_multiagente.domain.models import BranchType

_DEFAULTS: dict[str, int | float] = {"depth_limit": 3, "temperature": 0.3}


@dataclass(slots=True)
class ParameterLearner:
    """Learns optimal branch parameters from historical execution outcomes.

    Usage:
        learner = ParameterLearner()
        learner.record_outcome(BranchType.AVANCES, {"depth_limit": 5}, True, 0.92)
        best = learner.suggest(BranchType.AVANCES)
    """

    _history: dict[BranchType, list[dict]] = field(default_factory=dict, repr=False)

    def record_outcome(
        self, branch: BranchType, params: dict, success: bool, coverage: float
    ) -> None:
        self._history.setdefault(branch, []).append(
            {"params": params, "success": success, "coverage": coverage}
        )

    def suggest(self, branch: BranchType) -> dict:
        records = self._history.get(branch)
        if not records:
            return dict(_DEFAULTS)

        best: dict | None = None
        best_cov: float = -1.0

        for r in records:
            if r["success"] and r["coverage"] > best_cov:
                best = r["params"]
                best_cov = r["coverage"]

        return dict(best) if best is not None else dict(_DEFAULTS)
