"""DELETE /research/{session_id} — remove a research session and all cascaded data."""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException

from vigilancia_multiagente.api.dependencies import session_repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/research", tags=["research"])


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    try:
        sid = UUID(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid session ID format") from exc

    session = await session_repository.get_by_id(sid)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    await session_repository.delete(sid)
    logger.info("Deleted session %s", session_id)
    return {"status": "deleted", "sessionId": session_id}
