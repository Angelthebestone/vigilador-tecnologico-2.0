"""Enterprise dispatcher HTTP endpoint (Spec 021 F4a.H / T121).

Single ``POST /api/v2/enterprise/dispatch`` endpoint that drives the
end-to-end flow ``ChannelGateway → ModeResolver → ModeContext →
ComplexityClassifier → PlaybookRunner → ToolRegistry``. Returns a
structured response so the frontend / channel adapters can render the
playbook output uniformly across modes.

D4: NO user authentication (FR-038).
"""

from __future__ import annotations

import logging
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/enterprise", tags=["enterprise-dispatch"])


class DispatchRequestBody(BaseModel):
    session_id: str | None = Field(
        default=None,
        description="Optional session id; auto-generated if absent.",
    )
    message: str = Field(..., min_length=1, max_length=4_000)
    channel_id: str = Field(default="chat")
    mode_hint: str | None = Field(
        default=None,
        description="Explicit /mode <id> override; bypasses the cascade.",
    )


@router.post("/dispatch", status_code=200)
async def dispatch_request(body: DispatchRequestBody, request: Request):
    dispatcher = getattr(request.app.state, "dispatcher", None)
    if dispatcher is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "dispatcher not configured. Enterprise composition either "
                "failed at boot or settings.enterprise_enabled is False."
            ),
        )

    from vigilancia_multiagente.enterprise.orchestration.dispatcher import (
        DispatcherInputError,
        DispatcherUnavailableError,
        DispatchRequest,
    )

    session_id = body.session_id or str(uuid4())
    try:
        result = await dispatcher.dispatch(
            DispatchRequest(
                session_id=session_id,
                message=body.message,
                channel_id=body.channel_id,
                mode_hint=body.mode_hint,
            )
        )
    except DispatcherInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except DispatcherUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    run = result.run_result
    return {
        "session_id": result.session_id,
        "resolved_mode": result.resolved_mode,
        "playbook_id": result.playbook_id,
        "complexity": result.complexity,
        "complexity_reason": result.complexity_reason,
        "completed_steps": run.completed_steps,
        "total_llm_calls": run.total_llm_calls,
        "duration_s": round(run.duration_s, 3),
        "outputs": run.outputs,
    }
