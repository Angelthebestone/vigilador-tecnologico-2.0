"""Loop 2 — Writing style learning: analyze approved emails and update style profile."""

from __future__ import annotations

from typing import Any, Protocol

from vigilancia_multiagente.enterprise.dreaming.models import DreamingContext


class EmailAnalyzer(Protocol):
    """Port for analyzing approved/sent emails."""

    async def get_recent_emails(self, tenant_id: str, days: int) -> list[dict[str, Any]]: ...

    async def extract_style_stats(self, emails: list[dict[str, Any]]) -> dict[str, Any]: ...


class StyleProfileUpdater(Protocol):
    """Port for updating writing style profile via AgentModifier."""

    async def update(self, stats: dict[str, Any]) -> None: ...

    async def get_baseline(self, days: int) -> dict[str, Any] | None: ...


class WritingStyleLoop:
    """Analyzes emails, updates style profile, flags severe drift."""

    DRIFT_THRESHOLD = 0.3

    def __init__(
        self,
        analyzer: EmailAnalyzer,
        updater: StyleProfileUpdater,
    ) -> None:
        self._analyzer = analyzer
        self._updater = updater

    async def run(self, context: DreamingContext) -> dict[str, Any]:
        emails = await self._analyzer.get_recent_emails(context.tenant_id, days=7)
        if not emails:
            return {"emails_analyzed": 0, "drift_detected": False}

        stats = await self._analyzer.extract_style_stats(emails)
        baseline = await self._updater.get_baseline(days=30)
        drift_detected = False

        if baseline:
            drift_score = self._compute_drift(stats, baseline)
            drift_detected = drift_score > self.DRIFT_THRESHOLD

        await self._updater.update(stats)
        return {
            "emails_analyzed": len(emails),
            "drift_detected": drift_detected,
            "flagged_for_review": drift_detected,
        }

    def _compute_drift(self, current: dict[str, Any], baseline: dict[str, Any]) -> float:
        """Simple drift score: fraction of metrics that changed significantly."""
        if not baseline:
            return 0.0
        diffs = 0
        total = 0
        for key in current:
            if key in baseline:
                total += 1
                if (
                    isinstance(current[key], (int, float))
                    and isinstance(baseline[key], (int, float))
                    and baseline[key] != 0
                ):
                    change = abs(current[key] - baseline[key]) / abs(baseline[key])
                    if change > 0.25:
                        diffs += 1
        return diffs / total if total > 0 else 0.0
