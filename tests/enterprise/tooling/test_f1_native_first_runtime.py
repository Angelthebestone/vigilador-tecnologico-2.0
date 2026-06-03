"""F1.A-F smoke tests for spec 021 native-first runtime (Phase F1 partial).

Covers:

* ``MCPProcessSupervisor`` — manifest loading, status, list_status, healthcheck
  for the empty-manifest case (audit reports 0 MCP-EXTERNO providers).
* ``McpToolWrapper`` — healthcheck bridges supervisor state; execute() raises
  the documented ``NotImplementedError`` (constitución #4 — no silent stubs).
* ``TavilyTool`` / ``BraveTool`` / ``FetchTool`` — ToolWrapper protocol
  compliance, healthcheck gating on env vars, args validation. Network calls
  are not exercised here.
"""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# MCPProcessSupervisor
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_supervisor_with_missing_manifest_starts_empty(tmp_path):
    from vigilancia_multiagente.enterprise.mcp.process_supervisor import (
        MCPProcessSupervisor,
    )

    sup = MCPProcessSupervisor(manifest_path=tmp_path / "missing.yaml")
    await sup.start_all()
    assert sup.list_status() == {}
    await sup.stop_all()


@pytest.mark.asyncio
async def test_supervisor_with_empty_mcps_list(tmp_path):
    from vigilancia_multiagente.enterprise.mcp.process_supervisor import (
        MCPProcessSupervisor,
    )

    manifest = tmp_path / "external.yaml"
    manifest.write_text("mcps: []\n", encoding="utf-8")
    sup = MCPProcessSupervisor(manifest_path=manifest)
    await sup.start_all()
    assert sup.list_status() == {}


@pytest.mark.asyncio
async def test_supervisor_rejects_malformed_manifest(tmp_path):
    """Manifest with `mcps:` that isn't a list propagates an explicit error."""
    from vigilancia_multiagente.enterprise.mcp.process_supervisor import (
        MCPProcessSupervisor,
    )

    manifest = tmp_path / "bad.yaml"
    manifest.write_text("mcps: 'not-a-list'\n", encoding="utf-8")
    sup = MCPProcessSupervisor(manifest_path=manifest)
    with pytest.raises(ValueError, match="must be a list"):
        await sup.start_all()


@pytest.mark.asyncio
async def test_supervisor_get_status_unknown_raises(tmp_path):
    from vigilancia_multiagente.enterprise.mcp.process_supervisor import (
        MCPProcessSupervisor,
    )

    sup = MCPProcessSupervisor(manifest_path=tmp_path / "missing.yaml")
    await sup.start_all()
    with pytest.raises(KeyError, match="unknown mcp"):
        sup.get_status("nope")


# ---------------------------------------------------------------------------
# McpToolWrapper
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mcp_tool_wrapper_healthcheck_unknown_returns_unknown(tmp_path):
    from vigilancia_multiagente.enterprise.mcp.process_supervisor import (
        MCPProcessSupervisor,
    )
    from vigilancia_multiagente.enterprise.tooling.mcp_tool_wrapper import (
        McpToolWrapper,
    )

    sup = MCPProcessSupervisor(manifest_path=tmp_path / "missing.yaml")
    await sup.start_all()
    wrapper = McpToolWrapper(
        name="ghost",
        domain="research",
        requires_auth=True,
        supervisor=sup,
    )
    result = await wrapper.healthcheck()
    assert result.status == "UNKNOWN"
    assert "not registered" in (result.error or "")


@pytest.mark.asyncio
async def test_mcp_tool_wrapper_execute_is_explicit_not_implemented(tmp_path):
    from vigilancia_multiagente.enterprise.mcp.process_supervisor import (
        MCPProcessSupervisor,
    )
    from vigilancia_multiagente.enterprise.tooling.mcp_tool_wrapper import (
        McpToolWrapper,
    )

    sup = MCPProcessSupervisor(manifest_path=tmp_path / "missing.yaml")
    await sup.start_all()
    wrapper = McpToolWrapper(
        name="ghost",
        domain="research",
        requires_auth=True,
        supervisor=sup,
    )
    with pytest.raises(NotImplementedError, match="MCP client port is deferred"):
        await wrapper.execute("any_capability", {"q": "x"})


def test_mcp_tool_wrapper_implements_protocol_attributes(tmp_path):
    """ToolWrapper Protocol attribute compliance (name/domain/is_external_mcp/requires_auth)."""
    from vigilancia_multiagente.enterprise.mcp.process_supervisor import (
        MCPProcessSupervisor,
    )
    from vigilancia_multiagente.enterprise.tooling.mcp_tool_wrapper import (
        McpToolWrapper,
    )

    sup = MCPProcessSupervisor(manifest_path=tmp_path / "missing.yaml")
    wrapper = McpToolWrapper(
        name="example",
        domain="research",
        requires_auth=True,
        supervisor=sup,
    )
    assert wrapper.name == "example"
    assert wrapper.domain == "research"
    assert wrapper.is_external_mcp is True
    assert wrapper.requires_auth is True


# ---------------------------------------------------------------------------
# TavilyTool / BraveTool / FetchTool
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tavily_healthcheck_unconfigured_when_no_key(monkeypatch):
    from vigilancia_multiagente.enterprise.tooling.builtin.research.tavily import (
        TavilyTool,
    )

    monkeypatch.delenv("VT_TAVILY_API_KEY", raising=False)
    tool = TavilyTool()
    result = await tool.healthcheck()
    assert result.status == "UNCONFIGURED"


@pytest.mark.asyncio
async def test_tavily_execute_raises_for_unknown_tool_name(monkeypatch):
    from vigilancia_multiagente.enterprise.tooling.builtin.research.tavily import (
        TavilyTool,
    )

    monkeypatch.setenv("VT_TAVILY_API_KEY", "k-test-12345")
    tool = TavilyTool()
    with pytest.raises(ValueError, match="unknown tool_name"):
        await tool.execute("does_not_exist", {"query": "x"})


@pytest.mark.asyncio
async def test_tavily_execute_raises_for_empty_query(monkeypatch):
    from vigilancia_multiagente.enterprise.tooling.builtin.research.tavily import (
        TavilyTool,
    )

    monkeypatch.setenv("VT_TAVILY_API_KEY", "k-test-12345")
    tool = TavilyTool()
    with pytest.raises(ValueError, match="non-empty string"):
        await tool.execute("web_search", {"query": ""})


@pytest.mark.asyncio
async def test_brave_healthcheck_up_when_key_present(monkeypatch):
    from vigilancia_multiagente.enterprise.tooling.builtin.research.brave import (
        BraveTool,
    )

    monkeypatch.setenv("VT_BRAVE_API_KEY", "k-test")
    result = await BraveTool().healthcheck()
    assert result.status == "UP"


@pytest.mark.asyncio
async def test_brave_execute_unsupported_capability(monkeypatch):
    from vigilancia_multiagente.enterprise.tooling.builtin.research.brave import (
        BraveTool,
    )

    monkeypatch.setenv("VT_BRAVE_API_KEY", "k-test")
    with pytest.raises(ValueError, match="unknown tool_name"):
        await BraveTool().execute("vague", {"query": "x"})


@pytest.mark.asyncio
async def test_fetch_blocks_private_url():
    from vigilancia_multiagente.enterprise.tooling.builtin.web.fetch import FetchTool

    with pytest.raises(PermissionError, match="URL safety"):
        await FetchTool().execute("fetch_url", {"url": "http://localhost:8080/x"})


@pytest.mark.asyncio
async def test_fetch_extract_text_html_to_text_minimal():
    """Internal ``_html_to_text`` strips tags + drops <script> bodies."""
    from vigilancia_multiagente.enterprise.tooling.builtin.web.fetch import (
        _html_to_text,
    )

    html = "<html><script>evil()</script><p>Hello <b>World</b></p></html>"
    assert _html_to_text(html) == "Hello World"


@pytest.mark.asyncio
async def test_fetch_healthcheck_always_up():
    from vigilancia_multiagente.enterprise.tooling.builtin.web.fetch import FetchTool

    result = await FetchTool().healthcheck()
    assert result.status == "UP"


# ---------------------------------------------------------------------------
# Universal Tool registration (smoke)
# ---------------------------------------------------------------------------


def test_native_tools_satisfy_tool_wrapper_protocol():
    """Every tool exposes the ToolWrapper attribute surface (FR-054)."""
    from vigilancia_multiagente.enterprise.tooling.builtin.research.brave import (
        BraveTool,
    )
    from vigilancia_multiagente.enterprise.tooling.builtin.research.tavily import (
        TavilyTool,
    )
    from vigilancia_multiagente.enterprise.tooling.builtin.web.fetch import FetchTool

    for tool in (TavilyTool(), BraveTool(), FetchTool()):
        assert hasattr(tool, "name") and isinstance(tool.name, str)
        assert hasattr(tool, "domain") and isinstance(tool.domain, str)
        assert hasattr(tool, "is_external_mcp") and tool.is_external_mcp is False
        assert hasattr(tool, "requires_auth") and isinstance(tool.requires_auth, bool)
        assert hasattr(tool, "healthcheck") and callable(tool.healthcheck)
        assert hasattr(tool, "execute") and callable(tool.execute)
