"""Mock SSE event stream emitter with workstream support.

Emits a realistic sequence of SSE events (~30s total) including
all branch iterations, replan signals, fusion, graph building,
report generation, and evaluation with workstream data.
"""

import asyncio
import json
import random
from typing import Any

from mock_server.data.report import (
    BRANCH_ITERATIONS,
    FINAL_REPORT,
    REPLAN_SIGNALS,
)
from mock_server.data.workstreams import (
    MOCK_WSA_DATA,
    MOCK_WSB_DATA,
    MOCK_WSC_DATA,
    MOCK_WSD_DATA,
    MOCK_WSE_DATA,
)


def sse_event(event_type: str, data: Any) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def emit_research_stream(session_id: str, active_workstreams: set[str] | None = None):
    if active_workstreams is None:
        active_workstreams = set()

    branches = ["AVANCES", "COMERCIAL", "RIESGO", "PI_NORMATIVA", "COMPETITIVO", "OPORTUNIDADES"]

    await asyncio.sleep(0.3)

    yield sse_event("SessionStarted", {"sessionId": session_id, "userQuery": "IA generativa en manufactura automotriz"})
    await asyncio.sleep(0.3)

    # BranchStarted x6
    for branch in branches:
        yield sse_event("BranchStarted", {"branch": branch})
    await asyncio.sleep(0.5)

    delays = {
        "AVANCES": [1.0, 1.8, 1.5, 1.6, 2.0, 1.2],
        "COMERCIAL": [1.2, 1.6],
        "RIESGO": [1.4, 1.5],
        "PI_NORMATIVA": [1.0, 1.7, 1.5, 1.4, 1.6],
        "COMPETITIVO": [1.3, 1.4, 1.5],
        "OPORTUNIDADES": [1.1, 1.3, 2.0, 1.8],
    }

    max_iters = max(len(v) for v in BRANCH_ITERATIONS.values())
    for step_idx in range(max_iters):
        tasks = []
        for branch in branches:
            iters = BRANCH_ITERATIONS.get(branch, [])
            if step_idx < len(iters):
                branch_delays = delays.get(branch, [1.0] * max_iters)
                d = branch_delays[step_idx] if step_idx < len(branch_delays) else 1.0
                tasks.append((d, branch, iters[step_idx]))

        tasks.sort(key=lambda x: x[0])
        accumulated = 0.0
        for delay, branch, iteration in tasks:
            await asyncio.sleep(delay - accumulated)
            accumulated = delay
            yield sse_event("BranchProgress", {"branch": branch, "iteration": iteration})

        if step_idx == 0:
            await asyncio.sleep(0.4)
            for replan in REPLAN_SIGNALS:
                yield sse_event("ReplanTriggered", replan)
                await asyncio.sleep(0.5)

        await asyncio.sleep(0.3)

    await asyncio.sleep(0.5)

    if random.random() < 0.20:
        failed_branch = random.choice(branches)
        yield sse_event("BranchFailed", {"branch": failed_branch, "reason": "Error en proveedor MCP tavily: timeout excedido (30s)"})
        await asyncio.sleep(0.3)
        yield sse_event("BranchRestarted", {"branch": failed_branch, "reason": "Reintento con proveedor alternativo (exa)"})
        await asyncio.sleep(0.3)

    for branch in branches:
        yield sse_event("BranchCompleted", {"branch": branch})
        await asyncio.sleep(0.15)

    await asyncio.sleep(0.8)
    yield sse_event("AllBranchesCompleted", {"sessionId": session_id})

    await asyncio.sleep(1.0)
    yield sse_event("FusionStarted", {"sessionId": session_id})

    await asyncio.sleep(2.0)
    yield sse_event("FusionProgress", {"sessionId": session_id, "progress": 50})

    await asyncio.sleep(1.5)
    yield sse_event("FusionProgress", {"sessionId": session_id, "progress": 100})

    await asyncio.sleep(0.8)
    yield sse_event("GraphBuildingStarted", {"sessionId": session_id})

    await asyncio.sleep(2.0)
    yield sse_event("GraphAnalyticsComputed", {"sessionId": session_id})

    await asyncio.sleep(1.5)

    report = {**FINAL_REPORT, "sessionId": session_id}

    if active_workstreams:
        active_list = sorted(active_workstreams)
        evaluation = {
            "sessionId": session_id,
            "activeWorkstreams": active_list,
        }
        if "ws_a" in active_workstreams:
            evaluation["wsA"] = MOCK_WSA_DATA
        if "ws_b" in active_workstreams:
            evaluation["wsB"] = MOCK_WSB_DATA
        if "ws_c" in active_workstreams:
            evaluation["wsC"] = MOCK_WSC_DATA
        if "ws_d" in active_workstreams:
            evaluation["wsD"] = MOCK_WSD_DATA
        if "ws_e" in active_workstreams:
            evaluation["wsE"] = MOCK_WSE_DATA
        report["evaluation"] = evaluation

    yield sse_event("ReportGenerated", {"report": report})

    await asyncio.sleep(0.5)
    yield sse_event("ReportVariantsGenerated", {"types": ["technical", "executive", "risk", "investor"]})

    await asyncio.sleep(0.4)
    yield sse_event("EvaluationComputed", {
        "sessionId": session_id,
        "evaluations": [
            {"branchType": "AVANCES", "coverageKpi": 0.91, "precisionKpi": 0.87, "latencyMsKpi": 4320},
            {"branchType": "COMERCIAL", "coverageKpi": 0.83, "precisionKpi": 0.79, "latencyMsKpi": 3840},
            {"branchType": "RIESGO", "coverageKpi": 0.88, "precisionKpi": 0.85, "latencyMsKpi": 4100},
            {"branchType": "PI_NORMATIVA", "coverageKpi": 0.94, "precisionKpi": 0.91, "latencyMsKpi": 3650},
            {"branchType": "COMPETITIVO", "coverageKpi": 0.86, "precisionKpi": 0.83, "latencyMsKpi": 3920},
            {"branchType": "OPORTUNIDADES", "coverageKpi": 0.79, "precisionKpi": 0.76, "latencyMsKpi": 3510},
        ],
    })

    await asyncio.sleep(2.0)
