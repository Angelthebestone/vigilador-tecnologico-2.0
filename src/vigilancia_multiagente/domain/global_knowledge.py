"""Cross-session memory entity. Persists research session snapshots for cross-session retrieval."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID
from typing import Optional


@dataclass
class GlobalKnowledgeSnapshot:
    """Persistent snapshot of a research session's findings, entities, and source scores."""

    session_id: UUID
    query_summary: str
    findings_graph: Optional[dict] = None
    embeddings: Optional[list[float]] = None
    entities: Optional[list[dict]] = None
    source_scores: Optional[dict] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
