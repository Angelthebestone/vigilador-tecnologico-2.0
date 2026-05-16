"""Session timeline and cross-session memory routes."""

import logging

from fastapi import APIRouter

from vigilancia_multiagente.api.dependencies import cross_session_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("/timeline")
async def get_session_timeline():
    """Get a timeline of all research sessions showing how understanding evolved."""
    timeline = await cross_session_service.repository.get_session_timeline()
    return {"sessions": timeline}
