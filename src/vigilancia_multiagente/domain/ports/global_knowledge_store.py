from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from vigilancia_multiagente.domain.global_knowledge import GlobalKnowledgeSnapshot


class GlobalKnowledgeStore(Protocol):
    """Persist and retrieve cross-session knowledge snapshots."""

    async def save_snapshot(self, snapshot: GlobalKnowledgeSnapshot) -> None: ...

    async def get_snapshot(self, session_id: UUID) -> GlobalKnowledgeSnapshot | None: ...

    async def find_related(
        self, query_embedding: list[float], limit: int = 5
    ) -> list[dict[str, Any]]: ...

    async def get_session_timeline(self) -> list[dict[str, Any]]: ...
