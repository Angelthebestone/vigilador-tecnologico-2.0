from vigilancia_multiagente.application.evaluation.prompt_regression_service import (
    PromptRegressionService,
)


def test_prompt_regression_gate_thresholds():
    service = PromptRegressionService()

    assert service.evaluate("COMERCIAL", -0.04, -0.01).passed is True
    assert service.evaluate("COMERCIAL", -0.06, 0.0).passed is False
    assert service.evaluate("COMERCIAL", 0.0, -0.06).passed is False


def test_composed_prompt_regression_all_branches():
    """Regression guard: composed prompts for all branch types are non-empty and traceable."""
    from vigilancia_multiagente.application.governance.prompt_composer import PromptComposer
    from vigilancia_multiagente.domain.models import BranchType
    from vigilancia_multiagente.domain.system_base import BranchOverlay, SystemBase

    composer = PromptComposer()
    system_base = SystemBase(
        version="1.0.0",
        global_rules=("Never invent data.", "Always cite sources."),
        tool_usage_policy={"order": "sequential"},
        safety_limits={"max_depth": 5},
        error_handling=("Propagate explicitly.",),
        output_style=("JSON format.",),
        model_behavior={"temperature": 0.3},
        embedding_config={"dimensions": 768},
    )

    for bt in BranchType:
        overlay = BranchOverlay(
            branch_type=bt,
            objective=f"Analyze {bt.value.lower()} domain",
        )
        result = composer.compose(system_base, overlay, "query")
        assert result.prompt_composition_id, f"Missing composition_id for {bt.value}"
        assert result.full_text, f"Empty composed prompt for {bt.value}"
        assert "Never invent data." in result.full_text
