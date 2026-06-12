"""ModeToolFilter: filters tools by active mode's domains/exclusions (spec 011, DIP)."""

from __future__ import annotations

from typing import Protocol

from vigilancia_multiagente.enterprise.modes.mode_schema import ModeConfig


class ToolCardLike(Protocol):
    """Minimal protocol for a tool card — DIP: no import of tool_registry."""

    @property
    def id(self) -> str: ...

    @property
    def domains(self) -> list[str]: ...


class ToolNotAllowedError(Exception):
    """Raised when a tool is not permitted in the active mode (FR-017)."""

    def __init__(self, tool_name: str, mode_id: str) -> None:
        self.tool_name = tool_name
        self.mode_id = mode_id
        super().__init__(f"Tool '{tool_name}' is not allowed in mode '{mode_id}'")


class ToolListProvider(Protocol):
    """Protocol for obtaining the full list of tool cards — DIP."""

    def get_all_cards(self) -> list[ToolCardLike]: ...


class ModeToolFilter:
    """Filters tools based on mode's tools.domains and tools.excluded."""

    def filter_tools(self, mode: ModeConfig, cards: list[ToolCardLike]) -> list[ToolCardLike]:
        """Return only tools whose domains intersect with mode's allowed domains.

        Excludes tools in mode.tools.excluded regardless of domain match.
        If mode has no tools config, returns all cards unfiltered.
        """
        if mode.tools is None:
            return list(cards)

        allowed_domains = set(mode.tools.domains)
        excluded_names = set(mode.tools.excluded)

        result: list[ToolCardLike] = []
        for card in cards:
            if card.id in excluded_names:
                continue
            if any(d in allowed_domains for d in card.domains):
                result.append(card)
        return result

    def check_tool_allowed(
        self, mode: ModeConfig, tool_name: str, cards: list[ToolCardLike]
    ) -> bool:
        """Check if a specific tool is allowed in the mode.

        Raises ToolNotAllowedError if not permitted (FR-017).
        """
        if mode.tools is None:
            return True

        excluded_names = set(mode.tools.excluded)
        if tool_name in excluded_names:
            raise ToolNotAllowedError(tool_name, mode.id)

        allowed_domains = set(mode.tools.domains)
        for card in cards:
            if card.id == tool_name:
                if any(d in allowed_domains for d in card.domains):
                    return True
                raise ToolNotAllowedError(tool_name, mode.id)

        # Tool not found in cards — not allowed
        raise ToolNotAllowedError(tool_name, mode.id)
