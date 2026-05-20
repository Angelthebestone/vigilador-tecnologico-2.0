from __future__ import annotations

from enum import StrEnum
from typing import Any, Protocol


class TaskType(StrEnum):
    RETRIEVAL_QUERY = "RETRIEVAL_QUERY"
    RETRIEVAL_DOCUMENT = "RETRIEVAL_DOCUMENT"


class EmbeddingGateway(Protocol):
    """Embed documents and queries into vectors."""

    async def embed(self, text: str, task_type: TaskType = TaskType.RETRIEVAL_DOCUMENT) -> list[float]: ...

    async def embed_document(self, text: str) -> list[float]: ...

    async def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
