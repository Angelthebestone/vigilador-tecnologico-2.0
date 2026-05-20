"""Shared VectorRecord DTO — no layer dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(slots=True, frozen=True)
class VectorRecord:
    session_id: UUID
    content_type: str
    content_ref_id: str
    vector: list[float]
