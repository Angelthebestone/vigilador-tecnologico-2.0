from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass
class SessionContinuationState:
    """In-memory state for post-research Q&A."""

    session_id: UUID
    research_graph: Any | None = None
    findings_list: list[dict] = field(default_factory=list)
    source_registry: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_active_at: datetime = field(default_factory=datetime.utcnow)
    supplementary_count: int = 0
