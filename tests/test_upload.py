"""Tests for upload validation logic.

Tests the MarkitdownProvider wrapper and upload constants.
Router-level tests require merging to main (worktree editable-install limitation).
"""

import pytest

from vigilancia_multiagente.infra.mcp.markitdown_mcp import MarkitdownProvider


class TestMarkitdownProvider:
    @pytest.mark.asyncio
    async def test_returns_error_when_not_configured(self):
        provider = MarkitdownProvider()
        result = await provider.convert_to_markdown("file:///test.pdf")
        assert result["success"] is False
        assert "not configured" in result["error"]

    @pytest.mark.asyncio
    async def test_supported_formats_include_pdf(self):
        provider = MarkitdownProvider()
        formats = await provider.get_supported_formats()
        assert "pdf" in formats
        assert "docx" in formats

    def test_supported_formats_frozen(self):
        assert isinstance(MarkitdownProvider.SUPPORTED_FORMATS, frozenset)
        assert "xlsx" in MarkitdownProvider.SUPPORTED_FORMATS
