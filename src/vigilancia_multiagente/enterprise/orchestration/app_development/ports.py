"""Ports (abstractions) for the app-development playbook agents."""

from __future__ import annotations

from typing import Any, Protocol


class LLMPort(Protocol):
    """Generate text from messages."""

    async def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str: ...


class SandboxPort(Protocol):
    """Execute code in an isolated sandbox environment."""

    async def execute(self, code: str, language: str = "python") -> str: ...


class FileSystemPort(Protocol):
    """Read/write files in the project workspace."""

    async def write_file(self, path: str, content: str) -> None: ...
    async def read_file(self, path: str) -> str: ...
    async def path_exists(self, path: str) -> bool: ...


class ApprovalPort(Protocol):
    """Request human approval (gate)."""

    async def request_approval(self, phase: str, document: str) -> bool: ...


class AuditPort(Protocol):
    """Record audit trail entries."""

    async def record(self, triggered_by: str, target_file: str, phase: str) -> None: ...


class TemplatePort(Protocol):
    """Render Jinja2 templates."""

    def render(self, template_name: str, variables: dict[str, str]) -> str: ...
