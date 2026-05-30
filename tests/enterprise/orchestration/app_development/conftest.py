"""Fakes and fixtures for app_development tests."""

from __future__ import annotations

from typing import Any

import pytest


class FakeLLM:
    """Fake LLM that returns configurable responses."""

    def __init__(self, response: str = "") -> None:
        self.response = response
        self.calls: list[list[dict[str, str]]] = []

    async def complete(self, messages: list[Any], **kwargs: Any) -> str:
        self.calls.append(messages)
        return self.response


class FakeSandbox:
    """Fake sandbox that returns configurable output."""

    def __init__(self, output: str = "OK") -> None:
        self.output = output
        self.executions: list[str] = []

    async def execute(self, code: str, language: str = "python") -> str:
        self.executions.append(code)
        return self.output


class FakeFileSystem:
    """Fake file system for testing."""

    def __init__(self, exists: bool = True) -> None:
        self._exists = exists
        self.written: dict[str, str] = {}

    async def write_file(self, path: str, content: str) -> None:
        self.written[path] = content

    async def read_file(self, path: str) -> str:
        return self.written.get(path, "")

    async def path_exists(self, path: str) -> bool:
        return self._exists


class FakeApproval:
    """Fake approval gate."""

    def __init__(self, approved: bool = True) -> None:
        self.approved = approved
        self.requests: list[tuple[str, str]] = []

    async def request_approval(self, phase: str, document: str) -> bool:
        self.requests.append((phase, document))
        return self.approved


class FakeAudit:
    """Fake audit trail."""

    def __init__(self) -> None:
        self.entries: list[dict[str, str]] = []

    async def record(self, triggered_by: str, target_file: str, phase: str) -> None:
        self.entries.append(
            {"triggered_by": triggered_by, "target_file": target_file, "phase": phase}
        )


class FakeTemplate:
    """Fake template renderer that returns variables as formatted text."""

    def render(self, template_name: str, variables: dict[str, str]) -> str:
        parts = [f"{k}: {v}" for k, v in variables.items()]
        return f"[{template_name}]\n" + "\n".join(parts)


@pytest.fixture
def fake_llm() -> FakeLLM:
    return FakeLLM()


@pytest.fixture
def fake_sandbox() -> FakeSandbox:
    return FakeSandbox()


@pytest.fixture
def fake_template() -> FakeTemplate:
    return FakeTemplate()


@pytest.fixture
def fake_approval() -> FakeApproval:
    return FakeApproval()


@pytest.fixture
def fake_audit() -> FakeAudit:
    return FakeAudit()


@pytest.fixture
def fake_fs() -> FakeFileSystem:
    return FakeFileSystem()
