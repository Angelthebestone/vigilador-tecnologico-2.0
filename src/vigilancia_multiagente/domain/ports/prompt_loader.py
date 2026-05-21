"""Prompt template loader port."""

from __future__ import annotations

from typing import Protocol


class PromptLoader(Protocol):
    """Load a prompt template by logical path (no extension)."""

    def load(self, path: str) -> str: ...
