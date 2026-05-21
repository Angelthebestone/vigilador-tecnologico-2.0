#!/usr/bin/env python3
"""Benchmark P95 latency with all eval_ws flags false vs true (SC-PLAN-06).

Simulates synthetic step executions — does NOT call real APIs.
Output: JSON with comparative metrics.
"""

import json
import random
import statistics
import time

# Synthetic step descriptors per workstream
_STEPS: list[tuple[str, str]] = [
    ("ws_a", "source_quality_check"),
    ("ws_b", "data_intelligence_analyze"),
    ("ws_c", "deep_analysis_project"),
    ("ws_d", "strategic_signals_detect"),
    ("ws_e", "output_assurance_gate"),
    ("ws_c", "s_curve_fit"),
    ("ws_d", "narrative_shift_detect"),
    ("ws_e", "bias_audit"),
]


def _simulate_run(flags_enabled: bool, iterations: int = 100) -> list[float]:
    """Run synthetic steps and return per-step durations.

    When flags are enabled, steps execute their full logic path
    (simulated ~1.5x–3x slower than short-circuited path).
    """
    durations: list[float] = []
    for _ in range(iterations):
        for workstream, step_name in _STEPS:
            _ = workstream, step_name  # used for labeling in real impl
            base = random.uniform(0.01, 0.05) if not flags_enabled else random.uniform(0.02, 0.12)
            durations.append(base)
            time.sleep(base)
    return durations


def percentile(data: list[float], p: float) -> float:
    if not data:
        return 0.0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * p / 100.0
    f = int(k)
    c = f + 1
    if c >= len(sorted_data):
        return sorted_data[f]
    return sorted_data[f] + (k - f) * (sorted_data[c] - sorted_data[f])


def main() -> None:
    print("Benchmarking P95 latency: flags=false vs flags=true (synthetic)")
    print()

    false_durations = _simulate_run(flags_enabled=False, iterations=50)
    true_durations = _simulate_run(flags_enabled=True, iterations=50)

    p95_false = percentile(false_durations, 95)
    p95_true = percentile(true_durations, 95)
    mean_false = statistics.mean(false_durations)
    mean_true = statistics.mean(true_durations)

    result = {
        "scenario": "SC-PLAN-06 latency benchmark",
        "flags_false": {
            "p95_seconds": round(p95_false, 4),
            "mean_seconds": round(mean_false, 4),
            "samples": len(false_durations),
        },
        "flags_true": {
            "p95_seconds": round(p95_true, 4),
            "mean_seconds": round(mean_true, 4),
            "samples": len(true_durations),
        },
        "degradation_p95_pct": round(
            ((p95_true - p95_false) / p95_false * 100) if p95_false else 0, 2
        ),
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
