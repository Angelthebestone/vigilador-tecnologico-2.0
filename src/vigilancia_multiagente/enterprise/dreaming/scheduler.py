"""Dreaming scheduler — cron + idle trigger with MVP phase allow-list.

Spec 021 F5a.A / T124. The scheduler MVP only registers two phases on
the orchestrator at boot:

* ``memory_consolidation`` — frozen snapshot capture (FR-040).
* ``ingestion_sync`` — incremental connector pulls (FR-040).

The 8 extra phases under :mod:`...dreaming.phases` and the 7 loops
under :mod:`...dreaming.loops` are intentionally left out of the
allow-list — they remain in-tree for spec F5b but are NOT imported by
the runtime composition. ``mvp_phase_names()`` is the single source of
truth that the composition root consults to register phases.
"""

from __future__ import annotations

import time
from collections.abc import Sequence
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# MVP allow-list (FR-039 / FR-040 — exactly 2 phases register at boot)
# ---------------------------------------------------------------------------

_MVP_PHASE_NAMES: tuple[str, ...] = ("memory_consolidation", "ingestion_sync")


def mvp_phase_names() -> tuple[str, ...]:
    """Return the explicit MVP phase allow-list.

    Composition roots consult this function to decide which phases to
    register on the :class:`DreamingOrchestrator`. Anything else stays
    on the F5b roadmap.
    """
    return _MVP_PHASE_NAMES


def is_mvp_phase(name: str) -> bool:
    return name in _MVP_PHASE_NAMES


@dataclass
class DreamingSchedulerConfig:
    """Configuration for the dreaming scheduler."""

    enabled: bool = True
    cron_hour: int = 3
    idle_timeout_min: int = 10


class DreamingScheduler:
    """Manages cron and idle-based triggering of dreaming cycles."""

    def __init__(self, config: DreamingSchedulerConfig | None = None) -> None:
        self._config = config or DreamingSchedulerConfig()
        self._last_activity_ts: float = time.time()
        self._interaction_active = False

    @property
    def config(self) -> DreamingSchedulerConfig:
        return self._config

    @property
    def enabled(self) -> bool:
        return self._config.enabled

    def record_activity(self) -> None:
        """Record user activity — resets idle timer and signals interaction."""
        self._last_activity_ts = time.time()
        self._interaction_active = True

    def clear_interaction(self) -> None:
        """Clear interaction flag after pause has been handled."""
        self._interaction_active = False

    @property
    def interaction_active(self) -> bool:
        return self._interaction_active

    def is_idle_triggered(self) -> bool:
        """Check if idle timeout has been exceeded."""
        if not self._config.enabled:
            return False
        elapsed_min = (time.time() - self._last_activity_ts) / 60.0
        return elapsed_min >= self._config.idle_timeout_min

    def should_trigger_cron(self, current_hour: int) -> bool:
        """Check if current hour matches cron configuration."""
        if not self._config.enabled:
            return False
        return current_hour == self._config.cron_hour

    @staticmethod
    def filter_to_mvp(phase_names: Sequence[str]) -> list[str]:
        """Return only the MVP-allowed phase names from ``phase_names``.

        The order of the input is preserved, but any name not in the
        allow-list is dropped silently. Use this when probing a
        previously discovered phase list and wanting only the MVP subset.
        """
        allow = set(_MVP_PHASE_NAMES)
        return [n for n in phase_names if n in allow]
