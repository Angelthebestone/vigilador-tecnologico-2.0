from __future__ import annotations

from typing import Any, Protocol


class VectorIndex(Protocol):
    """Vector similarity search and upsert."""

    async def upsert(self, record: Any) -> None: ...

    async def list_by_session(self, session_id: Any, limit: int = 100) -> list[Any]: ...
