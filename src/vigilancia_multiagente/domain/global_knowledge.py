"""Cross-session memory entity. Persists research session snapshots for cross-session retrieval."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass
class GlobalKnowledgeSnapshot:
    """Persistent snapshot of a research session's findings, entities, and source scores."""

    session_id: UUID
    query_summary: str
    findings_graph: dict | None = None
    embeddings: list[float] | None = None
    entities: list[dict] | None = None
    source_scores: dict | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None
