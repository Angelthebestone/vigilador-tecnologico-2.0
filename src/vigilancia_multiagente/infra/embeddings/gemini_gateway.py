import asyncio
from collections.abc import Sequence
from enum import StrEnum
from math import sqrt
from typing import Any

import httpx

from vigilancia_multiagente.config.settings import get_settings


class TaskType(StrEnum):
    RETRIEVAL_QUERY = "RETRIEVAL_QUERY"
    RETRIEVAL_DOCUMENT = "RETRIEVAL_DOCUMENT"


_TASK_PREFIXES: dict[str, str] = {
    TaskType.RETRIEVAL_QUERY: "query: ",
    TaskType.RETRIEVAL_DOCUMENT: "document: ",
}


class GeminiEmbeddingGateway:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._client = httpx.AsyncClient(base_url="https://generativelanguage.googleapis.com")

    async def close(self) -> None:
        await self._client.aclose()

    async def embed_document(self, text: str) -> list[float]:
        """Embed a document. Equivalent to ``embed(text, RETRIEVAL_DOCUMENT)``."""
        return await self.embed(text, TaskType.RETRIEVAL_DOCUMENT)

    async def embed(
        self, text: str, task_type: TaskType = TaskType.RETRIEVAL_DOCUMENT
    ) -> list[float]:
        """Embed text with a task-specific prefix for retrieval quality.

        Args:
            text: Content to embed.
            task_type: ``RETRIEVAL_QUERY`` (``query: `` prefix) or
                ``RETRIEVAL_DOCUMENT`` (``document: `` prefix).

        Raises:
            ValueError: If text is empty.
            RuntimeError: If ``VT_EMBEDDING_API_KEY`` is not set.
        """
        if not text.strip():
            raise ValueError("text must not be empty")
        if not self._settings.embedding_api_key:
            raise RuntimeError("VT_EMBEDDING_API_KEY is required for embeddings")

        prefix = _TASK_PREFIXES[task_type]
        payload = {
            "model": f"models/{self._settings.embedding_model}",
            "content": {"parts": [{"text": f"{prefix}{text}"}]},
        }
        response = await self._client.post(
            f"/v1beta/models/{self._settings.embedding_model}:embedContent",
            params={"key": self._settings.embedding_api_key.get_secret_value()},
            json=payload,
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        values = _extract_values(data)
        return _normalize_and_validate(values, self._settings.embedding_dimensions)

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Batch embed multiple documents."""
        if not texts:
            raise ValueError("texts must not be empty")
        vectors: list[list[float]] = []
        batch_size = max(1, self._settings.embedding_batch_size)
        for offset in range(0, len(texts), batch_size):
            batch = texts[offset : offset + batch_size]
            vectors.extend(await asyncio.gather(*(self.embed(text) for text in batch)))
        return vectors


def _extract_values(payload: dict[str, Any]) -> list[float]:
    embedding = payload.get("embedding")
    if not isinstance(embedding, dict):
        raise TypeError("Embedding payload missing 'embedding' object")
    values = embedding.get("values")
    if not isinstance(values, list):
        raise TypeError("Embedding payload missing 'values' list")
    return [float(v) for v in values]


def _normalize_and_validate(values: list[float], dimensions: int) -> list[float]:
    if len(values) != dimensions:
        raise ValueError(f"Unexpected embedding dimension {len(values)}; expected {dimensions}")
    magnitude = sqrt(sum(value * value for value in values))
    if magnitude == 0:
        return [0.0 for _ in values]
    return [value / magnitude for value in values]
