"""Tests for CheckpointReporter: periodic reports, blockers, channel failure, format."""

from __future__ import annotations

from uuid import uuid4

from vigilancia_multiagente.enterprise.orchestration.goal_pursuit.checkpoint_reporter import (
    CheckpointReporter,
    ReportChannelPort,
)
from vigilancia_multiagente.enterprise.orchestration.goal_pursuit.ports import (
    CheckpointReport,
)


class FakeChannel(ReportChannelPort):
    """Fake channel that records sent reports."""

    def __init__(self, available: bool = True) -> None:
        self.reports: list[CheckpointReport] = []
        self.available = available

    def send(self, report: CheckpointReport) -> bool:
        if self.available:
            self.reports.append(report)
            return True
        return False


def test_report_generated_every_n_steps() -> None:
    channel = FakeChannel()
    reporter = CheckpointReporter(channel, checkpoint_every_n=3)
    goal_id = uuid4()
    # Steps 1, 2 should not trigger
    r1 = reporter.step_completed(goal_id, ("s1",), ("s2", "s3"), "partial1")
    r2 = reporter.step_completed(goal_id, ("s1", "s2"), ("s3",), "partial2")
    assert r1 is None
    assert r2 is None
    # Step 3 triggers checkpoint
    r3 = reporter.step_completed(goal_id, ("s1", "s2", "s3"), (), "partial3")
    assert r3 is not None
    assert r3.step_number == 3
    assert r3.completed_steps == ("s1", "s2", "s3")
    assert r3.pending_steps == ()
    assert r3.partial_result == "partial3"


def test_report_on_blocker_detected() -> None:
    channel = FakeChannel()
    reporter = CheckpointReporter(channel, checkpoint_every_n=10)
    goal_id = uuid4()
    # Even at step 1, a blocker triggers immediate report
    r = reporter.step_completed(
        goal_id, ("s1",), ("s2",), "partial", blockers=("API rate limit",)
    )
    assert r is not None
    assert r.blockers == ("API rate limit",)


def test_channel_unavailable_persists_in_log() -> None:
    channel = FakeChannel(available=False)
    reporter = CheckpointReporter(channel, checkpoint_every_n=1)
    goal_id = uuid4()
    r = reporter.step_completed(goal_id, ("s1",), (), "result")
    assert r is not None
    # Report was not delivered but persisted
    assert len(channel.reports) == 0
    persisted = reporter.get_persisted_reports()
    assert len(persisted) == 1
    assert persisted[0].goal_id == goal_id


def test_report_format_has_required_fields() -> None:
    channel = FakeChannel()
    reporter = CheckpointReporter(channel, checkpoint_every_n=1)
    goal_id = uuid4()
    r = reporter.step_completed(
        goal_id, ("a", "b"), ("c",), "partial_result", blockers=(), eta_seconds=120.0
    )
    assert r is not None
    assert r.goal_id == goal_id
    assert r.step_number == 2
    assert r.completed_steps == ("a", "b")
    assert r.pending_steps == ("c",)
    assert r.partial_result == "partial_result"
    assert r.blockers == ()
    assert r.eta_seconds == 120.0
