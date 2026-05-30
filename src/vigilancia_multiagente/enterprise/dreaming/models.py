"""Dreaming subsystem data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class PhaseStatus(Enum):
    SUCCESS = "success"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass(frozen=True)
class DreamingContext:
    """Immutable context passed to each phase during a dreaming cycle."""

    cycle_id: str
    started_at: datetime
    tenant_id: str
    llm_available: bool
    phases_to_run: list[str] = field(default_factory=list)


@dataclass
class PhaseResult:
    """Result of executing a single dreaming phase."""

    phase_name: str
    status: PhaseStatus
    duration_ms: float
    error: str | None = None
    metrics_dict: dict[str, Any] = field(default_factory=dict)


@dataclass
class CycleReport:
    """Aggregate report for a complete dreaming cycle."""

    cycle_id: str
    started_at: datetime
    finished_at: datetime
    results: list[PhaseResult] = field(default_factory=list)
