"""Tests for GoalDecomposer: decomposition, vague goals, max_depth, criteria."""

from __future__ import annotations

from uuid import uuid4

import pytest

from vigilancia_multiagente.enterprise.orchestration.goal_pursuit.decomposer import (
    DecompositionError,
    GoalDecomposer,
    LLMDecomposerPort,
    MaxDepthExceededError,
)


class FakeLLM(LLMDecomposerPort):
    """Fake LLM that returns pre-configured sub-goals."""

    def __init__(self, results: list[dict[str, object]]) -> None:
        self._results = results

    def decompose_objective(
        self, objective: str, context: dict[str, object]
    ) -> list[dict[str, object]]:
        return self._results


class EmptyLLM(LLMDecomposerPort):
    """Fake LLM that returns empty (simulates vague goal)."""

    def decompose_objective(
        self, objective: str, context: dict[str, object]
    ) -> list[dict[str, object]]:
        return []


def _make_sub_goals(count: int) -> list[dict[str, object]]:
    goals: list[dict[str, object]] = []
    for i in range(count):
        deps: list[str] = [f"sg-{i - 1}"] if i > 0 else []
        goals.append(
            {
                "id": f"sg-{i}",
                "description": f"Sub-goal {i}",
                "dependencies": deps,
                "completion_criteria": f"Criteria for sg-{i}",
            }
        )
    return goals


def test_complex_objective_produces_multiple_sub_goals() -> None:
    llm = FakeLLM(_make_sub_goals(5))
    decomposer = GoalDecomposer(llm)
    goal_id = uuid4()
    dag = decomposer.decompose(
        "Get 10 B2B leads in logistics Colombia",
        {"goal_id": str(goal_id)},
        max_depth=5,
    )
    assert len(dag.sub_goals) >= 3
    for sg in dag.sub_goals:
        assert sg.completion_criteria != ""


def test_vague_objective_raises_error() -> None:
    llm = EmptyLLM()
    decomposer = GoalDecomposer(llm)
    with pytest.raises(DecompositionError, match="too vague"):
        decomposer.decompose("do stuff", {"goal_id": str(uuid4())}, max_depth=5)


def test_max_depth_respected() -> None:
    # Create a deep chain that exceeds max_depth=2
    goals: list[dict[str, object]] = []
    for i in range(5):
        deps: list[str] = [f"sg-{i - 1}"] if i > 0 else []
        goals.append(
            {
                "id": f"sg-{i}",
                "description": f"Step {i}",
                "dependencies": deps,
                "completion_criteria": f"Done {i}",
            }
        )
    llm = FakeLLM(goals)
    decomposer = GoalDecomposer(llm)
    with pytest.raises(MaxDepthExceededError):
        decomposer.decompose("deep goal", {"goal_id": str(uuid4())}, max_depth=2)


def test_sub_goals_have_explicit_completion_criteria() -> None:
    llm = FakeLLM(_make_sub_goals(3))
    decomposer = GoalDecomposer(llm)
    dag = decomposer.decompose("objective", {"goal_id": str(uuid4())}, max_depth=5)
    for sg in dag.sub_goals:
        assert sg.completion_criteria
        assert len(sg.completion_criteria) > 0
