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
    global_rules: tuple[str, ...] = ()
    tool_usage_policy: dict[str, str] = field(default_factory=dict)
    safety_limits: dict[str, int | float | str] = field(default_factory=dict)
    error_handling: tuple[str, ...] = ()
    output_style: tuple[str, ...] = ()
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
    required_context: tuple[str, ...] = ()
    output_schema: dict[str, str] = field(default_factory=dict)
    quality_criteria: tuple[str, ...] = ()
    do_rules: tuple[str, ...] = ()
    dont_rules: tuple[str, ...] = ()
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
    prompt_composition_id: str = ""


@dataclass(slots=True, frozen=True)
class MiniMaxMessage:
    """A single message in a MiniMax chat conversation.

    Supports all roles documented in the MiniMax API:
    ``system``, ``user``, ``assistant``, ``user_system``,
    ``group``, ``sample_message_user``, ``sample_message_ai``.
    """

    role: str
    content: str
    name: str = ""

    def to_dict(self) -> dict[str, str]:
        """Serialize to the MiniMax API payload format."""
        payload: dict[str, str] = {"role": self.role, "content": self.content}
        if self.name:
            payload["name"] = self.name
        return payload

    def __repr__(self) -> str:
        return f"MiniMaxMessage(role={self.role!r}, name={self.name!r}, content={self.content[:50]}...)"
