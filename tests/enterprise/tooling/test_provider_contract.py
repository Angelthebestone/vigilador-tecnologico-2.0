"""Provider contract tests — verify all builtin tools satisfy ToolWrapper protocol.

Spec 022 T098: parametrized test ensuring every builtin tool is a valid ToolWrapper.
"""

from __future__ import annotations

import pytest

from vigilancia_multiagente.enterprise.tooling.tool_wrapper import ToolWrapper


def _all_builtin_tools() -> list[tuple[str, object]]:
    """Import and instantiate all builtin tools."""
    from vigilancia_multiagente.enterprise.tooling.builtin.creative.minimax_image import (
        MiniMaxImageTool,
    )
    from vigilancia_multiagente.enterprise.tooling.builtin.documents.markitdown import (
        MarkitdownTool,
    )
    from vigilancia_multiagente.enterprise.tooling.builtin.execution.sandbox import (
        SandboxTool,
    )
    from vigilancia_multiagente.enterprise.tooling.builtin.research.arxiv import ArxivTool
    from vigilancia_multiagente.enterprise.tooling.builtin.research.brave import BraveTool
    from vigilancia_multiagente.enterprise.tooling.builtin.research.exa import ExaTool
    from vigilancia_multiagente.enterprise.tooling.builtin.research.firecrawl import (
        FirecrawlTool,
    )
    from vigilancia_multiagente.enterprise.tooling.builtin.research.google_scholar import (
        GoogleScholarTool,
    )
    from vigilancia_multiagente.enterprise.tooling.builtin.research.jina import JinaTool
    from vigilancia_multiagente.enterprise.tooling.builtin.research.openalex import (
        OpenAlexTool,
    )
    from vigilancia_multiagente.enterprise.tooling.builtin.research.serper import SerperTool
    from vigilancia_multiagente.enterprise.tooling.builtin.research.serper_patents import (
        SerperPatentsTool,
    )
    from vigilancia_multiagente.enterprise.tooling.builtin.research.tavily import TavilyTool
    from vigilancia_multiagente.enterprise.tooling.builtin.web.fetch import FetchTool
    from vigilancia_multiagente.enterprise.tooling.builtin.web.playwright import (
        PlaywrightTool,
    )

    return [
        ("brave", BraveTool()),
        ("tavily", TavilyTool()),
        ("exa", ExaTool()),
        ("jina", JinaTool()),
        ("firecrawl", FirecrawlTool()),
        ("serper", SerperTool()),
        ("serper_patents", SerperPatentsTool()),
        ("openalex", OpenAlexTool()),
        ("arxiv", ArxivTool()),
        ("google_scholar", GoogleScholarTool()),
        ("fetch", FetchTool()),
        ("playwright", PlaywrightTool()),
        ("minimax_image", MiniMaxImageTool()),
        ("markitdown", MarkitdownTool()),
        ("sandbox", SandboxTool()),
    ]


@pytest.mark.parametrize(
    "tool_name,tool",
    _all_builtin_tools(),
    ids=[t[0] for t in _all_builtin_tools()],
)
def test_builtin_tool_is_tool_wrapper(tool_name: str, tool: object) -> None:
    """Every builtin tool must satisfy the ToolWrapper protocol."""
    assert isinstance(tool, ToolWrapper), f"{tool_name} is not a ToolWrapper"
    assert tool.name == tool_name
    assert isinstance(tool.domain, str)
    assert isinstance(tool.is_external_mcp, bool)
    assert isinstance(tool.requires_auth, bool)
    assert callable(getattr(tool, "healthcheck", None))
    assert callable(getattr(tool, "execute", None))


@pytest.mark.parametrize(
    "tool_name,tool",
    _all_builtin_tools(),
    ids=[t[0] for t in _all_builtin_tools()],
)
@pytest.mark.asyncio
async def test_builtin_tool_healthcheck_returns_result(tool_name: str, tool: object) -> None:
    """Every builtin tool's healthcheck must return a HealthcheckResult."""
    from vigilancia_multiagente.enterprise.tooling.tool_wrapper import HealthcheckResult

    result = await tool.healthcheck()  # type: ignore[union-attr]
    assert isinstance(result, HealthcheckResult)
    assert result.status in {"UP", "DOWN", "UNCONFIGURED", "UNKNOWN"}
