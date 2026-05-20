"""PostgreSQL + pgvector repository for cross-session memory."""

import json
import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import text

from vigilancia_multiagente.domain.global_knowledge import GlobalKnowledgeSnapshot
from vigilancia_multiagente.infra.db.connection import Database

logger = logging.getLogger(__name__)


class GlobalKnowledgeRepository:
    """Repository for persisting and retrieving GlobalKnowledgeSnapshots."""

    def __init__(self, database: Database) -> None:
        self._database = database

    async def get_snapshot(self, session_id: UUID) -> GlobalKnowledgeSnapshot | None:
        async with self._database.session() as db:
            result = await db.execute(
                text("""
                    SELECT session_id, query_summary, findings_graph,
                           entities, source_scores, created_at, expires_at
                    FROM global_knowledge
                    WHERE session_id = :session_id
                """),
                {"session_id": str(session_id)},
            )
            row = result.mappings().one_or_none()
        if row is None:
            return None
        return GlobalKnowledgeSnapshot(
            session_id=UUID(str(row["session_id"])),
            query_summary=str(row["query_summary"]),
            embeddings=None,
            findings_graph=row.get("findings_graph"),
            entities=row.get("entities"),
            source_scores=row.get("source_scores"),
        )

    async def save_snapshot(self, snapshot: GlobalKnowledgeSnapshot) -> None:
        embedding_literal = _vector_literal(snapshot.embeddings) if snapshot.embeddings else None
        async with self._database.session() as db:
            await db.execute(
                text("""
                    INSERT INTO global_knowledge (
                        session_id, query_summary, findings_graph, embedding,
                        entities, source_scores, created_at, expires_at
                    ) VALUES (
                        :session_id, :query_summary, CAST(:findings_graph AS jsonb),
                        CAST(:embedding AS vector),
                        CAST(:entities AS jsonb), CAST(:source_scores AS jsonb),
                        :created_at, :expires_at
                    )
                    ON CONFLICT (session_id)
                    DO UPDATE SET
                        query_summary = EXCLUDED.query_summary,
                        findings_graph = EXCLUDED.findings_graph,
                        embedding = EXCLUDED.embedding,
                        entities = EXCLUDED.entities,
                        source_scores = EXCLUDED.source_scores,
                        expires_at = EXCLUDED.expires_at
                """),
                {
                    "session_id": str(snapshot.session_id),
                    "query_summary": snapshot.query_summary,
                    "findings_graph": _json_dump(snapshot.findings_graph)
                    if snapshot.findings_graph is not None
                    else None,
                    "embedding": embedding_literal,
                    "entities": _json_dump(snapshot.entities)
                    if snapshot.entities is not None
                    else None,
                    "source_scores": _json_dump(snapshot.source_scores)
                    if snapshot.source_scores is not None
                    else None,
                    "created_at": snapshot.created_at,
                    "expires_at": snapshot.expires_at,
                },
            )
            await db.commit()

    async def find_related(self, query_embedding: list[float], limit: int = 5) -> list[dict]:
        vector_literal = _vector_literal(query_embedding)
        async with self._database.session() as db:
            result = await db.execute(
                text("""
                    SELECT session_id, query_summary,
                           1 - (embedding <=> CAST(:query_emb AS vector)) AS similarity
                    FROM global_knowledge
                    WHERE embedding IS NOT NULL
                      AND (expires_at IS NULL OR expires_at > NOW())
                    ORDER BY similarity DESC
                    LIMIT :limit
                """),
                {"query_emb": vector_literal, "limit": limit},
            )
            rows = result.mappings().all()
        return [
            {
                "session_id": UUID(str(row["session_id"])),
                "query_summary": str(row["query_summary"]),
                "similarity": float(row["similarity"]),
            }
            for row in rows
        ]

    async def get_session_timeline(self) -> list[dict]:
        async with self._database.session() as db:
            result = await db.execute(
                text("""
                    SELECT session_id, query_summary,
                           findings_graph IS NOT NULL AS has_graph,
                           COALESCE(JSONB_ARRAY_LENGTH(entities), 0) AS entity_count,
                           created_at, expires_at
                    FROM global_knowledge
                    ORDER BY created_at DESC
                """),
            )
            rows = result.mappings().all()
        return [
            {
                "session_id": str(row["session_id"]),
                "query_summary": str(row["query_summary"]),
                "has_graph": bool(row["has_graph"]),
                "entity_count": int(row["entity_count"]),
                "created_at": row["created_at"].isoformat()
                if hasattr(row["created_at"], "isoformat")
                else str(row["created_at"]),
                "expires_at": row["expires_at"].isoformat()
                if row["expires_at"] and hasattr(row["expires_at"], "isoformat")
                else None,
            }
            for row in rows
        ]

    async def prune_before(self, date: datetime) -> int:
        async with self._database.session() as db:
            result = await db.execute(
                text("DELETE FROM global_knowledge WHERE created_at < :date"),
                {"date": date},
            )
            await db.commit()
        return result.rowcount  # pyright: ignore


def _vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(f"{v:.10f}" for v in vector) + "]"


def _json_dump(value: object) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, default=str)
