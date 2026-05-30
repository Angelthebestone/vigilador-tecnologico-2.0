"""Tests for GoalExecutor: full flow, pause/resume, cancel, restart, token expiry, retries."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from vigilancia_multiagente.enterprise.orchestration.goal_pursuit.approval_gate import (
    ApprovalGate,
    ApprovalRequestPort,
)
from vigilancia_multiagente.enterprise.orchestration.goal_pursuit.capability_token import (
    CapabilityToken,
)
from vigilancia_multiagente.enterprise.orchestration.goal_pursuit.checkpoint_reporter import (
    CheckpointReporter,
    ReportChannelPort,
)
from vigilancia_multiagente.enterprise.orchestration.goal_pursuit.decomposer import (
    GoalDecomposer,
    LLMDecomposerPort,
)
from vigilancia_multiagente.enterprise.orchestration.goal_pursuit.dependency_resolver import (
    DependencyResolver,
)
from vigilancia_multiagente.enterprise.orchestration.goal_pursuit.goal_executor import (
    GoalExecutor,
    GoalState,
    SubGoalRunnerPort,
)
from vigilancia_multiagente.enterprise.orchestration.goal_pursuit.ports import (
    CheckpointReport,
    GoalDAG,
    SubGoal,
)


# --- Fakes ---


class FakeLLM(LLMDecomposerPort):
    def __init__(self, count: int = 5) -> None:
        self._count = count

    def decompose_objective(
        self, objective: str, context: dict[str, object]
    ) -> list[dict[str, object]]:
        goals: list[dict[str, object]] = []
        for i in range(self._count):
            deps: list[str] = [f"sg-{i-1}"] if i > 0 else []
            goals.append({
                "id": f"sg-{i}",
                "description": f"Step {i}",
                "dependencies": deps,
                "completion_criteria": f"Done {i}",
            })
        return goals


class FakeChannel(ReportChannelPort):
    def __init__(self) -> None:
        self.reports: list[CheckpointReport] = []

    def send(self, report: CheckpointReport) -> bool:
        self.reports.append(report)
        return True


class FakeApprovalPort(ApprovalRequestPort):
    def __init__(self, approved: bool = True) -> None:
        self._approved = approved

    def submit_request(self, goal_id: object, context: str) -> str:
        return "req-1"

    def is_approved(self, request_id: str) -> bool:
        return self._approved


class FakeRunner(SubGoalRunnerPort):
    def __init__(self, fail_ids: frozenset[str] = frozenset()) -> None:
        self._fail_ids = fail_ids
        self.executed: list[str] = []

    def run(self, sub_goal: SubGoal) -> str:
        if sub_goal.id in self._fail_ids:
            raise RuntimeError(f"Failed: {sub_goal.id}")
        self.executed.append(sub_goal.id)
        return f"result-{sub_goal.id}"


class FakeStore:
    def __init__(self) -> None:
        self._data: dict[UUID, GoalDAG] = {}

    def save_state(self, goal_id: UUID, dag: GoalDAG) -> None:
        self._data[goal_id] = dag

    def load_state(self, goal_id: UUID) -> GoalDAG | None:
        return self._data.get(goal_id)


def _make_executor(
    llm_count: int = 5,
    fail_ids: frozenset[str] = frozenset(),
    approval: bool = True,
    checkpoint_n: int = 3,
) -> tuple[GoalExecutor, FakeStore, FakeRunner, FakeChannel]:
    channel = FakeChannel()
    store = FakeStore()
    runner = FakeRunner(fail_ids=fail_ids)
    executor = GoalExecutor(
        decomposer=GoalDecomposer(FakeLLM(llm_count)),
        resolver=DependencyResolver(),
        reporter=CheckpointReporter(channel, checkpoint_every_n=checkpoint_n),
        gate=ApprovalGate(FakeApprovalPort(approved=approval)),
        runner=runner,
        store=store,
    )
    return executor, store, runner, channel


def _valid_token() -> CapabilityToken:
    return CapabilityToken.issue(uuid4(), ttl_seconds=3600, scopes=frozenset({"all"}))


def test_full_flow_5_sub_goals_with_checkpoints() -> None:
    executor, store, runner, channel = _make_executor(llm_count=5, checkpoint_n=2)
    goal_id = uuid4()
    state = executor.execute(goal_id, "complex goal", {}, _valid_token(), max_depth=10)
    assert state.status == "COMPLETED"
    assert len(state.completed) == 5
    assert len(channel.reports) >= 2  # at least 2 checkpoints for 5 steps with n=2


def test_pause_resume_works() -> None:
    executor, store, runner, channel = _make_executor(llm_count=3)
    goal_id = uuid4()
    state = executor.execute(goal_id, "goal", {}, _valid_token(), max_depth=10)
    assert state.status == "COMPLETED"
    # Simulate pause/resume on a fresh state
    executor2, store2, runner2, channel2 = _make_executor(llm_count=3)
    goal_id2 = uuid4()
    state2 = executor2.execute(goal_id2, "goal", {}, _valid_token(), max_depth=10)
    paused = executor2.pause(state2)
    assert paused.status == "PAUSED"
    resumed = executor2.resume(paused)
    assert resumed.status == "COMPLETED"


def test_cancel_marks_active_sub_goals_failed() -> None:
    executor, store, runner, channel = _make_executor(llm_count=5, fail_ids=frozenset({"sg-2"}))
    goal_id = uuid4()
    state = executor.execute(goal_id, "goal", {}, _valid_token(), max_depth=10)
    # State is paused because sg-2 failed after retries
    assert state.status == "PAUSED"
    cancelled = executor.cancel(state)
    assert cancelled.status == "FAILED"
    assert len(cancelled.failed_sub_goals) > 0


def test_restart_recovery_from_checkpoint() -> None:
    executor, store, runner, channel = _make_executor(llm_count=3)
    goal_id = uuid4()
    # Execute fully first to populate store
    state = executor.execute(goal_id, "goal", {}, _valid_token(), max_depth=10)
    assert state.status == "COMPLETED"
    # Simulate recovery
    recovered = executor.recover(goal_id, _valid_token())
    assert recovered is not None
    assert recovered.goal_id == goal_id


def test_token_expires_pauses_goal() -> None:
    channel = FakeChannel()
    store = FakeStore()
    runner = FakeRunner()
    expired_token = CapabilityToken(
        goal_id=uuid4(),
        ttl_seconds=1,
        scopes=frozenset({"all"}),
        issued_at=datetime.now(tz=timezone.utc) - timedelta(seconds=100),
        expires_at=datetime.now(tz=timezone.utc) - timedelta(seconds=90),
        token_id=uuid4(),
    )
    executor = GoalExecutor(
        decomposer=GoalDecomposer(FakeLLM(3)),
        resolver=DependencyResolver(),
        reporter=CheckpointReporter(channel, checkpoint_every_n=3),
        gate=ApprovalGate(FakeApprovalPort(approved=True)),
        runner=runner,
        store=store,
    )
    state = executor.execute(uuid4(), "goal", {}, expired_token, max_depth=10)
    assert state.status == "PAUSED"
    assert len(runner.executed) == 0  # No actions after token expiry


def test_sub_goal_fails_after_3_retries_pauses_goal() -> None:
    executor, store, runner, channel = _make_executor(
        llm_count=3, fail_ids=frozenset({"sg-0"})
    )
    goal_id = uuid4()
    state = executor.execute(goal_id, "goal", {}, _valid_token(), max_depth=10)
    assert state.status == "PAUSED"
    assert "sg-0" in state.failed_sub_goals
