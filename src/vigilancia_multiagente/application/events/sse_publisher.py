import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID


@dataclass(slots=True, frozen=True)
class SessionEvent:
    name: str
    session_id: UUID
    payload: dict[str, Any]
    timestamp: datetime

    @classmethod
    def now(cls, name: str, session_id: UUID, payload: dict[str, Any]) -> "SessionEvent":
        return cls(
            name=name,
            session_id=session_id,
            payload=payload,
            timestamp=datetime.now(UTC),
        )


def format_sse(event: SessionEvent) -> str:
    envelope = {
        "session_id": str(event.session_id),
        "timestamp": event.timestamp.isoformat(),
        "payload": event.payload,
    }
    return f"event: {event.name}\ndata: {json.dumps(envelope, ensure_ascii=True)}\n\n"

