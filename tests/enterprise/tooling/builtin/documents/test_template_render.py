"""Tests unitarios DB-free para template_render (T017)."""

from __future__ import annotations

from pathlib import Path

import pytest

from vigilancia_multiagente.enterprise.tooling.builtin.documents.template_render import (
    TemplateRenderTool,
)
from vigilancia_multiagente.enterprise.tooling.tool_wrapper import ToolWrapper


@pytest.fixture()
def templates_dir(tmp_path: Path) -> Path:
    tpl_dir = tmp_path / "templates"
    tpl_dir.mkdir()
    (tpl_dir / "report.md").write_text("# {{ title }}\n\n{{ body }}", encoding="utf-8")
    return tpl_dir


@pytest.fixture()
def tool(templates_dir: Path) -> TemplateRenderTool:
    return TemplateRenderTool(templates_dir=templates_dir)


class TestTemplateRenderTool:
    def test_implements_tool_wrapper_protocol(self, tool: TemplateRenderTool) -> None:
        assert isinstance(tool, ToolWrapper)
        assert tool.name == "template_render"
        assert tool.domain == "documents"
        assert tool.is_external_mcp is False

    @pytest.mark.asyncio()
    async def test_renders_template_with_variables(self, tool: TemplateRenderTool) -> None:
        result = await tool.execute("template_render", {
            "template_name": "report.md",
            "variables": {"title": "Test Report", "body": "Content here"},
            "output_format": "md",
        })
        assert "error" not in result
        assert "# Test Report" in result["rendered_content"]
        assert "Content here" in result["rendered_content"]

    @pytest.mark.asyncio()
    async def test_missing_template_returns_error(self, tool: TemplateRenderTool) -> None:
        result = await tool.execute("template_render", {
            "template_name": "nonexistent.md",
            "variables": {},
            "output_format": "md",
        })
        assert "error" in result
        assert "not found" in result["error"]
