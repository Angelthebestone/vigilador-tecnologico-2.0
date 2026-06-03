"""F1.A-F deferred — smoke tests for 10 WRAP-SDK + 2 CLONE-UPSTREAM + sandbox.

Spec 021 FR-053/054 + audit "10 WRAP-SDK / 2 CLONE-UPSTREAM" classification.

Coverage strategy: every tool implements the same ``ToolWrapper`` Protocol,
so we drive most assertions from a single fixture list and exercise the
healthcheck + ``execute()`` argument-validation paths uniformly.

Network calls are not exercised — those are integration tests that belong
elsewhere. Here we verify the contract surface only.
"""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

import pytest

from vigilancia_multiagente.enterprise.tooling.builtin.creative.minimax_image import (
    MiniMaxImageTool,
)
from vigilancia_multiagente.enterprise.tooling.builtin.documents.markitdown import (
    MarkitdownTool,
)
from vigilancia_multiagente.enterprise.tooling.builtin.execution.sandbox import (
    SandboxTool,
)
from vigilancia_multiagente.enterprise.tooling.builtin.productivity.google_workspace import (
    GoogleWorkspaceTool,
)
from vigilancia_multiagente.enterprise.tooling.builtin.research.arxiv import ArxivTool
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
from vigilancia_multiagente.enterprise.tooling.builtin.web.playwright import (
    PlaywrightTool,
)

_TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")


def _all_tool_factories() -> list[tuple[str, Callable[[], object]]]:
    """Factory list — instantiation must be cheap (no network/disk)."""
    return [
        ("exa", ExaTool),
        ("jina", JinaTool),
        ("firecrawl", FirecrawlTool),
        ("serper", SerperTool),
        ("serper_patents", SerperPatentsTool),
        ("markitdown", MarkitdownTool),
        ("minimax_image", MiniMaxImageTool),
        ("openalex", OpenAlexTool),
        ("playwright", PlaywrightTool),
        ("google_workspace", lambda: GoogleWorkspaceTool(
            oauth_manager=None, tenant_id=_TENANT_ID
        )),
        ("sandbox", SandboxTool),
        ("arxiv", ArxivTool),
        ("google_scholar", GoogleScholarTool),
    ]


# ---------------------------------------------------------------------------
# Protocol surface
# ---------------------------------------------------------------------------


def test_all_native_tools_satisfy_tool_wrapper_protocol():
    """FR-054: every native tool exposes the ToolWrapper attribute surface."""
    for tool_name, factory in _all_tool_factories():
        tool = factory()
        assert hasattr(tool, "name") and tool.name == tool_name, tool_name
        assert hasattr(tool, "domain") and isinstance(tool.domain, str)
        assert hasattr(tool, "is_external_mcp") and tool.is_external_mcp is False
        assert hasattr(tool, "requires_auth") and isinstance(tool.requires_auth, bool)
        assert callable(tool.healthcheck)
        assert callable(tool.execute)


@pytest.mark.asyncio
async def test_all_keyed_tools_report_unconfigured_without_keys(monkeypatch):
    """Tools requiring a key must report UNCONFIGURED when env is empty."""
    keyed = {
        "exa": "VT_EXA_API_KEY",
        "firecrawl": "VT_FIRECRAWL_API_KEY",
        "serper": "VT_SERPER_API_KEY",
        "serper_patents": "VT_SERPER_API_KEY",
        "minimax_image": "VT_MINIMAX_IMAGE_API_KEY",
    }
    for name, factory in _all_tool_factories():
        if name not in keyed:
            continue
        monkeypatch.delenv(keyed[name], raising=False)
        result = await factory().healthcheck()
        assert result.status == "UNCONFIGURED", (
            f"{name} should report UNCONFIGURED when {keyed[name]} is unset"
        )


@pytest.mark.asyncio
async def test_keyed_tools_report_up_when_key_present(monkeypatch):
    keyed = {
        "exa": "VT_EXA_API_KEY",
        "firecrawl": "VT_FIRECRAWL_API_KEY",
        "serper": "VT_SERPER_API_KEY",
        "serper_patents": "VT_SERPER_API_KEY",
        "minimax_image": "VT_MINIMAX_IMAGE_API_KEY",
    }
    for name, factory in _all_tool_factories():
        if name not in keyed:
            continue
        monkeypatch.setenv(keyed[name], "k-test")
        result = await factory().healthcheck()
        assert result.status == "UP", f"{name} should be UP when key is set"


@pytest.mark.asyncio
async def test_keyless_tools_report_up_or_unconfigured():
    """``jina``/``openalex``/``arxiv`` need no key (anonymous tier)."""
    for name in ("jina", "openalex", "arxiv"):
        factory = dict(_all_tool_factories())[name]
        result = await factory().healthcheck()
        assert result.status == "UP", f"{name} should be UP without any key"


# ---------------------------------------------------------------------------
# execute() arg validation per tool family
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_exa_execute_rejects_unknown_capability(monkeypatch):
    monkeypatch.setenv("VT_EXA_API_KEY", "k")
    with pytest.raises(ValueError, match="unknown tool_name"):
        await ExaTool().execute("nope", {"query": "x"})


@pytest.mark.asyncio
async def test_jina_execute_blocks_private_url():
    with pytest.raises(PermissionError, match="URL safety"):
        await JinaTool().execute("reader", {"url": "http://localhost/admin"})


@pytest.mark.asyncio
async def test_firecrawl_blocks_private_url(monkeypatch):
    monkeypatch.setenv("VT_FIRECRAWL_API_KEY", "k")
    with pytest.raises(PermissionError, match="URL safety"):
        await FirecrawlTool().execute("scrape_page", {"url": "http://127.0.0.1/x"})


@pytest.mark.asyncio
async def test_serper_unknown_capability(monkeypatch):
    monkeypatch.setenv("VT_SERPER_API_KEY", "k")
    with pytest.raises(ValueError, match="unknown tool_name"):
        await SerperTool().execute("magic_search", {"query": "x"})


@pytest.mark.asyncio
async def test_serper_patents_requires_patent_id(monkeypatch):
    monkeypatch.setenv("VT_SERPER_API_KEY", "k")
    with pytest.raises(ValueError, match="patent_id"):
        await SerperPatentsTool().execute("patent_details", {})


@pytest.mark.asyncio
async def test_markitdown_rejects_traversal(monkeypatch):
    with pytest.raises(PermissionError, match="traversal"):
        await MarkitdownTool().execute(
            "convert_to_markdown", {"path": "../etc/passwd"}
        )


@pytest.mark.asyncio
async def test_markitdown_rejects_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        await MarkitdownTool().execute(
            "convert_to_markdown", {"path": str(tmp_path / "missing.docx")}
        )


@pytest.mark.asyncio
async def test_minimax_image_requires_prompt(monkeypatch):
    monkeypatch.setenv("VT_MINIMAX_IMAGE_API_KEY", "k")
    with pytest.raises(ValueError, match="prompt"):
        await MiniMaxImageTool().execute("generate_image", {})


@pytest.mark.asyncio
async def test_openalex_unknown_capability():
    with pytest.raises(ValueError, match="unknown tool_name"):
        await OpenAlexTool().execute("magic", {"query": "x"})


@pytest.mark.asyncio
async def test_playwright_blocks_private_url():
    with pytest.raises(PermissionError, match="URL safety"):
        await PlaywrightTool().execute("navigate", {"url": "http://10.0.0.1/x"})


@pytest.mark.asyncio
async def test_google_workspace_unconfigured_without_oauth_manager():
    tool = GoogleWorkspaceTool(oauth_manager=None, tenant_id=_TENANT_ID)
    result = await tool.healthcheck()
    assert result.status == "UNCONFIGURED"


@pytest.mark.asyncio
async def test_google_workspace_execute_raises_without_credentials():
    tool = GoogleWorkspaceTool(oauth_manager=None, tenant_id=_TENANT_ID)
    with pytest.raises(RuntimeError, match="OAuthManager not wired"):
        await tool.execute("read_docs", {"document_id": "x"})


@pytest.mark.asyncio
async def test_sandbox_unconfigured_without_key(monkeypatch):
    monkeypatch.delenv("VT_E2B_API_KEY", raising=False)
    result = await SandboxTool().healthcheck()
    # Either e2b not installed (UNCONFIGURED) or e2b installed + no key (UNCONFIGURED).
    assert result.status == "UNCONFIGURED"


@pytest.mark.asyncio
async def test_arxiv_list_categories_returns_list():
    result = await ArxivTool().execute("list_categories", {})
    assert isinstance(result.get("categories"), list)
    assert "cs.AI" in result["categories"]


@pytest.mark.asyncio
async def test_arxiv_search_requires_query():
    with pytest.raises(ValueError, match="query"):
        await ArxivTool().execute("search_papers", {})


@pytest.mark.asyncio
async def test_google_scholar_search_requires_query():
    # Even if scholarly is missing, validation runs before import.
    with pytest.raises((ValueError, RuntimeError)):
        await GoogleScholarTool().execute("search_papers", {})


# ---------------------------------------------------------------------------
# T033 — universal Tool registration: all 16 catalog providers wire up
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_universal_tool_registration_assembles_all_providers():
    """FR-040 + FR-054: every native tool registers identically via ``ToolRegistry``.

    Builds a ``ToolRegistry`` directly with the 13 native tools added in
    F1.A-F deferred + the 4 documents tools that already shipped, mirroring
    ``api/enterprise_composition._build_tool_registry`` minus the Document
    tools' filesystem-root resolution. The point is to assert the registry
    pipeline accepts all native ToolWrappers without error.
    """
    from vigilancia_multiagente.enterprise.tooling.builtin.documents.docx_generate import (
        DocxGenerateTool,
    )
    from vigilancia_multiagente.enterprise.tooling.builtin.documents.pdf_generate import (
        PdfGenerateTool,
    )
    from vigilancia_multiagente.enterprise.tooling.builtin.documents.template_render import (
        TemplateRenderTool,
    )
    from vigilancia_multiagente.enterprise.tooling.builtin.research.brave import (
        BraveTool,
    )
    from vigilancia_multiagente.enterprise.tooling.builtin.research.tavily import (
        TavilyTool,
    )
    from vigilancia_multiagente.enterprise.tooling.builtin.web.fetch import FetchTool
    from vigilancia_multiagente.enterprise.tooling.tool_registry import ToolRegistry

    tools = [
        # Documents (4 of 5 — FileSystemTool needs a workspace, skipped here)
        TemplateRenderTool(),
        DocxGenerateTool(),
        PdfGenerateTool(),
        MarkitdownTool(),
        # F1.A-F shipped earlier (3)
        TavilyTool(),
        BraveTool(),
        FetchTool(),
        # F1.A-F deferred (13)
        ExaTool(),
        JinaTool(),
        FirecrawlTool(),
        SerperTool(),
        SerperPatentsTool(),
        MiniMaxImageTool(),
        OpenAlexTool(),
        PlaywrightTool(),
        ArxivTool(),
        GoogleScholarTool(),
        SandboxTool(),
        GoogleWorkspaceTool(oauth_manager=None, tenant_id=_TENANT_ID),
    ]
    # Use a stub repo + None embedding gateway (registration path doesn't need them).
    registry = ToolRegistry(tool_health_repo=None, embedding_gateway=None)
    for tool in tools:
        await registry.register(tool)
    names = {tool.name for tool in tools}
    assert len(names) == len(tools), "every tool name must be unique"
    # Sanity: every catalog-mvp provider is represented in our 19 tools above.
    expected = {
        "template_render", "docx_generate", "pdf_generate", "markitdown",
        "tavily", "brave", "fetch", "exa", "jina", "firecrawl",
        "serper", "serper_patents", "minimax_image", "openalex",
        "playwright", "arxiv", "google_scholar", "sandbox", "google_workspace",
    }
    assert names == expected, names ^ expected
