"""Prompt composition from SystemBase + BranchOverlay + user input.

The ``PromptComposer`` merges the canonical system base (global rules),
the branch-specific overlay (domain context), and the user query into
a single composed prompt string. This is the single entry point for
prompt assembly in the agent runtime.
"""

from __future__ import annotations

from uuid import uuid4

from vigilancia_multiagente.application.governance.contract_loader import AgentSkillPolicy
from vigilancia_multiagente.application.governance.validators import PromptValidator
from vigilancia_multiagente.domain.models import BranchConfig
from vigilancia_multiagente.domain.system_base import BranchOverlay, ComposedPrompt, SystemBase
from vigilancia_multiagente.infra.prompts.loader import load_prompt


class PromptComposer:
    """Composes prompts from system base, branch overlay, and user input."""

    def __init__(self, validator: PromptValidator | None = None) -> None:
        self._validator = validator or PromptValidator()

    def compose(
        self,
        system_base: SystemBase,
        overlay: BranchOverlay,
        user_query: str,
        branch_config: BranchConfig | None = None,
        policy: AgentSkillPolicy | None = None,
    ) -> ComposedPrompt:
        """Build the final prompt by merging system base + overlay + user input.

        Args:
            system_base: The canonical system base (global rules).
            overlay: The branch-specific overlay (domain context).
            user_query: The original user query for this session.
            branch_config: Optional branch configuration for additional context.
            policy: Optional skill policy — adds a ``Tools Disponibles`` section
                with tool order, timeout, retry, and fallback per tool.

        Returns:
            A ``ComposedPrompt`` with the full text and section breakdown.

        Raises:
            PromptValidationError: If the overlay redefines global rules.
        """
        self._validator.validate_overlay(system_base, overlay)

        sections: dict[str, str] = {}

        # --- System Base sections ---
        sections["global_rules"] = _fmt_list("Global Rules (Tool Usage)", system_base.global_rules)
        sections["tool_usage_policy"] = _fmt_dict("Tool Usage Policy", system_base.tool_usage_policy)
        sections["safety_limits"] = _fmt_dict("Safety Limits", system_base.safety_limits)
        sections["error_handling"] = _fmt_list("Error Handling", system_base.error_handling)
        sections["output_style"] = _fmt_list("Output Style", system_base.output_style)
        sections["embedding_config"] = _fmt_dict("Embedding Configuration", system_base.embedding_config)

        # --- Branch Overlay sections ---
        sections["objective"] = f"## Objective\n\n{overlay.objective}"
        if overlay.required_context:
            sections["context"] = "## Required Context\n\n" + "\n".join(f"- {ctx}" for ctx in overlay.required_context)
        if overlay.output_schema:
            schema_lines = "\n".join(f"  - `{k}`: {v}" for k, v in overlay.output_schema.items())
            sections["output_schema"] = f"## Output Schema\n\n{schema_lines}"
        if overlay.quality_criteria:
            sections["quality_criteria"] = _fmt_list("Quality Criteria", overlay.quality_criteria)
        if overlay.do_rules:
            sections["do_rules"] = _fmt_list("Do", overlay.do_rules)
        if overlay.dont_rules:
            sections["dont_rules"] = _fmt_list("Don't", overlay.dont_rules)
        if overlay.uncertainty_handling:
            sections["uncertainty_handling"] = f"## Uncertainty Handling\n\n{overlay.uncertainty_handling}"

        # --- Skill Matrix: tools disponibles para esta rama ---
        if policy is not None:
            sections["skill_matrix"] = _render_skill_matrix(policy)

        # --- Tool Usage Guides ---
        if policy is not None:
            tool_sections = []
            for tool in policy.tool_order:
                try:
                    content = load_prompt(f"tools/{tool.split('_')[0]}")
                    tool_sections.append(f"### {tool}\n\n{content}")
                except FileNotFoundError:
                    pass
            if tool_sections:
                sections["tool_usage"] = "## Tool Usage Guides\n\n" + "\n\n".join(tool_sections)

        # --- User input ---
        sections["user_query"] = f"## User Query\n\n{user_query}"

        # Optional branch config context
        if branch_config:
            ctx_parts = [f"- Branch: {branch_config.branch_type.value}"]
            if branch_config.focus_queries:
                ctx_parts.append(f"- Focus queries: {', '.join(branch_config.focus_queries)}")
            if branch_config.mcp_providers:
                ctx_parts.append(f"- MCP providers: {', '.join(branch_config.mcp_providers)}")
            sections["branch_config"] = "## Branch Configuration\n\n" + "\n".join(ctx_parts)

        # --- Assemble full text ---
        ordered_keys = [
            "global_rules",
            "tool_usage_policy",
            "safety_limits",
            "error_handling",
            "output_style",
            "embedding_config",
            "objective",
            "context",
            "output_schema",
            "quality_criteria",
            "do_rules",
            "dont_rules",
            "uncertainty_handling",
            "skill_matrix",
            "tool_usage",
            "user_query",
            "branch_config",
        ]
        parts: list[str] = [
            f"# System Base v{system_base.version}\n",
        ]
        for key in ordered_keys:
            if key in sections:
                parts.append(sections[key])
                parts.append("")

        full_text = "\n".join(parts).strip()

        composed_id = str(uuid4())

        return ComposedPrompt(
            system_base_version=system_base.version,
            branch_type=overlay.branch_type,
            user_query=user_query,
            sections=sections,
            full_text="\n\n".join(sections.values()),
            prompt_composition_id=composed_id,
        )


def _fmt_list(header: str, items: tuple[str, ...]) -> str:
    """Format a tuple of items as a markdown section."""
    if not items:
        return f"## {header}\n\n_None_"
    return f"## {header}\n\n" + "\n".join(f"{i+1}. {item}" for i, item in enumerate(items))


def _fmt_dict(header: str, mapping: dict[str, object]) -> str:
    """Format a dict as a markdown section."""
    if not mapping:
        return f"## {header}\n\n_None_"
    lines = "\n".join(f"- **{k}**: {v}" for k, v in mapping.items())
    return f"## {header}\n\n{lines}"


def _render_skill_matrix(policy: AgentSkillPolicy) -> str:
    """Render the skill matrix as a markdown table of available tools.

    Shows execution order, timeout, retry limit, and fallback tool
    (or ``FAIL branch`` for the last tool).
    """
    order = policy.tool_order
    if not order:
        return f"## Tools Disponibles\n\n_None configured_"

    rows: list[str] = [
        "| Tool | Timeout | Retry | Fallback |",
        "|------|---------|-------|----------|",
    ]
    for i, tool in enumerate(order):
        timeout = policy.timeout_ms_per_tool.get(tool, 30000)
        retry = policy.retry_limit_per_tool.get(tool, 2)
        fallback = order[i + 1] if i + 1 < len(order) else "FAIL branch"
        rows.append(f"| `{tool}` | {timeout}ms | {retry} | {fallback} |")

    return "## Tools Disponibles\n\nOrden de ejecución: " + " → ".join(f"`{t}`" for t in order) + "\n\n" + "\n".join(rows)
