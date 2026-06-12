"""Strategic Signals services — WS-D."""

from __future__ import annotations

from typing import Any


def build_strategic_signals_services(
    s: dict[str, Any], g: dict[str, Any], e: dict[str, Any]
) -> dict[str, Any]:
    """StrategicSignalsStep + 6 detectores WS-D. Solo cuando flag activo."""
    from vigilancia_multiagente.application.agents.pipeline.strategic_signals_step import (
        StrategicSignalsStep,
    )
    from vigilancia_multiagente.application.evaluation.analytics.agglomerative_convergence import (
        SklearnAgglomerativeConvergenceDetector,
    )
    from vigilancia_multiagente.application.evaluation.analytics.vader_narrative_shift import (
        VaderNarrativeShiftDetector,
    )
    from vigilancia_multiagente.application.evaluation.ws_d.collaboration_network_builder import (
        CollaborationNetworkBuilderImpl,
    )
    from vigilancia_multiagente.application.evaluation.ws_d.patenting_gap_analyzer import (
        PatentingGapAnalyzerImpl,
    )
    from vigilancia_multiagente.application.evaluation.ws_d.talent_mobility_analyzer import (
        TalentMobilityAnalyzerImpl,
    )
    from vigilancia_multiagente.infra.openalex.openalex_idea_lineage import (
        OpenAlexIdeaLineageTracer,
    )

    ss: dict[str, Any] = {}
    if not s["settings"].eval_ws_d_enabled:
        ss["strategic_signals_step"] = None
        return ss

    ss["convergence_detector"] = SklearnAgglomerativeConvergenceDetector()
    ss["narrative_detector"] = VaderNarrativeShiftDetector()
    ss["lineage_tracer"] = OpenAlexIdeaLineageTracer(
        polite_mailto=s["settings"].openalex_email,
    )
    ss["collaboration_builder"] = CollaborationNetworkBuilderImpl()
    ss["mobility_analyzer"] = TalentMobilityAnalyzerImpl(
        tool_executor=s["execution_client"],
        provider_registry=s["provider_registry"],
    )
    ss["patenting_analyzer"] = PatentingGapAnalyzerImpl(
        tool_executor=s["execution_client"],
        provider_registry=s["provider_registry"],
    )
    ss["strategic_signals_step"] = StrategicSignalsStep(
        convergence_detector=ss["convergence_detector"],
        narrative_detector=ss["narrative_detector"],
        lineage_tracer=ss["lineage_tracer"],
        collaboration_builder=ss["collaboration_builder"],
        mobility_analyzer=ss["mobility_analyzer"],
        patenting_analyzer=ss["patenting_analyzer"],
    )
    return ss
