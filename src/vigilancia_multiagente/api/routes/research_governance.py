from uuid import UUID

from fastapi import APIRouter

from vigilancia_multiagente.api.dependencies import (
    branch_coordinator,
    governance_loader,
)
from vigilancia_multiagente.api.routes.research_evaluation import router as evaluation_router

router = APIRouter(prefix="/research")
router.include_router(evaluation_router)


@router.get("/{session_id}/iterations")
async def get_iterations(session_id: UUID) -> dict[str, object]:
    return {
        "session_id": str(session_id),
        "items": branch_coordinator.get_iterations(session_id),
        "semantic_relations": branch_coordinator.get_relations(session_id),
    }


@router.get("/{session_id}/agent-contracts")
async def get_agent_contracts(session_id: UUID) -> dict[str, object]:
    skill_matrix = governance_loader.load_skill_matrix()
    branch_overlays = [
        governance_loader.load_branch_overlay(branch_type) for branch_type in skill_matrix
    ]
    return {
        "session_id": str(session_id),
        "skill_matrix": [
            {
                "branch_type": policy.branch_type.value,
                "allowed_tools": list(policy.allowed_tools),
                "tool_order": list(policy.tool_order),
                "timeout_ms_per_tool": policy.timeout_ms_per_tool,
                "retry_limit_per_tool": policy.retry_limit_per_tool,
                "substitution_policy": policy.substitution_policy,
            }
            for policy in skill_matrix.values()
        ],
        "branch_overlays": [
            {
                "branch_type": overlay.branch_type.value,
                "objective": overlay.objective,
                "required_context": list(overlay.required_context),
                "output_schema": overlay.output_schema,
                "quality_criteria": list(overlay.quality_criteria),
                "do_rules": list(overlay.do_rules),
                "dont_rules": list(overlay.dont_rules),
                "uncertainty_handling": overlay.uncertainty_handling,
                "version": overlay.version,
            }
            for overlay in branch_overlays
        ],
    }



