from uuid import UUID

from fastapi import APIRouter

from vigilancia_multiagente.api.dependencies import (
    branch_coordinator,
    branch_result_repository,
    governance_loader,
    prompt_regression_service,
)

router = APIRouter(prefix="/research")


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
    prompt_contracts = [governance_loader.load_prompt_template(branch_type) for branch_type in skill_matrix]
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
        "prompt_contracts": [
            {
                "branch_type": contract.branch_type.value,
                "objective": contract.objective,
                "required_context": list(contract.required_context),
                "output_schema": contract.output_schema,
                "quality_criteria": list(contract.quality_criteria),
                "do_rules": list(contract.do_rules),
                "dont_rules": list(contract.dont_rules),
                "uncertainty_handling": contract.uncertainty_handling,
                "version": contract.version,
            }
            for contract in prompt_contracts
        ],
    }


@router.get("/{session_id}/evaluation")
async def get_evaluation(session_id: UUID) -> dict[str, object]:
    results = await branch_result_repository.list_by_session(session_id)
    evaluations = [
        {
            "branch_type": result.branch_type.value,
            "coverage_kpi": result.coverage_score or 0.0,
            "precision_kpi": result.confidence_score or 0.0,
            "latency_ms_kpi": 500,
            "cost_kpi": 0.0,
            "prompt_regression_passed": prompt_regression_service.evaluate(result.branch_type.value, 0.0, 0.0).passed,
            "golden_case_id": None,
        }
        for result in results
    ]
    return {"session_id": str(session_id), "by_branch": evaluations}

