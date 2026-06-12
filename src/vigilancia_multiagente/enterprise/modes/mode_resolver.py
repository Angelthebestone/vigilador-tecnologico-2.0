"""ModeResolver: manages active mode per session (spec 011, CQS)."""

from __future__ import annotations

from vigilancia_multiagente.enterprise.modes.mode_loader import ModeRegistry011
from vigilancia_multiagente.enterprise.modes.mode_schema import ModeConfig


class ModeNotAvailableError(Exception):
    """Raised when activating a mode that is not registered."""

    def __init__(self, mode_id: str, available: list[str]) -> None:
        self.mode_id = mode_id
        self.available = available
        super().__init__(f"Mode '{mode_id}' not available. Available modes: {available}")


class ModeResolver:
    """Resolves and manages the active mode per session.

    CQS: activate() and change_mode() are COMMANDS (mutate _active_modes),
    returning ModeConfig as pragmatic exception. get_active() is a pure QUERY.
    """

    def __init__(self, registry: ModeRegistry011) -> None:
        self._registry = registry
        self._active_modes: dict[str, ModeConfig] = {}

    def activate(self, session_id: str, mode_id: str) -> ModeConfig:
        """COMMAND: Activate a mode for a session. FR-010, FR-012."""
        mode = self._registry.get(mode_id)
        if mode is None:
            available = [m.id for m in self._registry.list_available()]
            raise ModeNotAvailableError(mode_id, available)
        self._active_modes[session_id] = mode
        return mode

    def get_active(self, session_id: str) -> ModeConfig:
        """QUERY: Return the active mode for a session. Falls back to 'default' (FR-011)."""
        if session_id in self._active_modes:
            return self._active_modes[session_id]
        # Fallback to default
        default = self._registry.get("default")
        if default is None:
            available = [m.id for m in self._registry.list_available()]
            raise ModeNotAvailableError("default", available)
        self._active_modes[session_id] = default
        return default

    def change_mode(self, session_id: str, new_mode_id: str) -> ModeConfig:
        """COMMAND: Change mode mid-session, discarding previous (FR-013)."""
        mode = self._registry.get(new_mode_id)
        if mode is None:
            available = [m.id for m in self._registry.list_available()]
            raise ModeNotAvailableError(new_mode_id, available)
        self._active_modes[session_id] = mode
        return mode
