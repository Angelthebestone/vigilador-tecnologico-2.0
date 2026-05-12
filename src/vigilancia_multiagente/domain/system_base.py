"""Domain models for system base and branch overlays."""

from __future__ import annotations

from dataclasses import dataclass, field

from vigilancia_multiagente.domain.models import BranchType


@dataclass(slots=True, frozen=True)
class SystemBase:
    """Canonical system base template shared by all agents.

    This is the single source of truth for global agent rules.
    No branch overlay may redefine these fields.
    """

    version: str
    global_rules: tuple[str, ...] = field(default_factory=tuple)
    tool_usage_policy: dict[str, str] = field(default_factory=dict)
    safety_limits: dict[str, int | float | str] = field(default_factory=dict)
    error_handling: tuple[str, ...] = field(default_factory=tuple)
    output_style: tuple[str, ...] = field(default_factory=tuple)
    model_behavior: dict[str, str | int | float | None] = field(default_factory=dict)
    embedding_config: dict[str, str | int | float] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class BranchOverlay:
    """Domain-specific overlay for a single branch type.

    This is composed with the SystemBase at runtime to produce the final prompt.
    Must not redefine any field that belongs to SystemBase.
    """

    branch_type: BranchType
    objective: str
    required_context: tuple[str, ...] = field(default_factory=tuple)
    output_schema: dict[str, str] = field(default_factory=dict)
    quality_criteria: tuple[str, ...] = field(default_factory=tuple)
    do_rules: tuple[str, ...] = field(default_factory=tuple)
    dont_rules: tuple[str, ...] = field(default_factory=tuple)
    uncertainty_handling: str = ""
    version: str = "1.0.0"


@dataclass(slots=True, frozen=True)
class ComposedPrompt:
    """Result of composing SystemBase + BranchOverlay + user input."""

    system_base_version: str
    branch_type: BranchType
    user_query: str
    sections: dict[str, str]
    full_text: str
    prompt_composition_id: str = ""  # set by PromptComposer, used for MCP traceability
