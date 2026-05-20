from __future__ import annotations

from uuid import UUID

from vigilancia_multiagente.domain.ports.event_publisher import EventPublisher


class InMemoryEventPublisher:
    """Adapter over the module-level event_log dict used at composition root."""

    def __init__(self, store: dict[str, list[str]]) -> None:
        self._store = store

    async def publish(self, session_id: UUID, sse_message: str) -> None:
        self._store.setdefault(str(session_id), []).append(sse_message)
