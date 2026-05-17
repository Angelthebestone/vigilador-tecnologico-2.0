"""Routes for system base introspection and debugging (Phase 3 rollout).

These endpoints expose the canonical system base and composed prompt
debug view. Gated behind VT_SYSTEM_BASE_ENABLED feature flag.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException

from vigilancia_multiagente.api.dependencies import (
    governance_loader,
    prompt_composer,
    session_repository,
    system_base,
    system_base_loader,
)
from vigilancia_multiagente.config.settings import get_settings
from vigilancia_multiagente.domain.models import BranchType

router = APIRouter(prefix="/system-base")


def _check_enabled() -> None:
    """Raise 501 if the feature flag is disabled."""
    if not get_settings().system_base_enabled:
        raise HTTPException(
            status_code=501,
            detail="System base feature is disabled. Set VT_SYSTEM_BASE_ENABLED=true to enable.",
        )


@router.get("")
async def get_system_base() -> dict[str, object]:
    """Return the current canonical system base configuration.

    This endpoint exposes the shared source of truth for global agent rules.
    """
    _check_enabled()
    if system_base is None:
        # Try to reload if it wasn't available at startup
        try:
            loaded = system_base_loader.load()
        except Exception as exc:
            raise HTTPException(
                status_code=503, detail=f"System base not available: {exc}"
            ) from exc
    else:
        loaded = system_base

    return {
        "version": loaded.version,
        "global_rules": list(loaded.global_rules),
        "tool_usage_policy": loaded.tool_usage_policy,
        "safety_limits": {k: str(v) for k, v in loaded.safety_limits.items()},
        "error_handling": list(loaded.error_handling),
        "output_style": list(loaded.output_style),
        "model_behavior": {
            k: str(v) if v is not None else None for k, v in loaded.model_behavior.items()
        },
        "embedding_config": {k: str(v) for k, v in loaded.embedding_config.items()},
    }


@router.get("/composed-prompt/{session_id}/{branch_type}")
async def get_composed_prompt(session_id: UUID, branch_type: str) -> dict[str, object]:
    """Debug endpoint — returns the composed prompt for a specific branch.

    This shows how the system base + branch overlay + user query would be
    merged at runtime.
    """
    _check_enabled()
    # Validate branch type
    try:
        bt = BranchType(branch_type.upper())
    except ValueError:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown branch type: {branch_type}. Valid: {[b.value.lower() for b in BranchType]}",
        ) from None

    # Get session for user_query
    session = await session_repository.get_by_id(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Load overlay
    try:
        overlay = governance_loader.load_branch_overlay(bt)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Failed to load overlay: {exc}") from exc

    # Compose
    if system_base is None:
        raise HTTPException(status_code=503, detail="System base not loaded")
    try:
        composed = prompt_composer.compose(
            system_base=system_base,
            overlay=overlay,
            user_query=session.user_query,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Composition failed: {exc}") from exc

    return {
        "session_id": str(session_id),
        "branch_type": bt.value.lower(),
        "system_base_version": system_base.version,
        "system_base_sections": list(composed.sections.keys()),
        "branch_overlay": {
            "objective": overlay.objective,
            "required_context": list(overlay.required_context),
            "do_rules": list(overlay.do_rules),
            "dont_rules": list(overlay.dont_rules),
            "uncertainty_handling": overlay.uncertainty_handling,
        },
        "user_query": session.user_query,
        "composed_prompt": composed.full_text,
    }
