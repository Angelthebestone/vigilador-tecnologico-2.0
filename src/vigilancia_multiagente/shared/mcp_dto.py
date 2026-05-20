"""Shared MCP response DTOs (no layer dependencies)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ToolExecutionResult:
    provider: str
    tool_name: str
    payload: dict[str, Any]
    attempt_count: int
    result_status: str = "SUCCESS"


@dataclass(frozen=True, slots=True)
class NavigationResult:
    url: str
    title: str = ""
    content: str = ""
    screenshot_path: str | None = None
    blocked: bool = False
    block_reason: str | None = None


@dataclass(frozen=True, slots=True)
class ScreenshotResult:
    url: str
    image_path: str | None = None
    blocked: bool = False
    block_reason: str | None = None


@dataclass(frozen=True, slots=True)
class SearchResult:
    query: str
    results: tuple[dict[str, Any], ...] = ()
    provider: str = ""


@dataclass(frozen=True, slots=True)
class SourceResult:
    url: str
    title: str = ""
    snippet: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DocumentConversionResult:
    success: bool
    content: str = ""
    format: str = ""
    error: str | None = None
