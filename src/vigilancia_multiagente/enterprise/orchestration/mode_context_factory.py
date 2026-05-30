"""ModeContextFactory: builds a frozen ModeContext from a Mode + available data."""

from __future__ import annotations

from vigilancia_multiagente.domain.mode import Mode
from vigilancia_multiagente.domain.mode_context import ModeContext


class ModeContextFactory:
    """Builds an immutable ModeContext snapshot for a session."""

    @staticmethod
    def build(
        mode: Mode,
        company_data: dict[str, object],
        skill_ids: frozenset[str],
        tool_ids: frozenset[str],
    ) -> ModeContext:
        """Create a ModeContext by intersecting mode allowlists with available resources."""
        return ModeContext(
            soul_overlay=mode.soul_overlay_path,
            company_context=company_data,
            skills_allowed=mode.skills_allowlist & skill_ids,
            playbooks_allowed=mode.playbooks_allowed,
            tools_allowed=mode.tools_allowlist & tool_ids,
        )
