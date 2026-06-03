# ROADMAP F5b - fuera de MVP 021; no registrar en runtime
"""Phase 4 — Config refresher: detect COMPANY gaps and propose updates."""

from __future__ import annotations

import time
from typing import Any, Protocol

from vigilancia_multiagente.enterprise.dreaming.models import (
    DreamingContext,
    PhaseResult,
    PhaseStatus,
)


class GapDetector(Protocol):
    """Port for detecting knowledge gaps in COMPANY config."""

    async def detect_gaps(self, tenant_id: str) -> list[dict[str, Any]]: ...


class ProposalGenerator(Protocol):
    """Port for generating config update proposals via LLM."""

    async def generate_proposal(self, gap: dict[str, Any]) -> dict[str, Any]: ...


class ConfigProposalApplier(Protocol):
    """Port for applying config proposals (via AgentModifier or direct)."""

    async def apply_direct(self, proposal: dict[str, Any]) -> None: ...

    async def enqueue_approval(self, proposal: dict[str, Any]) -> None: ...


SENSITIVE_FILES = {"identity.md", "policies.md"}


class ConfigRefresherPhase:
    """Detects gaps in COMPANY config, generates proposals, applies or enqueues."""

    def __init__(
        self,
        gap_detector: GapDetector,
        proposal_generator: ProposalGenerator,
        applier: ConfigProposalApplier,
    ) -> None:
        self._gap_detector = gap_detector
        self._proposal_generator = proposal_generator
        self._applier = applier

    @property
    def name(self) -> str:
        return "config_refresher"

    async def execute(self, context: DreamingContext) -> PhaseResult:
        if not context.llm_available:
            return PhaseResult(
                phase_name=self.name,
                status=PhaseStatus.SKIPPED,
                duration_ms=0.0,
                error="LLM not available",
            )

        t0 = time.perf_counter()
        gaps = await self._gap_detector.detect_gaps(context.tenant_id)
        applied = 0
        enqueued = 0

        for gap in gaps:
            proposal = await self._proposal_generator.generate_proposal(gap)
            target_file = proposal.get("target_file", "")
            if target_file in SENSITIVE_FILES:
                await self._applier.enqueue_approval(proposal)
                enqueued += 1
            else:
                await self._applier.apply_direct(proposal)
                applied += 1

        duration_ms = (time.perf_counter() - t0) * 1000
        return PhaseResult(
            phase_name=self.name,
            status=PhaseStatus.SUCCESS,
            duration_ms=duration_ms,
            metrics_dict={
                "gaps_detected": len(gaps),
                "applied_direct": applied,
                "enqueued_approval": enqueued,
            },
        )
