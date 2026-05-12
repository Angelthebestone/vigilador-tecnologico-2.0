from datetime import UTC, datetime
from uuid import UUID, uuid4

from vigilancia_multiagente.domain.models import ResearchSession
from vigilancia_multiagente.domain.repositories import SessionRepository
from vigilancia_multiagente.domain.session_state import SessionStatus, ensure_transition


class OrchestratorService:
    def __init__(self, session_repository: SessionRepository) -> None:
        self._session_repository = session_repository

    async def start_session(self, user_query: str, scope: dict[str, str] | None = None) -> ResearchSession:
        now = datetime.now(UTC)
        session = ResearchSession(
            id=uuid4(),
            created_at=now,
            updated_at=now,
            status=SessionStatus.CLARIFYING,
            user_query=user_query,
            scope=scope,
        )
        return await self._session_repository.create(session)

    async def transition(self, session_id: UUID, target: SessionStatus) -> ResearchSession:
        session = await self._session_repository.get_by_id(session_id)
        if session is None:
            raise KeyError(f"Session not found: {session_id}")
        ensure_transition(session.status, target)
        session.status = target
        session.updated_at = datetime.now(UTC)
        return await self._session_repository.update(session)

