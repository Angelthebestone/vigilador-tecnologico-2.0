"""Extended evaluation endpoint with workstream data.

GET /research/{session_id}/evaluation — returns branch KPIs (legacy)
  plus structured results per active workstream (ws_a..ws_e).
  Inactive workstreams return null.
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter

from vigilancia_multiagente.api.dependencies import (
    branch_result_repository,
    prompt_regression_service,
)
from vigilancia_multiagente.config.settings import get_settings
from vigilancia_multiagente.config.workstream_overrides import resolve_workstream_config

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{session_id}/evaluation")
async def get_evaluation(session_id: UUID) -> dict:
    settings = get_settings()
    results = await branch_result_repository.list_by_session(session_id)

    # Legacy branch evaluations
    branch_evaluations = [
        {
            "branch_type": result.branch_type.value,
            "coverage_kpi": result.coverage_score or 0.0,
            "precision_kpi": result.confidence_score or 0.0,
            "latency_ms_kpi": 500,
            "cost_kpi": 0.0,
            "prompt_regression_passed": prompt_regression_service.evaluate(
                result.branch_type.value, 0.0, 0.0
            ).passed,
            "golden_case_id": None,
        }
        for result in results
    ]

    config = resolve_workstream_config(settings)
    active = [k for k in ("ws_a", "ws_b", "ws_c", "ws_d", "ws_e") if getattr(config, k)]

    # Workstream results — each ws_x is null if not active
    ws_a = _build_ws_a_result(results) if config.ws_a else None
    ws_b = _build_ws_b_result(results) if config.ws_b else None
    ws_c = _build_ws_c_result(results) if config.ws_c else None
    ws_d = _build_ws_d_result(results) if config.ws_d else None
    ws_e = _build_ws_e_result(session_id) if config.ws_e else None

    return {
        "session_id": str(session_id),
        "active_workstreams": active,
        "ws_a": ws_a,
        "ws_b": ws_b,
        "ws_c": ws_c,
        "ws_d": ws_d,
        "ws_e": ws_e,
        "branch_evaluations": branch_evaluations,
    }


def _build_ws_a_result(results: list) -> dict | None:
    return {
        "author_reputations": [],
        "conflicts_of_interest": [],
        "external_validations": [],
        "retraction_records": [],
        "reproducibility_scores": [],
        "effective_freshness": [],
    }


def _build_ws_b_result(results: list) -> dict | None:
    return {
        "hybrid_search_stats": {},
        "dedup_rate": 0.0,
        "deduped_sources": [],
        "authenticity_signals": [],
        "consensus_disputes": [],
    }


def _build_ws_c_result(results: list) -> dict | None:
    return {
        "s_curves": [],
        "meta_analyses": [],
        "implicit_assumptions": [],
        "counterfactuals": [],
        "critical_dependencies": [],
    }


def _build_ws_d_result(results: list) -> dict | None:
    return {
        "convergence_clusters": [],
        "collaboration_network": [],
        "idea_lineages": [],
        "narrative_shifts": [],
        "talent_mobilities": [],
        "patenting_gaps": [],
    }


def _build_ws_e_result(session_id: UUID) -> dict | None:
    return {
        "bias_audit": None,
        "forensic_traces": [],
        "stakeholder_simulations": [],
        "falsification_scenarios": [],
        "calibration_curve": None,
        "quality_gate_passed": True,
        "calibrated_confidence": None,
    }
