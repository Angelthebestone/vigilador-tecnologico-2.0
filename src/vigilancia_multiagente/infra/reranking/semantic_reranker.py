"""Reranker semántico: reordena resultados por relevancia real a la query.

Los proveedores MCP devuelven N resultados ordenados por su propia relevancia
(opaca y heterogénea entre proveedores). Un reranker cross-encoder los reordena
contra la pregunta original, subiendo lo que de verdad responde.

Estrategia: Cohere Rerank si hay `VT_COHERE_API_KEY`; si no, fallback a
similitud coseno con los embeddings Gemini que el sistema ya usa (sin clave
nueva, degradación elegante igual que el resto del proyecto).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

from vigilancia_multiagente.config.settings import get_settings

logger = logging.getLogger(__name__)

_COHERE_RERANK_URL = "https://api.cohere.com/v2/rerank"
_COHERE_MODEL = "rerank-v3.5"


@dataclass(slots=True)
class RankedDocument:
    index: int  # posición original en la lista de entrada
    text: str
    score: float  # relevancia [0,1], mayor = más relevante


class SemanticReranker:
    def __init__(self, embedding_gateway=None) -> None:
        self._settings = get_settings()
        self._embedding_gateway = embedding_gateway

    async def rerank(
        self,
        query: str,
        documents: list[str],
        top_n: int | None = None,
    ) -> list[RankedDocument]:
        """Devuelve *documents* reordenados por relevancia a *query*.

        Resiliente: si Cohere falla o no hay clave ni embeddings, devuelve el
        orden original (no rompe el pipeline).
        """
        if not documents:
            return []

        key = self._settings.cohere_api_key
        if key is not None:
            try:
                return await self._rerank_cohere(query, documents, key.get_secret_value(), top_n)
            except (httpx.HTTPError, KeyError, ValueError) as exc:
                logger.warning("Cohere rerank falló, usando fallback: %s", exc)

        if self._embedding_gateway is not None:
            try:
                return await self._rerank_embeddings(query, documents, top_n)
            except Exception as exc:
                logger.warning("Rerank por embeddings falló, orden original: %s", exc)

        return [RankedDocument(index=i, text=doc, score=0.0) for i, doc in enumerate(documents)][
            : top_n or len(documents)
        ]

    async def _rerank_cohere(
        self, query: str, documents: list[str], api_key: str, top_n: int | None
    ) -> list[RankedDocument]:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                _COHERE_RERANK_URL,
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": _COHERE_MODEL,
                    "query": query,
                    "documents": documents,
                    "top_n": top_n or len(documents),
                },
            )
            response.raise_for_status()
            results = response.json()["results"]
        return [
            RankedDocument(
                index=item["index"],
                text=documents[item["index"]],
                score=float(item["relevance_score"]),
            )
            for item in results
        ]

    async def _rerank_embeddings(
        self, query: str, documents: list[str], top_n: int | None
    ) -> list[RankedDocument]:
        from vigilancia_multiagente.application.research.semantic_relations import (
            cosine_similarity,
        )

        query_vec = await self._embedding_gateway.embed_document(query)
        doc_vecs = await self._embedding_gateway.embed_documents(documents)
        scored = [
            RankedDocument(
                index=i,
                text=documents[i],
                score=round((cosine_similarity(query_vec, vec) + 1) / 2, 6),
            )
            for i, vec in enumerate(doc_vecs)
        ]
        scored.sort(key=lambda d: d.score, reverse=True)
        return scored[: top_n or len(documents)]
