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
    prompt_composition_id: str = ""


class MiniMaxMessage:
    """A single message in a MiniMax chat conversation.

    Supports all roles documented in the MiniMax API:
    ``system``, ``user``, ``assistant``, ``user_system``,
    ``group``, ``sample_message_user``, ``sample_message_ai``.
    """

    __slots__ = ("role", "content", "name")

    def __init__(self, role: str, content: str, name: str = "") -> None:
        self.role = role
        self.content = content
        self.name = name

    def to_dict(self) -> dict[str, str]:
        """Serialize to the MiniMax API payload format."""
        d: dict[str, str] = {"role": self.role, "content": self.content}
        if self.name:
            d["name"] = self.name
        return d

    def __repr__(self) -> str:
        return f"MiniMaxMessage(role={self.role!r}, name={self.name!r}, content={self.content[:50]}...)"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MiniMaxMessage):
            return NotImplemented
        return self.role == other.role and self.name == other.name and self.content == other.content

    def __hash__(self) -> int:
        return hash((self.role, self.name, self.content))
