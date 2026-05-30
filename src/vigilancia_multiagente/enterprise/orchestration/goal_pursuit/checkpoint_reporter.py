"""CheckpointReporter: reports progress at configured intervals."""

from __future__ import annotations

import logging
from uuid import UUID

from vigilancia_multiagente.enterprise.orchestration.goal_pursuit.ports import (
    CheckpointReport,
)

logger = logging.getLogger(__name__)


class ReportChannelPort:
    """Port for sending reports to the user channel."""

    def send(self, report: CheckpointReport) -> bool:
        """Send report. Return True if delivered, False if channel unavailable."""
        raise NotImplementedError


class CheckpointReporter:
    """Monitors progress and generates reports every N steps or on blockers."""

    def __init__(self, channel: ReportChannelPort, checkpoint_every_n: int = 3) -> None:
        self._channel = channel
        self._checkpoint_every_n = checkpoint_every_n
        self._steps_since_last_report = 0
        self._persisted_reports: list[CheckpointReport] = []

    def step_completed(
        self,
        goal_id: UUID,
        completed: tuple[str, ...],
        pending: tuple[str, ...],
        partial_result: str,
        blockers: tuple[str, ...] = (),
        eta_seconds: float | None = None,
    ) -> CheckpointReport | None:
        """Record a step completion. Returns report if checkpoint triggered."""
        self._steps_since_last_report += 1

        should_report = (
            self._steps_since_last_report >= self._checkpoint_every_n
            or len(blockers) > 0
        )

        if not should_report:
            return None

        report = CheckpointReport(
            goal_id=goal_id,
            step_number=len(completed),
            completed_steps=completed,
            pending_steps=pending,
            partial_result=partial_result,
            blockers=blockers,
            eta_seconds=eta_seconds,
        )

        self._deliver(report)
        self._steps_since_last_report = 0
        return report

    def _deliver(self, report: CheckpointReport) -> None:
        """Attempt delivery; persist in log if channel unavailable."""
        delivered = self._channel.send(report)
        if not delivered:
            logger.warning(
                "Channel unavailable for goal %s step %d; persisted in log",
                report.goal_id,
                report.step_number,
            )
            self._persisted_reports.append(report)

    def get_persisted_reports(self) -> list[CheckpointReport]:
        """Query: return reports that could not be delivered."""
        return list(self._persisted_reports)

    @property
    def checkpoint_every_n(self) -> int:
        """Query: configured checkpoint interval."""
        return self._checkpoint_every_n
