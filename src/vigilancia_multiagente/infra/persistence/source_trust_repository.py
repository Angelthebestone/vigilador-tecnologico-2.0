import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy import text

from vigilancia_multiagente.infra.db.connection import Database

logger = logging.getLogger(__name__)


class SourceTrustRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def get_score(self, source_id: str) -> int | None:
        async with self._database.session() as db:
            result = await db.execute(
                text("SELECT current_score FROM source_trust WHERE source_id = :source_id"),
                {"source_id": source_id},
            )
            row = result.one_or_none()
            return row[0] if row else None

    async def record_outcome(self, source_key: str, outcome: Any) -> None:
        """Protocol conformance: maps generic outcome to score update."""
        if isinstance(outcome, dict):
            delta = outcome.get("delta", 0)
            reason = outcome.get("reason", "record_outcome")
        elif isinstance(outcome, int):
            delta = outcome
            reason = "record_outcome"
        else:
            delta = 0
            reason = str(outcome) if outcome else "record_outcome"
        await self.update_score(source_key, delta, reason)

    async def update_score(self, source_id: str, delta: int, reason: str) -> int | None:
        history_entry = json.dumps(
            {"delta": delta, "reason": reason, "timestamp": datetime.utcnow().isoformat()}
        )
        async with self._database.session() as db:
            result = await db.execute(
                text("""
                    INSERT INTO source_trust (source_id, source_type, current_score, score_history, updated_at)
                    VALUES (:source_id, 'domain', GREATEST(10, LEAST(100, 50 + :delta)),
                            CAST(:history AS jsonb), NOW())
                    ON CONFLICT (source_id) DO UPDATE SET
                        current_score = GREATEST(10, LEAST(100, source_trust.current_score + :delta)),
                        score_history = source_trust.score_history || CAST(:history AS jsonb),
                        updated_at = NOW()
                    RETURNING current_score
                """),
                {"source_id": source_id, "delta": delta, "history": history_entry},
            )
            await db.commit()
            row = result.one_or_none()
            if row is None:
                return None
            score = row[0]
            if delta > 0:
                await db.execute(
                    text(
                        "UPDATE source_trust SET confirmation_count = confirmation_count + 1 WHERE source_id = :source_id"
                    ),
                    {"source_id": source_id},
                )
            elif delta < 0:
                await db.execute(
                    text(
                        "UPDATE source_trust SET contradiction_count = contradiction_count + 1 WHERE source_id = :source_id"
                    ),
                    {"source_id": source_id},
                )
            await db.commit()
            return score

    async def get_top_sources(self, limit: int = 10, source_type: str | None = None) -> list[dict]:
        async with self._database.session() as db:
            if source_type:
                result = await db.execute(
                    text("""
                        SELECT source_id, source_type, current_score, confirmation_count,
                               contradiction_count, last_accessed, updated_at
                        FROM source_trust
                        WHERE source_type = :source_type
                        ORDER BY current_score DESC
                        LIMIT :limit
                    """),
                    {"source_type": source_type, "limit": limit},
                )
            else:
                result = await db.execute(
                    text("""
                        SELECT source_id, source_type, current_score, confirmation_count,
                               contradiction_count, last_accessed, updated_at
                        FROM source_trust
                        ORDER BY current_score DESC
                        LIMIT :limit
                    """),
                    {"limit": limit},
                )
            rows = result.mappings().all()
            return [
                {
                    "source_id": str(row["source_id"]),
                    "source_type": str(row["source_type"]),
                    "current_score": int(row["current_score"]),
                    "confirmation_count": int(row["confirmation_count"]),
                    "contradiction_count": int(row["contradiction_count"]),
                    "last_accessed": row["last_accessed"].isoformat()
                    if row["last_accessed"]
                    else None,
                    "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
                }
                for row in rows
            ]

    async def get_score_map(self, source_type: str = "domain") -> dict[str, float]:
        """Snapshot dominio→score aprendido, para inyectar en scorers síncronos.

        EvidenceLinker / FindingImpactScorer son síncronos; cargan este mapa
        async antes de puntuar para no abrir sesiones de BD por cada URL.
        """
        async with self._database.session() as db:
            result = await db.execute(
                text(
                    "SELECT source_id, current_score FROM source_trust "
                    "WHERE source_type = :source_type"
                ),
                {"source_type": source_type},
            )
            return {
                str(row["source_id"]): float(row["current_score"])
                for row in result.mappings().all()
            }

    async def record_access(self, source_id: str) -> None:
        async with self._database.session() as db:
            await db.execute(
                text("UPDATE source_trust SET last_accessed = NOW() WHERE source_id = :source_id"),
                {"source_id": source_id},
            )
            await db.commit()
