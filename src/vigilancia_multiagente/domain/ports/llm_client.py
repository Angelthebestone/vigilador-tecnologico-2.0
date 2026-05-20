from __future__ import annotations

from typing import Any, Protocol


class LLMClient(Protocol):
    """Generate text completions from message history."""

    async def complete(self, messages: list[Any], **kwargs: Any) -> Any: ...
