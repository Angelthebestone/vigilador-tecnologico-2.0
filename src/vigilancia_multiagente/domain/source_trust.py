from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class ScoreChange:
    delta: int
    reason: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SourceTrustRecord:
    source_id: str
    source_type: str
    current_score: int = 50
    confirmation_count: int = 0
    contradiction_count: int = 0
    last_accessed: Optional[datetime] = None
    score_history: list[ScoreChange] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    MIN_SCORE = 10
    MAX_SCORE = 100
    INITIAL_SCORE = 50
