"""Prompt composition from SystemBase + BranchOverlay + user input.

The ``PromptComposer`` merges the canonical system base (global rules),
the branch-specific overlay (domain context), and the user query into
a single composed prompt string. This is the single entry point for
prompt assembly in the agent runtime.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from uuid import uuid4

from vigilancia_multiagente.application.governance.contract_loader import AgentSkillPolicy
from vigilancia_multiagente.application.governance.validators import PromptValidator
from vigilancia_multiagente.domain.models import BranchConfig
from vigilancia_multiagente.domain.system_base import BranchOverlay, ComposedPrompt, SystemBase
from vigilancia_multiagente.infra.prompts.loader import load_prompt

logger = logging.getLogger(__name__)

_TOOL_PROMPT_NAMES = {
    "tavily_search": "tavily",
    "tavily_extract": "tavily",
    "web_search_exa": "exa",
    "web_fetch_exa": "exa",
    "web_search_advanced_exa": "exa",
    "read_url": "jina",
    "search_web": "jina",
    "guess_datetime_url": "jina",
    "brave_web_search": "brave",
    "brave_news_search": "brave",
    "firecrawl_scrape": "firecrawl",
    "search_google_scholar_key_words": "scholar",
    "search_google_scholar_advanced": "scholar",
    "get_author_info": "scholar",
    "search_papers": "arxiv",
    "download_paper": "arxiv",
    "read_paper": "arxiv",
    "fetch": "fetch",
    "execute_code": "sandbox",
    "list_libraries": "sandbox",
    "visualize": "sandbox",
    "convert_to_markdown": "markitdown",
    "google_search": "serper",
    "google_search_news": "serper",
    "google_search_scholar": "serper",
    "google_search_patents": "serper",
    "google_search_images": "serper",
    "webpage_scrape": "serper",
    "browser_navigate": "playwright",
    "browser_snapshot": "playwright",
    "browser_screenshot": "playwright",
    "browser_click": "playwright",
    "browser_type": "playwright",
    "browser_select_option": "playwright",
    "browser_hover": "playwright",
    "browser_network_requests": "playwright",
    "browser_network_request": "playwright",
    "browser_tabs": "playwright",
    "understand_image": "minimax_image",
    "search_works": "openalex",
    "get_work": "openalex",
    "get_related_works": "openalex",
    "search_by_topic": "openalex",
    "get_work_citations": "openalex",
    "get_work_references": "openalex",
    "get_citation_network": "openalex",
    "get_top_cited_works": "openalex",
    "search_authors": "openalex",
    "search_authors_by_expertise": "openalex",
    "get_author_profile": "openalex",
    "get_author_collaborators": "openalex",
    "search_institutions": "openalex",
    "find_review_articles": "openalex",
    "find_seminal_papers": "openalex",
    "analyze_topic_trends": "openalex",
    "compare_research_areas": "openalex",
    "get_trending_topics": "openalex",
    "analyze_geographic_distribution": "openalex",
    "search_sources": "openalex",
}


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
        cross_branch_context: list[str] | None = None,
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
        sections["tool_usage_policy"] = _fmt_dict(
            "Tool Usage Policy", system_base.tool_usage_policy
        )
        sections["safety_limits"] = _fmt_dict("Safety Limits", system_base.safety_limits)
        sections["error_handling"] = _fmt_list("Error Handling", system_base.error_handling)
        sections["output_style"] = _fmt_list("Output Style", system_base.output_style)
        sections["embedding_config"] = _fmt_dict(
            "Embedding Configuration", system_base.embedding_config
        )

        # --- Branch Overlay sections ---
        sections["objective"] = f"## Objective\n\n{overlay.objective}"
        if overlay.required_context:
            sections["context"] = "## Required Context\n\n" + "\n".join(
                f"- {ctx}" for ctx in overlay.required_context
            )
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
            sections["uncertainty_handling"] = (
                f"## Uncertainty Handling\n\n{overlay.uncertainty_handling}"
            )

        # --- Skill Matrix + Tool Usage Guides: tools disponibles para esta rama ---
        if policy is not None:
            sections["skill_matrix"] = _render_skill_matrix(policy)
            allowed = set(policy.allowed_tools) or set(policy.tool_order)
            tool_sections = []
            seen_guides: set[str] = set()
            for tool in policy.tool_order:
                prompt_name = _TOOL_PROMPT_NAMES.get(tool)
                if prompt_name is None:
                    logger.debug("No tool prompt mapping for %s", tool)
                    continue
                # Una guía documenta TODAS las tools de su proveedor; cargarla
                # una sola vez y filtrar a las tools que esta rama puede usar
                # evita ruido (tools no permitidas) y duplicados.
                if prompt_name in seen_guides:
                    continue
                seen_guides.add(prompt_name)
                try:
                    content = load_prompt(f"tools/{prompt_name}")
                except FileNotFoundError:
                    logger.debug("No tool usage guide found for %s", tool)
                    continue
                filtered = _filter_tool_guide(content, allowed)
                if filtered:
                    tool_sections.append(filtered)
            if tool_sections:
                sections["tool_usage"] = "## Tool Usage Guides\n\n" + "\n\n".join(tool_sections)

        # Hallazgos relevantes que otras ramas ya emitieron: la rama investiga
        # informada en vez de a ciegas, reduciendo redundancia y conectando
        # hallazgos cross-branch.
        if cross_branch_context:
            hints = "\n".join(f"- {h}" for h in cross_branch_context[:10])
            sections["cross_branch_context"] = (
                "## Cross-Branch Context\n\n"
                "Other branches already surfaced these signals — use them to "
                "avoid redundant queries and to connect findings:\n\n" + hints
            )

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
            "cross_branch_context",
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
            full_text=full_text,
            prompt_composition_id=composed_id,
        )


_TOOL_BLOCK_RE = re.compile(r'<tool name="([^"]+)">.*?</tool>', re.DOTALL)
_RULES_BLOCK_RE = re.compile(r"<rules>.*?</rules>", re.DOTALL)


def _filter_tool_guide(content: str, allowed: set[str]) -> str:
    """Keep only ``<tool>`` blocks whose name is in *allowed*.

    A guide file documents every tool of its provider (e.g. all 20 OpenAlex
    tools). A branch may only use a few. Stripping the non-allowed blocks
    removes prompt noise that would otherwise dilute tool-selection focus,
    while the trailing ``<rules>`` block (compact selection guidance) is kept.

    Falls back to the full content if no ``<tool>`` blocks are present (the
    guide doesn't follow the convention) so behaviour never silently breaks.
    """
    blocks = [m.group(0) for m in _TOOL_BLOCK_RE.finditer(content) if m.group(1) in allowed]
    if not blocks:
        if _TOOL_BLOCK_RE.search(content) is None:
            return content.strip()
        return ""
    rules = _RULES_BLOCK_RE.search(content)
    if rules:
        blocks.append(rules.group(0))
    return "\n\n".join(blocks).strip()


def _fmt_list(header: str, items: tuple[str, ...]) -> str:
    """Format a tuple of items as a markdown section."""
    if not items:
        return f"## {header}\n\n_None_"
    return f"## {header}\n\n" + "\n".join(f"{i + 1}. {item}" for i, item in enumerate(items))


def _fmt_dict(header: str, mapping: Mapping[str, object]) -> str:
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
        return "## Tools Disponibles\n\n_None configured_"

    rows: list[str] = [
        "| Tool | Timeout | Retry | Fallback |",
        "|------|---------|-------|----------|",
    ]
    for i, tool in enumerate(order):
        timeout = policy.timeout_ms_per_tool.get(tool, 30000)
        retry = policy.retry_limit_per_tool.get(tool, 2)
        fallback = order[i + 1] if i + 1 < len(order) else "FAIL branch"
        rows.append(f"| `{tool}` | {timeout}ms | {retry} | {fallback} |")

    return (
        "## Tools Disponibles\n\nOrden de ejecución: "
        + " → ".join(f"`{t}`" for t in order)
        + "\n\n"
        + "\n".join(rows)
    )
