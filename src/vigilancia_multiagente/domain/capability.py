"""Domain model: CapabilitySchema — atomic executable verb with schema."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CapabilitySchema:
    """Immutable representation of a single capability (verb) exposed by a Tool."""

    id: str
    verb: str
    input_schema: dict[str, object]
    output_schema: dict[str, object]
    tool_id: str
