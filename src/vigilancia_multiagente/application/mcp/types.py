"""Typed MCP response DTOs (application layer re-exports)."""

from vigilancia_multiagente.shared.mcp_dto import (
    DocumentConversionResult,
    NavigationResult,
    ScreenshotResult,
    SearchResult,
    SourceResult,
    ToolExecutionResult,
)

__all__ = [
    "DocumentConversionResult",
    "NavigationResult",
    "ScreenshotResult",
    "SearchResult",
    "SourceResult",
    "ToolExecutionResult",
]
