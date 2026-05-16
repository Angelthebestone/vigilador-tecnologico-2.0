from uuid import UUID

from fastapi import APIRouter, HTTPException

from vigilancia_multiagente.api.dependencies import conversation_service

router = APIRouter(prefix="/sessions", tags=["conversation"])


@router.post("/{session_id}/ask")
async def ask_follow_up(session_id: UUID, body: dict) -> dict:
    """Ask a follow-up question after research completes."""
    query = body.get("query", "")
    if not query:
        raise HTTPException(status_code=400, detail="query is required")

    result = await conversation_service.needs_supplementary_search(session_id, query)
    if result.get("needs_search"):
        return {"requires_permission": True, "prompt": result["prompt"]}

    return result["answer"]


@router.delete("/{session_id}/conversation")
async def end_conversation(session_id: UUID) -> dict:
    """Explicitly end a conversation session."""
    conversation_service.end_session(session_id)
    return {"status": "ended"}
