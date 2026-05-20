"""Provider registry port — abstracts MCP provider lookup for application."""

from __future__ import annotations

from typing import Protocol


class ProviderConfig(Protocol):
    """Minimal provider config interface consumed by application code."""

    name: str
    enabled_tools: tuple[str, ...]


class ProviderRegistry(Protocol):
    """Lookup MCP providers without depending on infra implementation."""

    def get(self, name: str) -> ProviderConfig: ...
    def validate_ready(self, required_tools: tuple[str, ...]) -> None: ...
