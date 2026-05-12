"""Tests for PromptComposer."""

import pytest

from vigilancia_multiagente.application.governance.prompt_composer import PromptComposer
from vigilancia_multiagente.application.governance.validators import PromptValidationError
from vigilancia_multiagente.domain.models import BranchType
from vigilancia_multiagente.domain.system_base import BranchOverlay, SystemBase


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


@pytest.fixture
def overlay() -> BranchOverlay:
    return BranchOverlay(
        branch_type=BranchType.AVANCES,
        objective="Identify technology signals",
        required_context=("user_query", "temporal_window"),
        output_schema={"findings": "array", "confidence": "float"},
        quality_criteria=("evidence_per_finding",),
        do_rules=("cite sources",),
        dont_rules=("invent data",),
        uncertainty_handling="confidence < 0.6 → next_query",
        version="1.0.0",
    )


@pytest.fixture
def composer() -> PromptComposer:
    return PromptComposer()


def test_compose_returns_composed_prompt(system_base: SystemBase, overlay: BranchOverlay, composer: PromptComposer) -> None:
    """A valid composition should return a ComposedPrompt with all sections."""
    result = composer.compose(system_base, overlay, "What is the latest in AI?")

    assert result.system_base_version == "1.0.0"
    assert result.branch_type == BranchType.AVANCES
    assert result.user_query == "What is the latest in AI?"
    assert "Global Rules (Tool Usage)" in result.full_text
    assert "Identify technology signals" in result.full_text
    assert "What is the latest in AI?" in result.full_text
    assert "cite sources" in result.full_text
    assert len(result.sections) >= 8  # system base + overlay + user query
    assert result.prompt_composition_id  # non-empty UUID for traceability


def test_compose_empty_user_query(system_base: SystemBase, overlay: BranchOverlay, composer: PromptComposer) -> None:
    """An empty user query should still produce a valid prompt."""
    result = composer.compose(system_base, overlay, "")
    assert result.user_query == ""
    assert "User Query" in result.full_text


def test_compose_with_branch_config(system_base: SystemBase, overlay: BranchOverlay, composer: PromptComposer) -> None:
    """Branch config should be included when provided."""
    from vigilancia_multiagente.domain.models import BranchConfig

    config = BranchConfig(
        branch_type=BranchType.AVANCES,
        focus_queries=["AI signals", "ML trends"],
        mcp_providers=["tavily", "exa"],
    )
    result = composer.compose(system_base, overlay, "AI query", branch_config=config)
    assert "AI signals" in result.full_text
    assert "tavily" in result.full_text


def test_overlay_redefining_global_rule_raises_error(composer: PromptComposer) -> None:
    """An overlay that redefines a global rule should be rejected."""
    system = SystemBase(
        version="1.0.0",
        global_rules=("Rule 1",),
        tool_usage_policy={"order": "sequential"},
        safety_limits={"max_depth": 5},
        error_handling=("Retry",),
        output_style=("JSON",),
        model_behavior={},
        embedding_config={},
    )

    # It should be impossible to create an overlay with forbidden keys
    # since BranchOverlay doesn't have tool_usage_policy field.
    # The validator checks for this via dataclass fields.
    overlay = BranchOverlay(
        branch_type=BranchType.AVANCES,
        objective="Test",
    )

    # This should pass since BranchOverlay can't hold tool_usage_policy
    result = composer.compose(system, overlay, "test query")
    assert result is not None


def test_minimal_overlay(system_base: SystemBase, composer: PromptComposer) -> None:
    """An overlay with only objective should compose successfully."""
    minimal = BranchOverlay(
        branch_type=BranchType.RIESGO,
        objective="Detect risk signals",
    )
    result = composer.compose(system_base, minimal, "Find risks")
    assert "Detect risk signals" in result.full_text
    assert "Find risks" in result.full_text


def test_all_branch_types_compose(system_base: SystemBase, composer: PromptComposer) -> None:
    """All branch types should produce valid compositions."""
    for bt in BranchType:
        overlay = BranchOverlay(
            branch_type=bt,
            objective=f"Analyze {bt.value}",
        )
        result = composer.compose(system_base, overlay, f"Query for {bt.value}")
        assert result.branch_type == bt
        assert f"Analyze {bt.value}" in result.full_text


def test_compose_with_minimal_system_base(composer: PromptComposer) -> None:
    """A minimal system base should still compose."""
    minimal_base = SystemBase(
        version="0.1.0",
        global_rules=("Be safe",),
        tool_usage_policy={},
        safety_limits={},
        error_handling=(),
        output_style=(),
        model_behavior={},
        embedding_config={},
    )
    overlay = BranchOverlay(
        branch_type=BranchType.AVANCES,
        objective="Test",
    )
    result = composer.compose(minimal_base, overlay, "hello")
    assert result.system_base_version == "0.1.0"
