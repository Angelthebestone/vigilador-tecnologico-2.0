from dataclasses import asdict
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from vigilancia_multiagente.api import audit_logger
from vigilancia_multiagente.api.dependencies import (
    clarification_service,
    event_log,
    minimax_client,
    orchestrator,
    plan_builder,
    plan_repository,
    session_repository,
)
from vigilancia_multiagente.application.events.sse_publisher import SessionEvent, format_sse
from vigilancia_multiagente.domain.models import ResearchPlan
from vigilancia_multiagente.domain.session_state import SessionStatus

router = APIRouter(prefix="/research")


class StartRequest(BaseModel):
    user_query: str = Field(min_length=1)
    scope: dict[str, str] | None = None


class ClarifyRequest(BaseModel):
    answers: dict[str, str]


@router.post("/start")
async def start_research(payload: StartRequest) -> dict[str, object]:
    session = await orchestrator.start_session(payload.user_query, payload.scope)
    audit_logger.debug(
        "SessionStarted: session_id=%s, user_query=%s", session.id, payload.user_query
    )
    questions = await clarification_service.generate_questions(
        payload.user_query, llm=minimax_client
    )
    event = format_sse(
        SessionEvent.now(
            "SessionStarted",
            session.id,
            {"status": session.status, "user_query": payload.user_query},
        )
    )
    event_log[str(session.id)] = [event]
    event_log[str(session.id)].append(
        format_sse(
            SessionEvent.now(
                "ClarificationRequested",
                session.id,
                {
                    "questions": [asdict(q) for q in questions],
                },
            )
        )
    )
    return {
        "session_id": str(session.id),
        "status": session.status.lower(),
        "questions": [asdict(question) for question in questions],
    }


@router.post("/{session_id}/clarify")
async def clarify(session_id: str, payload: ClarifyRequest) -> dict[str, object]:
    clarification_service.save_answers(UUID(session_id), payload.answers)
    session = await session_repository.get_by_id(UUID(session_id))
    user_query = session.user_query if session else ""
    # Memoria cross-session: si ya investigamos temas relacionados, arrancar
    # desde el delta en vez de desde cero.
    preload_context = await orchestrator.preload_for_session(user_query)
    plan = await plan_builder.build(
        UUID(session_id),
        payload.answers,
        user_query=user_query,
        llm=minimax_client,
        preload_context=preload_context,
    )
    await plan_repository.create(plan)
    audit_logger.debug("PlanGenerated: session_id=%s", session_id)
    session = await orchestrator.transition(UUID(session_id), SessionStatus.PLANNING)
    event_log.setdefault(session_id, []).append(
        format_sse(
            SessionEvent.now(
                "PlanGenerated",
                session.id,
                {
                    "plan_id": str(plan.id),
                    "branches": [branch.branch_type.value for branch in plan.branches],
                    "requires_approval": plan.requires_approval,
                },
            )
        )
    )
    return {
        "session_id": str(session.id),
        "status": "planning",
        "requires_approval": plan.requires_approval,
        "plan": {
            **_plan_payload(plan),
        },
    }


@router.get("/{session_id}/plan")
async def get_plan(session_id: UUID) -> dict[str, object]:
    plan = await plan_repository.get_latest_for_session(session_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    return {
        "session_id": str(session_id),
        "plan": _plan_payload(plan),
    }


def _plan_payload(plan: ResearchPlan) -> dict[str, object]:
    return {
        "id": str(plan.id),
        "version": plan.version,
        "system_base_version": plan.system_base_version,
        "requires_approval": plan.requires_approval,
        "approved_at": plan.approved_at.isoformat() if plan.approved_at else None,
        "global_constraints": plan.global_constraints,
        "branches": [
            {
                "branch_type": branch.branch_type.value.lower(),
                "focus_queries": branch.focus_queries,
                "mcp_providers": branch.mcp_providers,
                "mcp_tool_profile": branch.mcp_tool_profile,
                "priority_weight": branch.priority_weight,
                "status": branch.status.value.lower(),
                "overlay_ref": branch.overlay_ref,
            }
            for branch in plan.branches
        ],
    }
