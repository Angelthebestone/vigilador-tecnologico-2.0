"""Protocol for Dreaming phases — each phase implements this contract."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from vigilancia_multiagente.enterprise.dreaming.models import DreamingContext, PhaseResult


@runtime_checkable
class DreamingPhase(Protocol):
    """Contract that every dreaming phase must satisfy."""

    @property
    def name(self) -> str: ...

    async def execute(self, context: DreamingContext) -> PhaseResult: ...
