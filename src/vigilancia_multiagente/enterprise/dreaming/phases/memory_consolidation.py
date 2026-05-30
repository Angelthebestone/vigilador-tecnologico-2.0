"""Phase 1 — Memory consolidation: compress daily sessions into long-term memory."""

from __future__ import annotations

import logging
import time
from typing import Any

from vigilancia_multiagente.enterprise.dreaming.models import (
    DreamingContext,
    PhaseResult,
    PhaseStatus,
)
from vigilancia_multiagente.enterprise.dreaming.ports import (
    ConsolidatedMemoryStore,
    LLMSummarizer,
    SessionStore,
)

logger = logging.getLogger(__name__)


class MemoryConsolidationPhase:
    """Collects unconsolidated sessions, summarizes via LLM, persists to long-term memory."""

    def __init__(
        self,
        session_store: SessionStore,
        memory_store: ConsolidatedMemoryStore,
        summarizer: LLMSummarizer,
    ) -> None:
        self._session_store = session_store
        self._memory_store = memory_store
        self._summarizer = summarizer

    @property
    def name(self) -> str:
        return "memory_consolidation"

    async def execute(self, context: DreamingContext) -> PhaseResult:
        if not context.llm_available:
            return PhaseResult(
                phase_name=self.name,
                status=PhaseStatus.SKIPPED,
                duration_ms=0.0,
                error="LLM not available",
            )

        t0 = time.perf_counter()
        sessions = await self._session_store.get_unconsolidated_sessions(context.tenant_id)
        processed = 0
        skipped = 0
        errors: list[str] = []
        successfully_consolidated_ids: list[str] = []

        for session in sessions:
            session_id: str = session.get("id", "")
            if await self._memory_store.exists(session_id):
                skipped += 1
                continue
            try:
                summary = await self._summarizer.summarize_session(session)
                summary["session_id"] = session_id
                await self._memory_store.append(summary)
                successfully_consolidated_ids.append(session_id)
                processed += 1
            except Exception as exc:
                msg = f"Session {session_id}: {type(exc).__name__}: {exc}"
                logger.error(msg)
                errors.append(msg)

        if successfully_consolidated_ids:
            await self._session_store.mark_consolidated(successfully_consolidated_ids)

        duration_ms = (time.perf_counter() - t0) * 1000
        metrics: dict[str, Any] = {
            "sessions_found": len(sessions),
            "processed": processed,
            "skipped_duplicates": skipped,
            "errors": len(errors),
        }
        return PhaseResult(
            phase_name=self.name,
            status=PhaseStatus.SUCCESS,
            duration_ms=duration_ms,
            metrics_dict=metrics,
        )
