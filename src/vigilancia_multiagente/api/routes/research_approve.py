import logging
from typing import cast
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from vigilancia_multiagente.api.dependencies import (
    approve_research_usecase,
    plan_repository,
    session_repository,
)
from vigilancia_multiagente.domain.models import BranchConfig, BranchType, ResearchPlan

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/research")


class ApproveRequest(BaseModel):
    approved: bool


class ModifyPlanRequest(BaseModel):
    branch_type: BranchType | None = None
    focus_queries: list[str] | None = None
    mcp_providers: list[str] | None = None
    mcp_tool_profile: str | None = None
    priority_weight: int | None = None
    global_constraints: dict[str, object] | None = None


@router.post("/{session_id}/approve")
async def approve_plan(session_id: UUID, payload: ApproveRequest) -> dict[str, object]:
    session = await session_repository.get_by_id(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if not payload.approved:
        return {
            "session_id": str(session_id),
            "status": "rejected",
            "message": "Plan was not approved",
        }

    plan = await plan_repository.get_latest_for_session(session_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")

    # Spec 007 T031: si el ReportQualityGate detecta un sesgo critico durante
    # la sintesis (WS-E activo), bloquea la entrega con HTTP 409 y expone el
    # audit para que el operador decida.
    from vigilancia_multiagente.application.evaluation.report_quality_gate import (
        QualityGateBlocked,
    )

    try:
        result = await approve_research_usecase.execute(session_id, plan)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except QualityGateBlocked as blocked:
        raise HTTPException(
            status_code=409,
            detail={
                "session_id": str(session_id),
                "reason": "critical_bias_detected",
                "categories": blocked.audit.bias_categories,
                "geographic": blocked.audit.geographic_distribution,
                "institutional": blocked.audit.institutional_distribution,
            },
        ) from blocked

    return {
        "session_id": str(result.session_id),
        "status": result.status,
        "message": result.message,
    }


@router.post("/{session_id}/modify")
async def modify_plan(session_id: UUID, payload: ModifyPlanRequest) -> dict[str, object]:
    session = await session_repository.get_by_id(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    plan = await plan_repository.get_latest_for_session(session_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")

    updated_branches: list[BranchConfig] = []
    branch_updated = payload.branch_type is None
    for branch in plan.branches:
        if payload.branch_type is not None and branch.branch_type != payload.branch_type:
            updated_branches.append(branch)
            continue
        branch_updated = True
        updated_branches.append(
            BranchConfig(
                branch_type=branch.branch_type,
                focus_queries=payload.focus_queries or branch.focus_queries,
                mcp_providers=payload.mcp_providers or branch.mcp_providers,
                mcp_tool_profile=payload.mcp_tool_profile
                if payload.mcp_tool_profile is not None
                else branch.mcp_tool_profile,
                priority_weight=payload.priority_weight
                if payload.priority_weight is not None
                else branch.priority_weight,
                status=branch.status,
            )
        )
    if not branch_updated:
        raise HTTPException(status_code=404, detail="Branch not found in plan")

    modified_plan = ResearchPlan(
        id=uuid4(),
        session_id=session_id,
        version=plan.version + 1,
        branches=updated_branches,
        global_constraints=cast(
            "dict[str, str | int | float]",
            {**plan.global_constraints, **(payload.global_constraints or {})},
        ),
        requires_approval=True,
        approved_at=None,
    )
    await plan_repository.create(modified_plan)
    return {
        "session_id": str(session_id),
        "status": "planning",
        "requires_approval": True,
        "plan": _plan_payload(modified_plan),
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
