"""Dreaming scheduler — cron + idle trigger with pause-on-interaction."""

from __future__ import annotations

import time
from dataclasses import dataclass


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
