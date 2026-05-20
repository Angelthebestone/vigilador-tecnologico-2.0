"""Port for document-to-markdown conversion."""

from __future__ import annotations

from typing import Any, Protocol


class MarkitdownPort(Protocol):
    """Convert documents to markdown text."""

    async def convert_to_markdown(self, file_uri: str) -> dict[str, Any]: ...
