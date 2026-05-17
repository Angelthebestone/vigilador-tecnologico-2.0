from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/sources", tags=["sources"])


class ScoreAdjustment(BaseModel):
    delta: int = Field(..., ge=-50, le=50, description="Score change (-50 to +50)")
    reason: str = Field(..., min_length=1, max_length=500)


def _get_source_scorer():
    from vigilancia_multiagente.api.dependencies import source_scorer_service

    return source_scorer_service


@router.patch("/{source_id}/score")
async def adjust_source_score(
    source_id: str,
    adjustment: ScoreAdjustment,
    source_scorer=Depends(_get_source_scorer),
):
    new_score = await source_scorer.repository.update_score(
        source_id, adjustment.delta, f"Manual: {adjustment.reason}"
    )
    if new_score is None:
        raise HTTPException(status_code=404, detail="Source not found")

    return {
        "source_id": source_id,
        "new_score": new_score,
        "adjustment": adjustment.delta,
        "reason": adjustment.reason,
    }
