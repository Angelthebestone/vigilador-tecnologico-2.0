"""Prometheus metrics for the Dreaming subsystem."""

from __future__ import annotations

from prometheus_client import Counter, Histogram

dreaming_phase_duration_seconds = Histogram(
    "vigilador_dreaming_phase_duration_seconds",
    "Duration of each dreaming phase in seconds",
    ["phase"],
)

dreaming_phase_status = Counter(
    "vigilador_dreaming_phase_status",
    "Count of dreaming phase executions by status",
    ["phase", "status"],
)
