"""Agent services — all 6 branch agents wired with governance and execution."""
from __future__ import annotations

from typing import Any

from vigilancia_multiagente.domain.models import BranchType


def build_agent_services(
    s: dict[str, Any], g: dict[str, Any], e: dict[str, Any],
) -> dict[str, Any]:
    """All 6 branch agents wired with governance and execution."""
    from vigilancia_multiagente.application.agents.avances_agent import AvancesAgent
    from vigilancia_multiagente.application.agents.comercial_agent import ComercialAgent
    from vigilancia_multiagente.application.agents.competitivo_agent import CompetitivoAgent
    from vigilancia_multiagente.application.agents.oportunidades_agent import OportunidadesAgent
    from vigilancia_multiagente.application.agents.pi_normativa_agent import PiNormativaAgent
    from vigilancia_multiagente.application.agents.riesgo_agent import RiesgoAgent

    _agent_classes: dict[BranchType, type] = {
        BranchType.AVANCES: AvancesAgent,
        BranchType.COMERCIAL: ComercialAgent,
        BranchType.RIESGO: RiesgoAgent,
        BranchType.PI_NORMATIVA: PiNormativaAgent,
        BranchType.COMPETITIVO: CompetitivoAgent,
        BranchType.OPORTUNIDADES: OportunidadesAgent,
    }
    agents = {}
    for bt, cls in _agent_classes.items():
        agents[bt] = cls(
            g["governance_loader"],
            s["provider_registry"],
            s["execution_client"],
            s["embedding_gateway"],
            s["minimax_client"],
            system_base=g.get("system_base"),
            prompt_composer=g["prompt_composer"],
            tool_router=g["smart_router"],
            event_publisher=e["event_publisher"],
            scholarly_works_gateway=s["scholarly_works_gateway"],
            reranker=s["reranker"],
            source_quality_step=e.get("source_quality_step"),
            data_intelligence_step=e.get("data_intelligence_step"),
            deep_analysis_step=e.get("deep_analysis_step"),
            strategic_signals_step=e.get("strategic_signals_step"),
        )
    return {"agents": agents}
