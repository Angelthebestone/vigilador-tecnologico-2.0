"""Event publishing port for SSE session streams."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID


class EventPublisher(Protocol):
    """Append SSE-formatted events for a research session."""

    async def publish(self, session_id: UUID, sse_message: str) -> None: ...
