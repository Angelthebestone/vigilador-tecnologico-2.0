"""Abstract ports for the Dreaming subsystem — DIP boundaries."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol


class SessionStore(Protocol):
    """Port for reading/marking sessions."""

    async def get_unconsolidated_sessions(self, tenant_id: str) -> list[dict[str, Any]]: ...

    async def mark_consolidated(self, session_ids: list[str]) -> None: ...


class ConsolidatedMemoryStore(Protocol):
    """Port for persisting consolidated memory entries."""

    async def append(self, entry: dict[str, Any]) -> None: ...

    async def exists(self, session_id: str) -> bool: ...


class LLMSummarizer(Protocol):
    """Port for LLM-based summarization."""

    async def summarize_session(self, session: dict[str, Any]) -> dict[str, Any]: ...


class IngestionConnector(Protocol):
    """Port for a single ingestion connector."""

    @property
    def connector_id(self) -> str: ...

    async def fetch_new_documents(self, since: datetime | None) -> list[dict[str, Any]]: ...

    async def index_documents(self, documents: list[dict[str, Any]]) -> int: ...


class SyncCheckpointStore(Protocol):
    """Port for persisting sync checkpoints per connector."""

    async def get_last_sync(self, connector_id: str) -> datetime | None: ...

    async def set_last_sync(self, connector_id: str, ts: datetime) -> None: ...
