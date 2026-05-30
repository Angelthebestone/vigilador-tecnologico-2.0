"""Prometheus metrics for the audit trail system."""

from __future__ import annotations

from prometheus_client import Counter, Gauge

agent_modifications_total = Counter(
    "vigilador_agent_modifications_total",
    "Total agent modifications",
    ["target_kind", "triggered_by", "status"],
)

agent_modifications_reverted_total = Counter(
    "vigilador_agent_modifications_reverted_total",
    "Total reverted agent modifications",
    ["target_kind", "reason"],
)

agent_modifications_pending_approval = Gauge(
    "vigilador_agent_modifications_pending_approval",
    "Current count of modifications pending approval",
    ["tenant_id"],
)
