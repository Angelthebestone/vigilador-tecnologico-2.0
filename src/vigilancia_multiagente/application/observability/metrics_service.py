from dataclasses import dataclass
from collections import defaultdict
from uuid import UUID


@dataclass(slots=True, frozen=True)
class ProviderMetrics:
    provider_name: str
    avg_latency_ms: float
    error_rate: float
    retry_rate: float
    latency_buckets: dict[str, int]


class MetricsService:
    def aggregate_provider_metrics(
        self, session_id: UUID, provider_usage: list[dict[str, str | int]]
    ) -> list[ProviderMetrics]:
        del session_id
        if not provider_usage:
            return []
        grouped: dict[str, list[dict[str, str | int]]] = defaultdict(list)
        for item in provider_usage:
            provider = str(item["provider"])
            grouped[provider].append(item)
        return [
            ProviderMetrics(
                provider_name=provider,
                avg_latency_ms=sum(int(entry["latency_ms"]) for entry in entries) / len(entries),
                error_rate=self._error_rate(entries),
                retry_rate=self._retry_rate(entries),
                latency_buckets=self._latency_buckets(entries),
            )
            for provider, entries in grouped.items()
        ]

    def _error_rate(self, entries: list[dict[str, str | int]]) -> float:
        total = len(entries)
        if not total:
            return 0.0
        failures = sum(
            1 for entry in entries if str(entry.get("result_status", "")).upper() == "FAILED"
        )
        return failures / total

    def _retry_rate(self, entries: list[dict[str, str | int]]) -> float:
        total = len(entries)
        if not total:
            return 0.0
        retries = sum(1 for entry in entries if int(entry.get("attempt_count", 1)) > 1)
        return retries / total

    def _latency_buckets(self, entries: list[dict[str, str | int]]) -> dict[str, int]:
        buckets = {"lt_100ms": 0, "lt_500ms": 0, "lt_1000ms": 0, "gte_1000ms": 0}
        for entry in entries:
            latency = int(entry["latency_ms"])
            if latency < 100:
                buckets["lt_100ms"] += 1
            elif latency < 500:
                buckets["lt_500ms"] += 1
            elif latency < 1000:
                buckets["lt_1000ms"] += 1
            else:
                buckets["gte_1000ms"] += 1
        return buckets
