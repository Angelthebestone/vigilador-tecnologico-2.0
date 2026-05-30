"""Ports (abstractions) for goal-pursuit components — DIP compliance."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SubGoal:
    """A single step in a goal's execution DAG."""

    id: str
    description: str
    dependencies: frozenset[str]
    completion_criteria: str
    status: str = "PENDING"
    result: str = ""


@dataclass(frozen=True, slots=True)
class GoalDAG:
    """Directed acyclic graph of sub-goals with execution order."""

    goal_id: UUID
    sub_goals: tuple[SubGoal, ...]


@dataclass(frozen=True, slots=True)
class ExecutionPlan:
    """Ordered execution plan produced by DependencyResolver."""

    stages: tuple[tuple[str, ...], ...]  # Each stage = parallel sub-goal IDs


@dataclass(frozen=True, slots=True)
class CheckpointReport:
    """Progress report sent at checkpoints."""

    goal_id: UUID
    step_number: int
    completed_steps: tuple[str, ...]
    pending_steps: tuple[str, ...]
    partial_result: str
    blockers: tuple[str, ...]
    eta_seconds: float | None


class GoalDecomposerPort(Protocol):
    """Decomposes a natural-language goal into a DAG of sub-goals."""

    def decompose(
        self, objective: str, context: dict[str, object], max_depth: int
    ) -> GoalDAG: ...


class DependencyResolverPort(Protocol):
    """Validates DAG and produces an ordered execution plan."""

    def resolve(self, dag: GoalDAG) -> ExecutionPlan: ...


class CheckpointReporterPort(Protocol):
    """Reports progress at checkpoints."""

    def report(self, checkpoint: CheckpointReport) -> None: ...


class ApprovalGatePort(Protocol):
    """Blocks execution until human approval is granted."""

    def request_approval(self, goal_id: UUID, context: str) -> bool: ...


class GoalStateStore(Protocol):
    """Persists and retrieves goal execution state."""

    def save_state(self, goal_id: UUID, dag: GoalDAG) -> None: ...

    def load_state(self, goal_id: UUID) -> GoalDAG | None: ...
