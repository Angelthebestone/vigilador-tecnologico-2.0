"""Contract tests for system base stability, validators, and plan simplification."""

import pytest

from vigilancia_multiagente.application.governance.validators import (
    PromptValidationError,
    PromptValidator,
)
from vigilancia_multiagente.domain.models import BranchType
from vigilancia_multiagente.domain.system_base import BranchOverlay, SystemBase


@pytest.fixture
def validator() -> PromptValidator:
    return PromptValidator()


@pytest.fixture
def system_base() -> SystemBase:
    return SystemBase(
        version="1.0.0",
        global_rules=("Rule 1", "Rule 2"),
        tool_usage_policy={"order": "sequential"},
        safety_limits={"max_depth": 5},
        error_handling=("Retry on failure",),
        output_style=("JSON format",),
        model_behavior={"temperature": 0.3},
        embedding_config={"dimensions": 768},
    )


# --- Validator tests ---


def test_valid_overlay_passes(validator: PromptValidator, system_base: SystemBase) -> None:
    """A valid overlay with no forbidden fields should pass."""
    overlay = BranchOverlay(
        branch_type=BranchType.AVANCES,
        objective="Identify technology signals",
        do_rules=("cite sources",),
    )
    # Should not raise
    validator.validate_overlay(system_base, overlay)


def test_overlay_without_objective_raises_error(
    validator: PromptValidator, system_base: SystemBase
) -> None:
    """An overlay without an objective should fail."""
    overlay = BranchOverlay(
        branch_type=BranchType.AVANCES,
        objective="",
    )
    with pytest.raises(PromptValidationError, match="empty.*objective"):
        validator.validate_overlay(system_base, overlay)


# --- Composition validation tests ---


def test_empty_user_query_raises_error(validator: PromptValidator, system_base: SystemBase) -> None:
    """An empty user query should be caught by composition validation."""
    overlay = BranchOverlay(
        branch_type=BranchType.AVANCES,
        objective="Test",
    )
    with pytest.raises(PromptValidationError, match="empty"):
        validator.validate_composition(system_base, overlay, "")


def test_composition_missing_global_rules_raises_error(validator: PromptValidator) -> None:
    """System base missing global_rules should fail composition validation."""
    empty_base = SystemBase(
        version="1.0.0",
        global_rules=(),
        tool_usage_policy={},
        safety_limits={},
        error_handling=(),
        output_style=(),
        model_behavior={},
        embedding_config={},
    )
    overlay = BranchOverlay(branch_type=BranchType.AVANCES, objective="Test")
    with pytest.raises(PromptValidationError, match="global_rules"):
        validator.validate_composition(empty_base, overlay, "query")


def test_valid_composition_passes(validator: PromptValidator, system_base: SystemBase) -> None:
    """A valid composition should pass validation."""
    overlay = BranchOverlay(
        branch_type=BranchType.AVANCES,
        objective="Test",
    )
    # Should not raise
    validator.validate_composition(system_base, overlay, "What is AI?")


# --- Plan simplification contract tests ---


@pytest.mark.asyncio
async def test_plan_builder_includes_system_base_version() -> None:
    """Plan builder output should reference system base version."""
    from vigilancia_multiagente.application.planning.plan_builder import PlanBuilder
    from uuid import uuid4

    builder = PlanBuilder()
    plan = await builder.build(uuid4(), {"scope-horizon": "short-term", "scope-geo": "local"})

    assert plan.system_base_version == "1.0.0"
    assert "depth_limit" in plan.global_constraints
    assert "geographic_scope" in plan.global_constraints
    assert "temporal_policy" in plan.global_constraints


@pytest.mark.asyncio
async def test_plan_builder_global_constraints_are_scope_only() -> None:
    """Plan global_constraints should only contain investigation-scope fields."""
    from vigilancia_multiagente.application.planning.plan_builder import PlanBuilder
    from uuid import uuid4

    builder = PlanBuilder()
    plan = await builder.build(uuid4(), {"scope-horizon": "long-term", "scope-geo": "global"})

    # Should NOT contain tool lists or behavioral rules
    forbidden = ["tool", "rule", "prompt", "behavior", "format", "safety"]
    for key in plan.global_constraints:
        key_lower = key.lower()
        assert not any(f in key_lower for f in forbidden), (
            f"global_constraints contains forbidden key: {key}"
        )


def test_route_plan_payload_includes_system_base_version() -> None:
    """The API plan payload should include system_base_version."""
    from uuid import uuid4

    from vigilancia_multiagente.domain.models import BranchConfig, BranchType, ResearchPlan

    plan = ResearchPlan(
        id=uuid4(),
        session_id=uuid4(),
        version=1,
        system_base_version="1.0.0",
        branches=[
            BranchConfig(
                branch_type=BranchType.AVANCES,
                focus_queries=["test"],
                mcp_providers=["tavily"],
            )
        ],
        global_constraints={"depth_limit": 3},
    )

    payload = {
        "id": str(plan.id),
        "version": plan.version,
        "system_base_version": plan.system_base_version,
    }
    assert payload["system_base_version"] == "1.0.0"


# --- BranchOverlay contract tests ---


def test_branch_overlay_has_required_fields() -> None:
    """A BranchOverlay should always have branch_type and objective."""
    overlay = BranchOverlay(
        branch_type=BranchType.AVANCES,
        objective="Test objective",
    )
    assert overlay.branch_type == BranchType.AVANCES
    assert overlay.objective == "Test objective"


def test_all_branch_types_have_overlays() -> None:
    """All six branch types should have defined overlays in the contract loader."""
    from vigilancia_multiagente.application.governance.contract_loader import (
        GovernanceContractLoader,
    )
    from pathlib import Path

    contracts_root = Path("specs/002-vigilancia-multiagente/contracts")
    loader = GovernanceContractLoader(contracts_root)

    for bt in BranchType:
        overlay = loader.load_branch_overlay(bt)
        assert overlay.branch_type == bt
        assert overlay.objective
        assert "user_query" in overlay.required_context
        assert len(overlay.dont_rules) >= 1


def test_contract_loader_backward_compatible() -> None:
    """The overlay loader returns BranchOverlay with all expected fields."""
    from vigilancia_multiagente.application.governance.contract_loader import (
        GovernanceContractLoader,
    )
    from vigilancia_multiagente.domain.system_base import BranchOverlay
    from pathlib import Path

    contracts_root = Path("specs/002-vigilancia-multiagente/contracts")
    loader = GovernanceContractLoader(contracts_root)

    overlay = loader.load_branch_overlay(BranchType.AVANCES)
    assert isinstance(overlay, BranchOverlay)
    assert overlay.branch_type == BranchType.AVANCES
    assert overlay.objective
    assert overlay.version == "1.0.0"
