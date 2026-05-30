"""GoalExecutor: orchestrates decomposition, resolution, execution, and checkpoints."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Literal
from uuid import UUID

from vigilancia_multiagente.enterprise.orchestration.goal_pursuit.approval_gate import (
    ApprovalGate,
)
from vigilancia_multiagente.enterprise.orchestration.goal_pursuit.capability_token import (
    CapabilityToken,
)
from vigilancia_multiagente.enterprise.orchestration.goal_pursuit.checkpoint_reporter import (
    CheckpointReporter,
)
from vigilancia_multiagente.enterprise.orchestration.goal_pursuit.decomposer import (
    GoalDecomposer,
)
from vigilancia_multiagente.enterprise.orchestration.goal_pursuit.dependency_resolver import (
    DependencyResolver,
)
from vigilancia_multiagente.enterprise.orchestration.goal_pursuit.ports import (
    ExecutionPlan,
    GoalDAG,
    GoalStateStore,
    SubGoal,
)

GoalStatus = Literal["ACTIVE", "PAUSED", "COMPLETED", "FAILED"]

logger = logging.getLogger(__name__)


class SubGoalExecutionError(Exception):
    """Raised when a sub-goal fails after retries."""

    def __init__(self, sub_goal_id: str, attempts: int, last_error: str) -> None:
        self.sub_goal_id = sub_goal_id
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(
            f"Sub-goal {sub_goal_id!r} failed after {attempts} attempts: {last_error}"
        )


class SubGoalRunnerPort:
    """Port for executing individual sub-goals."""

    def run(self, sub_goal: SubGoal) -> str:
        """Execute a sub-goal. Returns result string. Raises on failure."""
        raise NotImplementedError


@dataclass
class GoalState:
    """Mutable state of a goal execution."""

    goal_id: UUID
    status: GoalStatus
    dag: GoalDAG
    plan: ExecutionPlan
    token: CapabilityToken
    completed: list[str] = field(default_factory=list)
    results: dict[str, str] = field(default_factory=dict)
    current_stage: int = 0
    failed_sub_goals: list[str] = field(default_factory=list)


class GoalExecutor:
    """Coordinates goal decomposition, resolution, execution, and reporting."""

    MAX_RETRIES = 3

    def __init__(
        self,
        decomposer: GoalDecomposer,
        resolver: DependencyResolver,
        reporter: CheckpointReporter,
        gate: ApprovalGate,
        runner: SubGoalRunnerPort,
        store: GoalStateStore,
    ) -> None:
        self._decomposer = decomposer
        self._resolver = resolver
        self._reporter = reporter
        self._gate = gate
        self._runner = runner
        self._store = store

    def execute(
        self,
        goal_id: UUID,
        objective: str,
        context: dict[str, object],
        token: CapabilityToken,
        max_depth: int = 5,
        critical_steps: frozenset[str] = frozenset(),
    ) -> GoalState:
        """Execute a goal end-to-end. Returns final state."""
        context_with_id = {**context, "goal_id": str(goal_id)}
        dag = self._decomposer.decompose(objective, context_with_id, max_depth)
        plan = self._resolver.resolve(dag)
        state = GoalState(
            goal_id=goal_id, status="ACTIVE", dag=dag, plan=plan, token=token
        )
        self._store.save_state(goal_id, dag)
        return self._run_plan(state, critical_steps)

    def resume(self, state: GoalState, critical_steps: frozenset[str] = frozenset()) -> GoalState:
        """Resume a paused goal from its current stage."""
        state.status = "ACTIVE"
        return self._run_plan(state, critical_steps)

    def pause(self, state: GoalState) -> GoalState:
        """Pause an active goal."""
        state.status = "PAUSED"
        return state

    def cancel(self, state: GoalState) -> GoalState:
        """Cancel an active goal, marking active sub-goals as FAILED."""
        state.status = "FAILED"
        all_completed = set(state.completed)
        for sg in state.dag.sub_goals:
            if sg.id not in all_completed:
                state.failed_sub_goals.append(sg.id)
        return state

    def recover(self, goal_id: UUID, token: CapabilityToken) -> GoalState | None:
        """Recover a goal from persisted state after restart."""
        dag = self._store.load_state(goal_id)
        if dag is None:
            return None
        plan = self._resolver.resolve(dag)
        # Determine completed from DAG status
        completed = [sg.id for sg in dag.sub_goals if sg.status == "COMPLETED"]
        # Find current stage
        current_stage = 0
        for i, stage in enumerate(plan.stages):
            if all(sid in completed for sid in stage):
                current_stage = i + 1
            else:
                break
        return GoalState(
            goal_id=goal_id,
            status="ACTIVE",
            dag=dag,
            plan=plan,
            token=token,
            completed=completed,
            current_stage=current_stage,
        )

    def _run_plan(
        self, state: GoalState, critical_steps: frozenset[str]
    ) -> GoalState:
        """Execute stages sequentially, sub-goals within a stage in order."""
        pending_ids = {sg.id for sg in state.dag.sub_goals} - set(state.completed)
        sg_map = {sg.id: sg for sg in state.dag.sub_goals}

        for stage_idx in range(state.current_stage, len(state.plan.stages)):
            stage = state.plan.stages[stage_idx]

            for sg_id in stage:
                if sg_id in state.completed:
                    continue

                # Check token expiration
                if state.token.is_expired():
                    state.status = "PAUSED"
                    return state

                # Check approval gate for critical steps
                if sg_id in critical_steps:
                    result = self._gate.request_approval(
                        state.goal_id,
                        f"Executing critical step: {sg_map[sg_id].description}",
                        state.token,
                    )
                    if not result.approved:
                        state.status = "PAUSED"
                        return state

                # Execute with retries
                sg = sg_map[sg_id]
                executed = self._execute_with_retries(sg)
                if executed is None:
                    state.status = "PAUSED"
                    state.failed_sub_goals.append(sg_id)
                    return state

                state.completed.append(sg_id)
                state.results[sg_id] = executed
                pending_ids.discard(sg_id)

                # Checkpoint reporting
                self._reporter.step_completed(
                    goal_id=state.goal_id,
                    completed=tuple(state.completed),
                    pending=tuple(sorted(pending_ids)),
                    partial_result=executed,
                )

            state.current_stage = stage_idx + 1

        state.status = "COMPLETED"
        return state

    def _execute_with_retries(self, sg: SubGoal) -> str | None:
        """Execute a sub-goal with up to MAX_RETRIES attempts. Returns result or None."""
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                return self._runner.run(sg)
            except Exception as exc:
                logger.warning(
                    "Sub-goal %r attempt %d/%d failed: %s",
                    sg.id,
                    attempt,
                    self.MAX_RETRIES,
                    exc,
                )
                if attempt == self.MAX_RETRIES:
                    return None
        return None  # unreachable but satisfies type checker
