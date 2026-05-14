from collections.abc import Sequence
from dataclasses import dataclass
from math import sqrt
from uuid import UUID, uuid4

from sqlalchemy import text

from vigilancia_multiagente.config.settings import get_settings
from vigilancia_multiagente.infra.db.connection import Database


@dataclass(slots=True, frozen=True)
class VectorRecord:
    session_id: UUID
    content_type: str
    content_ref_id: str
    vector: list[float]


class PostgresVectorIndex:
    def __init__(self, database: Database) -> None:
        self._database = database
        self._settings = get_settings()

    async def upsert(self, record: VectorRecord) -> VectorRecord:
        normalized = _coerce_vector(record.vector, self._settings.embedding_dimensions)
        normalized = _normalize_vector(normalized)
        vector_literal = _vector_literal(normalized)
        async with self._database.session() as db:
            await db.execute(
                text(
                    """
                    INSERT INTO embedding_vectors (
                        id, session_id, content_type, content_ref_id, vector
                    ) VALUES (
                        :id, :session_id, :content_type, :content_ref_id, CAST(:vector AS vector)
                    )
                    ON CONFLICT (session_id, content_type, content_ref_id)
                    DO UPDATE SET vector = EXCLUDED.vector,
                                  updated_at = NOW()
                    """
                ),
                {
                    "id": str(uuid4()),
                    "session_id": str(record.session_id),
                    "content_type": record.content_type,
                    "content_ref_id": record.content_ref_id,
                    "vector": vector_literal,
                },
            )
            await db.commit()
        return VectorRecord(
            session_id=record.session_id,
            content_type=record.content_type,
            content_ref_id=record.content_ref_id,
            vector=normalized,
        )

    async def list_by_session(self, session_id: UUID | None = None, limit: int | None = None) -> list[VectorRecord]:
        query = """
            SELECT session_id, content_type, content_ref_id, vector::text AS vector_text
            FROM embedding_vectors
        """
        params: dict[str, object] = {}
        if session_id is not None:
            query += " WHERE session_id = :session_id"
            params["session_id"] = str(session_id)
        query += " ORDER BY content_type, content_ref_id"
        if limit is not None:
            query += " LIMIT :limit"
            params["limit"] = limit
        async with self._database.session() as db:
            result = await db.execute(text(query), params)
            rows: Sequence = result.mappings().all()
        return [
            VectorRecord(
                session_id=UUID(str(row["session_id"])),
                content_type=str(row["content_type"]),
                content_ref_id=str(row["content_ref_id"]),
                vector=_parse_vector_text(str(row["vector_text"])),
            )
            for row in rows
        ]


def _normalize_vector(vector: list[float]) -> list[float]:
    magnitude = sqrt(sum(component * component for component in vector))
    if magnitude == 0:
        return [0.0 for _ in vector]
    return [component / magnitude for component in vector]


def _coerce_vector(vector: list[float], dimensions: int) -> list[float]:
    if len(vector) == dimensions:
        return vector
    if len(vector) > dimensions:
        return vector[:dimensions]
    return vector + [0.0] * (dimensions - len(vector))


def _vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(f"{value:.10f}" for value in vector) + "]"


def _parse_vector_text(vector_text: str) -> list[float]:
    stripped = vector_text.strip()
    if stripped.startswith("[") and stripped.endswith("]"):
        stripped = stripped[1:-1]
    if not stripped:
        return []
    return [float(part.strip()) for part in stripped.split(",")]
