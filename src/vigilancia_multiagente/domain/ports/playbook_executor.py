"""Port: PlaybookExecutor — contract for running a playbook."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from vigilancia_multiagente.domain.mode_context import ModeContext
from vigilancia_multiagente.domain.playbook import PlaybookDefinition


@dataclass(frozen=True)
class ExecutionResult:
    """Immutable result of a playbook execution."""

    success: bool
    outputs: dict[str, object]
    errors: tuple[str, ...]


class PlaybookExecutor(Protocol):
    """Executes a playbook within a given mode context."""

    def execute(
        self, playbook: PlaybookDefinition, context: ModeContext
    ) -> ExecutionResult: ...
