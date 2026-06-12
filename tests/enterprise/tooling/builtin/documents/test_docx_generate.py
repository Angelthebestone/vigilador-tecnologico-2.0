"""Tests unitarios DB-free para docx_generate (T018)."""

from __future__ import annotations

from pathlib import Path

import pytest

from vigilancia_multiagente.enterprise.tooling.builtin.documents.docx_generate import (
    DocxGenerateTool,
)
from vigilancia_multiagente.enterprise.tooling.tool_wrapper import ToolWrapper

docx = pytest.importorskip("docx", reason="python-docx not installed")


@pytest.fixture()
def tool() -> DocxGenerateTool:
    return DocxGenerateTool()


class TestDocxGenerateTool:
    def test_implements_tool_wrapper_protocol(self, tool: DocxGenerateTool) -> None:
        assert isinstance(tool, ToolWrapper)
        assert tool.name == "docx_generate"
        assert tool.domain == "documents"
        assert tool.is_external_mcp is False

    @pytest.mark.asyncio()
    async def test_generates_valid_docx(self, tool: DocxGenerateTool, tmp_path: Path) -> None:
        output = tmp_path / "out.docx"
        result = await tool.execute(
            "docx_generate",
            {
                "title": "Test Doc",
                "sections": [
                    {"heading": "Intro", "body": "Hello world"},
                    {"heading": "Conclusion", "body": "Done"},
                ],
                "output_path": str(output),
            },
        )
        assert "error" not in result
        assert result["output_path"] == str(output)
        assert output.exists()
        assert result["page_count"] >= 1

    @pytest.mark.asyncio()
    async def test_empty_sections_returns_error(self, tool: DocxGenerateTool) -> None:
        result = await tool.execute(
            "docx_generate",
            {
                "title": "Test",
                "sections": [],
                "output_path": "/tmp/out.docx",
            },
        )
        assert "error" in result
        assert "non-empty" in result["error"]
