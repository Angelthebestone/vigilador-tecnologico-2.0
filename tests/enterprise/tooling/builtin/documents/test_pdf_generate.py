"""Tests unitarios DB-free para pdf_generate (T019).

NOTA: WeasyPrint requiere dependencias de sistema (GTK/Pango).
Si no están disponibles, los tests se saltan con pytest.importorskip.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from vigilancia_multiagente.enterprise.tooling.builtin.documents.pdf_generate import (
    PdfGenerateTool,
)
from vigilancia_multiagente.enterprise.tooling.tool_wrapper import ToolWrapper

weasyprint = pytest.importorskip("weasyprint", reason="weasyprint not installed")


@pytest.fixture()
def tool() -> PdfGenerateTool:
    return PdfGenerateTool()


class TestPdfGenerateTool:
    def test_implements_tool_wrapper_protocol(self, tool: PdfGenerateTool) -> None:
        assert isinstance(tool, ToolWrapper)
        assert tool.name == "pdf_generate"
        assert tool.domain == "documents"
        assert tool.is_external_mcp is False

    @pytest.mark.asyncio()
    async def test_generates_valid_pdf(self, tool: PdfGenerateTool, tmp_path: Path) -> None:
        output = tmp_path / "out.pdf"
        result = await tool.execute("pdf_generate", {
            "html_content": "<html><body><h1>Hello</h1><p>World</p></body></html>",
            "output_path": str(output),
        })
        assert "error" not in result
        assert result["output_path"] == str(output)
        assert output.exists()
        assert result["page_count"] >= 1

    @pytest.mark.asyncio()
    async def test_missing_html_returns_error(self, tool: PdfGenerateTool) -> None:
        result = await tool.execute("pdf_generate", {
            "html_content": "",
            "output_path": "/tmp/out.pdf",
        })
        assert "error" in result
