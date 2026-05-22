"""Mock research endpoints — all existing research routes preserved."""

import json
import random
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from mock_server.data.report import (
    BRANCH_ITERATIONS,
    CLARIFICATION_QUESTIONS,
    FINAL_REPORT,
    GRAPH_EDGES,
    GRAPH_NODES,
    MOCK_ECOSYSTEM,
    QUERY_EJEMPLO,
    RESEARCH_PLAN,
    SESSION_ID,
    SOURCES,
)
from mock_server.sse_emitter import emit_research_stream
from mock_server.routes.config import get_active_workstreams

router = APIRouter()


@router.post("/research/start")
async def research_start(body: dict):
    return {"sessionId": SESSION_ID, "status": "CLARIFYING", "questions": CLARIFICATION_QUESTIONS}


@router.post("/research/{session_id}/clarify")
async def research_clarify(session_id: str, body: dict):
    return {"sessionId": session_id, "status": "PLANNING", "requiresApproval": True, "plan": RESEARCH_PLAN}


@router.get("/research/{session_id}/plan")
async def research_plan(session_id: str):
    return {"sessionId": session_id, "plan": RESEARCH_PLAN}


@router.post("/research/{session_id}/approve")
async def research_approve(session_id: str):
    return {"sessionId": session_id, "status": "EXECUTING", "message": "Investigación iniciada. Conecte al stream SSE para seguir el progreso."}


@router.get("/research/{session_id}/stream")
async def research_stream(session_id: str):
    config = get_active_workstreams()
    active = {k for k, v in config.items() if v}
    return StreamingResponse(
        emit_research_stream(session_id, active),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/research/{session_id}/report")
async def research_report(session_id: str):
    config = get_active_workstreams()
    active_list = sorted([k for k, v in config.items() if v])
    report = {**FINAL_REPORT, "sessionId": session_id}
    if active_list:
        from mock_server.data.workstreams import (
            MOCK_WSA_DATA, MOCK_WSB_DATA, MOCK_WSC_DATA,
            MOCK_WSD_DATA, MOCK_WSE_DATA,
        )
        evaluation: dict[str, Any] = {
            "sessionId": session_id,
            "activeWorkstreams": active_list,
        }
        if "ws_a" in active_list:
            evaluation["wsA"] = MOCK_WSA_DATA
        if "ws_b" in active_list:
            evaluation["wsB"] = MOCK_WSB_DATA
        if "ws_c" in active_list:
            evaluation["wsC"] = MOCK_WSC_DATA
        if "ws_d" in active_list:
            evaluation["wsD"] = MOCK_WSD_DATA
        if "ws_e" in active_list:
            evaluation["wsE"] = MOCK_WSE_DATA
        report["evaluation"] = evaluation
    return report


@router.get("/research/{session_id}/sources")
async def research_sources(session_id: str):
    return {"sessionId": session_id, "total": len(SOURCES), "items": SOURCES}


@router.get("/research/{session_id}/graph")
async def research_graph(session_id: str):
    return {"sessionId": session_id, "nodes": GRAPH_NODES, "edges": GRAPH_EDGES}


@router.get("/research/{session_id}/graph/analytics")
async def research_graph_analytics(session_id: str):
    return {
        "sessionId": session_id,
        "centralNodes": [n["id"] for n in sorted(GRAPH_NODES, key=lambda x: -x["centrality"])[:5]],
        "clusters": [
            {"id": "cl1", "label": "Avances Técnicos", "nodeIds": ["n1", "n2", "n3", "n4", "c1"]},
            {"id": "cl2", "label": "Mercado y Comercial", "nodeIds": ["n5", "n6", "n7", "c2"]},
            {"id": "cl3", "label": "Riesgos", "nodeIds": ["n8", "n9", "n10"]},
            {"id": "cl4", "label": "Regulatorio / PI", "nodeIds": ["n12", "c3", "p1", "p2", "p3"]},
            {"id": "cl5", "label": "Panorama Competitivo", "nodeIds": ["co1", "co2", "co3", "co4", "co5", "per3"]},
            {"id": "cl6", "label": "Oportunidades", "nodeIds": ["n16", "n17", "n18"]},
        ],
        "density": 0.134,
        "avgPathLength": 2.47,
        "clusteringCoefficient": 0.412,
    }


@router.get("/research/{session_id}/graph/search")
async def research_graph_search(session_id: str, query: str = ""):
    q = query.lower()
    results = [{"nodeId": n["id"], "label": n["label"], "score": n["centrality"]} for n in GRAPH_NODES if q in n["label"].lower()]
    return {"items": results}


@router.get("/research/{session_id}/graph/path")
async def research_graph_path(session_id: str, sourceNodeId: str, targetNodeId: str):
    return {"nodeIds": [sourceNodeId, "n1", targetNodeId], "edgeIds": ["e1", "e4"], "totalCost": 0.42}


@router.get("/research/{session_id}/providers")
async def research_providers(session_id: str):
    return {
        "sessionId": session_id,
        "providers": [
            {"name": "tavily", "avgLatencyMs": 843, "errorRate": 0.02, "retryRate": 0.03},
            {"name": "arxiv", "avgLatencyMs": 612, "errorRate": 0.01, "retryRate": 0.01},
            {"name": "google_scholar", "avgLatencyMs": 1120, "errorRate": 0.04, "retryRate": 0.05},
            {"name": "exa", "avgLatencyMs": 754, "errorRate": 0.02, "retryRate": 0.02},
            {"name": "brave", "avgLatencyMs": 523, "errorRate": 0.01, "retryRate": 0.01},
            {"name": "fetch", "avgLatencyMs": 389, "errorRate": 0.00, "retryRate": 0.00},
            {"name": "serper", "avgLatencyMs": 671, "errorRate": 0.03, "retryRate": 0.03},
        ],
        "branchKpis": [
            {"branchType": "AVANCES", "coverageKpi": 0.91, "precisionKpi": 0.87, "latencyMsKpi": 4320},
            {"branchType": "COMERCIAL", "coverageKpi": 0.83, "precisionKpi": 0.79, "latencyMsKpi": 3840},
            {"branchType": "RIESGO", "coverageKpi": 0.88, "precisionKpi": 0.85, "latencyMsKpi": 4100},
            {"branchType": "PI_NORMATIVA", "coverageKpi": 0.94, "precisionKpi": 0.91, "latencyMsKpi": 3650},
            {"branchType": "COMPETITIVO", "coverageKpi": 0.86, "precisionKpi": 0.83, "latencyMsKpi": 3920},
            {"branchType": "OPORTUNIDADES", "coverageKpi": 0.79, "precisionKpi": 0.76, "latencyMsKpi": 3510},
        ],
        "confidenceScore": 0.847,
        "totalSources": 12,
        "totalFindings": 28,
        "confidenceCalibration": [
            {"bucket": "0.6-0.8", "predicted": 0.71, "observed": 0.64, "samples": 23, "factor": 0.90},
            {"bucket": "0.8-1.0", "predicted": 0.90, "observed": 0.86, "samples": 41, "factor": 0.96},
            {"bucket": "0.4-0.6", "predicted": 0.52, "observed": 0.55, "samples": 12, "factor": 1.06},
        ],
    }


@router.delete("/research/{session_id}")
async def research_delete(session_id: str):
    return {"status": "deleted", "sessionId": session_id}


@router.post("/sessions/{session_id}/ask")
async def session_ask(session_id: str, body: dict):
    query = body.get("query", "")
    return {"answer": f"Basándome en los hallazgos sobre '{QUERY_EJEMPLO}': Con respecto a '{query}', el análisis identificó convergencia hacia soluciones integradas.", "sources": [SOURCES[0]["id"], SOURCES[2]["id"]], "requiresPermission": False}


@router.delete("/sessions/{session_id}/conversation")
async def session_end_conversation(session_id: str):
    return {"status": "closed"}


@router.get("/sessions/timeline")
async def sessions_timeline():
    return {"sessions": [{"sessionId": SESSION_ID, "querySummary": QUERY_EJEMPLO, "timestamp": datetime.now(UTC).isoformat(), "entities": [n["label"] for n in GRAPH_NODES if n["nodeType"] in ("PERSON", "COMPANY")], "findingCount": 28}]}


@router.get("/reports/{report_id}/export")
async def report_export(report_id: str, format: str = "md"):
    content = FINAL_REPORT["markdown"]
    if format == "html":
        content = f"<html><body><pre>{content}</pre></body></html>"
    return {"content": content, "format": format, "reportId": report_id}


@router.patch("/sources/{source_id}/score")
async def source_score(source_id: str, body: dict):
    delta = body.get("delta", 0)
    return {"sourceId": source_id, "newScore": 75 + delta, "adjustment": delta, "reason": body.get("reason", "")}


@router.post("/upload/document")
async def upload_document():
    return {"markdown": "# Documento cargado\n\nContenido simulado del documento procesado.", "format": "pdf", "filename": "documento.pdf"}


@router.get("/research/{session_id}/graph/nodes")
async def research_graph_nodes(session_id: str):
    return {"sessionId": session_id, "total": len(GRAPH_NODES), "items": GRAPH_NODES}


@router.get("/research/{session_id}/graph/edges")
async def research_graph_edges(session_id: str):
    return {"sessionId": session_id, "total": len(GRAPH_EDGES), "items": GRAPH_EDGES}


@router.get("/research/{session_id}/graph/{node_id}/sources")
async def research_graph_node_sources(session_id: str, node_id: str):
    matched = [n for n in GRAPH_NODES if n["id"] == node_id]
    source_ids = matched[0].get("sourceIds", []) if matched else []
    return {"sessionId": session_id, "nodeId": node_id, "sourceNodeIds": source_ids}


@router.post("/research/{session_id}/modify")
async def research_modify(session_id: str, body: dict):
    return {"sessionId": session_id, "status": "PLANNING", "message": "Plan modificado exitosamente.", "plan": RESEARCH_PLAN}


@router.get("/research/{session_id}/graph/ecosystem")
async def research_graph_ecosystem(session_id: str, seed: str = "", depth: int = 2):
    return {"sessionId": session_id, "ecosystem": MOCK_ECOSYSTEM, "seed": seed, "depth": depth}


@router.get("/research/{session_id}/graph/search-cross-session")
async def research_graph_search_cross_session(session_id: str, query: str = "", limit: int = 10):
    return {"sessionId": session_id, "query": query, "limit": limit, "results": [
        {"sessionId": "prev-session-001", "querySummary": "Blockchain en cadena de suministro automotriz", "timestamp": "2026-03-10T14:00:00Z", "matchedNodes": [n["id"] for n in GRAPH_NODES if query.lower() in n["label"].lower()], "relevanceScore": 0.78},
        {"sessionId": "prev-session-002", "querySummary": "IoT industrial para mantenimiento predictivo", "timestamp": "2026-01-22T09:30:00Z", "matchedNodes": [], "relevanceScore": 0.65},
        {"sessionId": "prev-session-003", "querySummary": "Gemelos digitales en manufactura automotriz", "timestamp": "2025-11-05T16:45:00Z", "matchedNodes": ["n2", "n1"], "relevanceScore": 0.91},
    ]}


@router.post("/research/{session_id}/decision")
async def research_decision(session_id: str, body: dict):
    return {"sessionId": session_id, "decision": {"recommendedOption": "Inversión en IA para control de calidad", "scores": {"Integración gemelos digitales": 0.87, "Plataforma SaaS inspección visual": 0.82}, "confidence": 0.82}}


@router.post("/research/{session_id}/obsolescence")
async def research_obsolescence(session_id: str, body: dict):
    tech = body.get("tech", "Computer Vision")
    return {"sessionId": session_id, "results": [{"technology": tech, "obsolescenceRisk": random.choice(["alta", "media", "baja"]), "estimatedLifespan": "3-5 years"}]}


@router.post("/research/{session_id}/hype-analysis")
async def research_hype_analysis(session_id: str, body: dict):
    return {"sessionId": session_id, "hypeCycle": {"phase": "Trough of Disillusionment", "peakYear": 2026, "maturityHorizon": "2-5 years", "technologies": [{"name": "Generative AI for Manufacturing", "phase": "Peak of Inflated Expectations", "visibility": 0.85, "maturity": 0.30}]}}


# Sandbox endpoints
@router.post("/sandbox/execute")
async def sandbox_execute(body: dict):
    return {"status": "success", "stdout": json.dumps({"mean": 42.5, "std": 12.3}), "returncode": 0, "duration_ms": 350}


@router.post("/sandbox/list-libraries")
async def sandbox_list_libraries():
    return {"status": "success", "libraries": {"matplotlib": "3.10.3", "numpy": "1.26.4", "pandas": "2.2.3", "scipy": "1.15.2", "scikit-learn": "1.6.1", "scienceplots": "2.1.0"}}


@router.post("/sandbox/visualize")
async def sandbox_visualize(body: dict):
    PLACEHOLDER = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    return {"status": "success", "image": PLACEHOLDER, "format": "png", "metadata": {"generated_at": datetime.now(UTC).isoformat()}}


@router.get("/research/{session_id}/evaluation")
async def research_evaluation(session_id: str):
    config = get_active_workstreams()
    active_list = sorted([k for k, v in config.items() if v])
    result: dict[str, Any] = {"sessionId": session_id, "activeWorkstreams": active_list, "branchEvaluations": [
        {"branchType": "AVANCES", "coverageKpi": 0.91, "precisionKpi": 0.87, "latencyMsKpi": 4320},
        {"branchType": "COMERCIAL", "coverageKpi": 0.83, "precisionKpi": 0.79, "latencyMsKpi": 3840},
        {"branchType": "RIESGO", "coverageKpi": 0.88, "precisionKpi": 0.85, "latencyMsKpi": 4100},
        {"branchType": "PI_NORMATIVA", "coverageKpi": 0.94, "precisionKpi": 0.91, "latencyMsKpi": 3650},
        {"branchType": "COMPETITIVO", "coverageKpi": 0.86, "precisionKpi": 0.83, "latencyMsKpi": 3920},
        {"branchType": "OPORTUNIDADES", "coverageKpi": 0.79, "precisionKpi": 0.76, "latencyMsKpi": 3510},
    ]}

    from mock_server.data.workstreams import (
        MOCK_WSA_DATA, MOCK_WSB_DATA, MOCK_WSC_DATA, MOCK_WSD_DATA, MOCK_WSE_DATA,
    )
    if "ws_a" in active_list:
        result["wsA"] = MOCK_WSA_DATA
    if "ws_b" in active_list:
        result["wsB"] = MOCK_WSB_DATA
    if "ws_c" in active_list:
        result["wsC"] = MOCK_WSC_DATA
    if "ws_d" in active_list:
        result["wsD"] = MOCK_WSD_DATA
    if "ws_e" in active_list:
        result["wsE"] = MOCK_WSE_DATA
    return result
