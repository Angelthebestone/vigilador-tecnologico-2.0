"""GoalDecomposer: breaks complex objectives into a DAG of sub-goals."""

from __future__ import annotations

from uuid import UUID

from vigilancia_multiagente.enterprise.orchestration.goal_pursuit.ports import (
    GoalDAG,
    SubGoal,
)


class DecompositionError(Exception):
    """Raised when a goal cannot be decomposed (too vague, etc.)."""

    def __init__(self, reason: str, objective: str) -> None:
        self.reason = reason
        self.objective = objective
        super().__init__(f"Cannot decompose goal: {reason}. Objective: {objective!r}")


class MaxDepthExceededError(Exception):
    """Raised when decomposition exceeds max_depth."""

    def __init__(self, max_depth: int) -> None:
        self.max_depth = max_depth
        super().__init__(f"Decomposition exceeds max_depth={max_depth}")


class LLMDecomposerPort:
    """Protocol-like interface for the LLM that produces sub-goals."""

    def decompose_objective(
        self, objective: str, context: dict[str, object]
    ) -> list[dict[str, object]]:
        """Return list of sub-goal dicts with id, description, dependencies, completion_criteria."""
        raise NotImplementedError


class GoalDecomposer:
    """Decomposes a natural-language goal into a DAG of sub-goals via LLM."""

    def __init__(self, llm: LLMDecomposerPort) -> None:
        self._llm = llm

    def decompose(
        self, objective: str, context: dict[str, object], max_depth: int
    ) -> GoalDAG:
        """Decompose objective into GoalDAG. Raises on vague goals or depth exceeded."""
        if not objective.strip():
            raise DecompositionError(
                reason="objective is empty", objective=objective
            )

        raw_goals = self._llm.decompose_objective(objective, context)

        if not raw_goals:
            raise DecompositionError(
                reason="objective too vague, clarification needed",
                objective=objective,
            )

        if len(raw_goals) > max_depth * 10:
            raise MaxDepthExceededError(max_depth=max_depth)

        sub_goals: list[SubGoal] = []
        for item in raw_goals:
            sg = SubGoal(
                id=str(item["id"]),
                description=str(item["description"]),
                dependencies=frozenset(
                    str(d) for d in item.get("dependencies", [])  # type: ignore[union-attr]
                ),
                completion_criteria=str(item["completion_criteria"]),
            )
            sub_goals.append(sg)

        # Validate depth constraint
        self._validate_depth(sub_goals, max_depth)

        goal_id = UUID(str(context.get("goal_id", "00000000-0000-0000-0000-000000000000")))
        return GoalDAG(goal_id=goal_id, sub_goals=tuple(sub_goals))

    def _validate_depth(self, sub_goals: list[SubGoal], max_depth: int) -> None:
        """Validate that the dependency chain depth does not exceed max_depth."""
        id_to_deps: dict[str, frozenset[str]] = {
            sg.id: sg.dependencies for sg in sub_goals
        }
        memo: dict[str, int] = {}

        def depth_of(node_id: str) -> int:
            if node_id in memo:
                return memo[node_id]
            deps = id_to_deps.get(node_id, frozenset())
            if not deps:
                memo[node_id] = 0
                return 0
            d = 1 + max(depth_of(dep) for dep in deps if dep in id_to_deps)
            memo[node_id] = d
            return d

        for sg_id in id_to_deps:
            if depth_of(sg_id) >= max_depth:
                raise MaxDepthExceededError(max_depth=max_depth)
