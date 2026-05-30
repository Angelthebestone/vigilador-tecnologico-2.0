"""Tests for DependencyResolver: sequencing, parallelism, cycles, empty, depth."""

from __future__ import annotations

from uuid import uuid4

import pytest

from vigilancia_multiagente.enterprise.orchestration.goal_pursuit.dependency_resolver import (
    CyclicDependencyError,
    DependencyResolver,
    DepthExceededError,
    EmptyDAGError,
)
from vigilancia_multiagente.enterprise.orchestration.goal_pursuit.ports import (
    GoalDAG,
    SubGoal,
)


def _dag(sub_goals: list[SubGoal]) -> GoalDAG:
    return GoalDAG(goal_id=uuid4(), sub_goals=tuple(sub_goals))


def test_valid_dag_sequences_correctly() -> None:
    sg_a = SubGoal(id="a", description="A", dependencies=frozenset(), completion_criteria="done")
    sg_b = SubGoal(id="b", description="B", dependencies=frozenset({"a"}), completion_criteria="done")
    sg_c = SubGoal(id="c", description="C", dependencies=frozenset({"b"}), completion_criteria="done")
    resolver = DependencyResolver()
    plan = resolver.resolve(_dag([sg_a, sg_b, sg_c]))
    flat = [sg_id for stage in plan.stages for sg_id in stage]
    assert flat.index("a") < flat.index("b") < flat.index("c")


def test_identifies_parallelizable_steps() -> None:
    sg_a = SubGoal(id="a", description="A", dependencies=frozenset(), completion_criteria="done")
    sg_b = SubGoal(id="b", description="B", dependencies=frozenset(), completion_criteria="done")
    sg_c = SubGoal(id="c", description="C", dependencies=frozenset({"a", "b"}), completion_criteria="done")
    resolver = DependencyResolver()
    plan = resolver.resolve(_dag([sg_a, sg_b, sg_c]))
    # a and b should be in the same stage (parallel)
    assert "a" in plan.stages[0]
    assert "b" in plan.stages[0]
    assert "c" in plan.stages[1]


def test_detects_cycle_and_rejects() -> None:
    sg_a = SubGoal(id="a", description="A", dependencies=frozenset({"c"}), completion_criteria="done")
    sg_b = SubGoal(id="b", description="B", dependencies=frozenset({"a"}), completion_criteria="done")
    sg_c = SubGoal(id="c", description="C", dependencies=frozenset({"b"}), completion_criteria="done")
    resolver = DependencyResolver()
    with pytest.raises(CyclicDependencyError):
        resolver.resolve(_dag([sg_a, sg_b, sg_c]))


def test_empty_dag_raises_error() -> None:
    resolver = DependencyResolver()
    with pytest.raises(EmptyDAGError):
        resolver.resolve(_dag([]))


def test_excessive_depth_rejected() -> None:
    # Chain of 5 nodes with max_depth=3
    sgs = []
    for i in range(5):
        deps = frozenset({f"sg-{i-1}"}) if i > 0 else frozenset()
        sgs.append(SubGoal(id=f"sg-{i}", description=f"S{i}", dependencies=deps, completion_criteria="done"))
    resolver = DependencyResolver(max_depth=3)
    with pytest.raises(DepthExceededError):
        resolver.resolve(_dag(sgs))
