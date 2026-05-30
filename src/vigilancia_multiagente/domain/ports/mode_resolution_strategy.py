"""Port: ModeResolutionStrategy — contract for resolving the active Mode."""

from __future__ import annotations

from typing import Protocol

from vigilancia_multiagente.domain.mode import Mode


class ModeResolutionStrategy(Protocol):
    """Resolves which Mode is active for a given session/message."""

    def resolve(self, channel_id: str, message: str, session_id: str) -> Mode: ...
