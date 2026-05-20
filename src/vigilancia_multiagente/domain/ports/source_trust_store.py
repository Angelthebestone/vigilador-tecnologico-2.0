from __future__ import annotations

from typing import Any, Protocol


class SourceTrustStore(Protocol):
    """Record and query source trust scores."""

    async def get_score(self, source_key: str) -> int | None: ...

    async def record_outcome(self, source_key: str, outcome: Any) -> None: ...
