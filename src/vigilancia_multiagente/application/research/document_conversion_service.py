"""Document-to-markdown conversion via Markitdown port."""

from __future__ import annotations

from vigilancia_multiagente.application.mcp.types import DocumentConversionResult
from vigilancia_multiagente.domain.ports.markitdown_port import MarkitdownPort


class DocumentConversionService:
    def __init__(self, markitdown: MarkitdownPort) -> None:
        self._markitdown = markitdown

    async def convert(self, file_uri: str, filename: str, ext: str) -> DocumentConversionResult:
        result = await self._markitdown.convert_to_markdown(file_uri)
        if not result.get("success"):
            return DocumentConversionResult(
                success=False,
                error=str(result.get("error", "Markitdown conversion failed")),
            )
        return DocumentConversionResult(
            success=True,
            content=str(result.get("content", "")),
            format=str(result.get("format", ext)),
        )
