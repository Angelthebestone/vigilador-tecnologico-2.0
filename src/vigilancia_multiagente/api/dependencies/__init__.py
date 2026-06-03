"""Composition root — wire all services in dependency order.

This package splits the monolithic dependencies.py into submodules:
- _singletons: @lru_cache factories for expensive objects
- session: DB connection, repositories, MCP clients
- governance: system base, prompt composer, contract loader
- assurance: WS-E Output Assurance
- source_quality: WS-A Source Quality
- data_intelligence: WS-B Data Intelligence
- deep_analysis: WS-C Deep Analysis
- strategic_signals: WS-D Strategic Signals
- execution: source scorer, linker, synthesizer, KPIs, memory
- agents: all 6 branch agents
- orchestration: orchestrator, coordinator, approve use case
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from vigilancia_multiagente.config.settings import get_settings

from .session import build_session_services, settings, database, PROJECT_ROOT
from .governance import build_governance_services
from .execution import build_execution_services
from .agents import build_agent_services
from .orchestration import build_orchestration_services

# ── Composition root ────────────────────────────────────────────────────
_s = build_session_services()
_g = build_governance_services(_s)
_e = build_execution_services(_s, _g)
_a = build_agent_services(_s, _g, _e)
_o = build_orchestration_services(_s, _g, _e, _a)

# Module-level exports (consumed by routes, tests, etc.)
settings = _s["settings"]
database = _s["database"]
session_repository = _s["session_repository"]
plan_repository = _s["plan_repository"]
branch_result_repository = _s["branch_result_repository"]
report_repository = _s["report_repository"]
vector_index = _s["vector_index"]
embedding_gateway = _s["embedding_gateway"]
llm_client = _s["llm_client"]
minimax_client = _s["minimax_client"]
execution_client = _s["execution_client"]
provider_registry = _s["provider_registry"]
mcp_cache = _s["mcp_cache"]

source_trust_repository = _g["source_trust_repository"]
source_scorer_service = _g["source_scorer_service"]
smart_router = _g["smart_router"]
governance_loader = _g["governance_loader"]
system_base_loader = _g["system_base_loader"]
system_base = _g["system_base"]
prompt_composer = _g["prompt_composer"]

clarification_service = _e["clarification_service"]
plan_builder = _e["plan_builder"]
source_scorer = _e["source_scorer"]
evidence_linker = _e["evidence_linker"]
event_log = _e["event_log"]
event_publisher = _e["event_publisher"]
report_synthesizer = _e["report_synthesizer"]
graph_service = _e["graph_service"]
metrics_service = _e["metrics_service"]
branch_kpi_service = _e["branch_kpi_service"]
prompt_regression_service = _e["prompt_regression_service"]
golden_cases_runner = _e["golden_cases_runner"]
artifact_service = _e["artifact_service"]
conversation_service = _e["conversation_service"]
global_knowledge_repository = _e["global_knowledge_repository"]
cross_session_service = _e["cross_session_service"]
report_generator = _e["report_generator"]

agents = _a["agents"]

ad_hoc_research_tools = _o["ad_hoc_research_tools"]
document_conversion_service = _o["document_conversion_service"]
trend_forecaster = _o["trend_forecaster"]
branch_coordinator = _o["branch_coordinator"]
orchestrator = _o["orchestrator"]
approve_research_usecase = _o["approve_research_usecase"]
graph_snapshot_repository = _o["graph_snapshot_repository"]
