from vigilancia_multiagente.application.evaluation.golden_cases_runner import GoldenCasesRunner


def test_golden_cases_runner_keeps_cases_green():
    runner = GoldenCasesRunner()
    results = runner.run([("case-1", "COMERCIAL"), ("case-2", "RIESGO")])

    assert [result.passed for result in results] == [True, True]
    assert [result.case_id for result in results] == ["case-1", "case-2"]


def test_golden_case_composed_prompt_flow():
    """Golden case: composed prompt for AVANCES branch matches expected structure."""
    from vigilancia_multiagente.application.governance.prompt_composer import PromptComposer
    from vigilancia_multiagente.domain.models import BranchType
    from vigilancia_multiagente.domain.system_base import BranchOverlay, SystemBase

    system_base = SystemBase(
        version="1.0.0",
        global_rules=("Cite sources.", "Declare uncertainty."),
        tool_usage_policy={"order": "sequential"},
        safety_limits={"max_depth": 5},
        error_handling=("Retry once.",),
        output_style=("JSON.",),
        model_behavior={"temperature": 0.3},
        embedding_config={"dimensions": 768},
    )
    overlay = BranchOverlay(
        branch_type=BranchType.AVANCES,
        objective="Identify technology signals.",
        do_rules=("cite sources",),
        dont_rules=("invent data",),
        uncertainty_handling="confidence < 0.6 -> next_query",
    )
    composer = PromptComposer()
    result = composer.compose(system_base, overlay, "Latest breakthroughs in AI")

    # Golden assertions: structure is invariant regardless of system_base version bump
    assert result.system_base_version == "1.0.0"
    assert result.branch_type == BranchType.AVANCES
    assert result.prompt_composition_id
    assert "Cite sources." in result.full_text
    assert "Identify technology signals." in result.full_text
    assert "Latest breakthroughs in AI" in result.full_text
    assert "cite sources" in result.full_text
