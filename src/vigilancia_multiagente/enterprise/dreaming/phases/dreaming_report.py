"""Phase 10 — Dreaming Report: generate end-of-cycle summary report."""

from __future__ import annotations

import time
from typing import Any, Protocol

from vigilancia_multiagente.enterprise.dreaming.models import (
    CycleReport,
    DreamingContext,
    PhaseResult,
    PhaseStatus,
)


class ReportRenderer(Protocol):
    """Port for rendering the dreaming report."""

    async def render(self, report_data: dict[str, Any]) -> str: ...


class ReportDelivery(Protocol):
    """Port for delivering the report to the user's preferred channel."""

    async def deliver(self, content: str, channel: str) -> None: ...


class PendingApprovalsStore(Protocol):
    """Port for querying pending approvals."""

    async def get_pending(self) -> list[dict[str, Any]]: ...


class DreamingReportPhase:
    """Generates and delivers the end-of-cycle dreaming report."""

    def __init__(
        self,
        renderer: ReportRenderer,
        delivery: ReportDelivery,
        approvals_store: PendingApprovalsStore,
        delivery_channel: str = "log",
    ) -> None:
        self._renderer = renderer
        self._delivery = delivery
        self._approvals_store = approvals_store
        self._delivery_channel = delivery_channel
        self._cycle_report: CycleReport | None = None

    @property
    def name(self) -> str:
        return "dreaming_report"

    def set_cycle_report(self, report: CycleReport) -> None:
        """Inject the current cycle report before execution."""
        self._cycle_report = report

    async def execute(self, context: DreamingContext) -> PhaseResult:
        t0 = time.perf_counter()
        pending = await self._approvals_store.get_pending()
        report_data: dict[str, Any] = {
            "cycle_id": context.cycle_id,
            "started_at": context.started_at.isoformat(),
            "pending_approvals": pending,
            "phase_results": (
                [
                    {"phase": r.phase_name, "status": r.status.value, "metrics": r.metrics_dict}
                    for r in self._cycle_report.results
                ]
                if self._cycle_report
                else []
            ),
        }
        content = await self._renderer.render(report_data)
        await self._delivery.deliver(content, self._delivery_channel)

        duration_ms = (time.perf_counter() - t0) * 1000
        return PhaseResult(
            phase_name=self.name,
            status=PhaseStatus.SUCCESS,
            duration_ms=duration_ms,
            metrics_dict={"pending_approvals": len(pending), "delivered_to": self._delivery_channel},
        )
