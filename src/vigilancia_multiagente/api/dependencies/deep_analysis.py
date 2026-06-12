"""Deep Analysis services — WS-C."""

from __future__ import annotations

from typing import Any


def build_deep_analysis_services(
    s: dict[str, Any], g: dict[str, Any], e: dict[str, Any]
) -> dict[str, Any]:
    """DeepAnalysisStep + 5 servicios WS-C. Solo cuando flag activo."""
    from vigilancia_multiagente.application.agents.pipeline.deep_analysis_step import (
        DeepAnalysisStep,
    )
    from vigilancia_multiagente.application.evaluation.analytics.dersimonian_laird_meta import (
        DerSimonianLairdMetaAnalyzer,
    )
    from vigilancia_multiagente.application.evaluation.analytics.scipy_logistic_forecaster import (
        ScipyLogisticForecaster,
    )
    from vigilancia_multiagente.application.evaluation.ws_c.llm_assumption_detector import (
        LlmAssumptionDetector,
    )
    from vigilancia_multiagente.application.evaluation.ws_c.llm_counterfactual_synthesizer import (
        LlmCounterfactualSynthesizer,
    )
    from vigilancia_multiagente.application.evaluation.ws_c.llm_critical_dependency_mapper import (
        LlmCriticalDependencyMapper,
    )

    da: dict[str, Any] = {}
    if not s["settings"].eval_ws_c_enabled:
        da["deep_analysis_step"] = None
        return da

    da["forecaster"] = ScipyLogisticForecaster()
    da["meta_analyzer"] = DerSimonianLairdMetaAnalyzer()
    da["assumption_detector"] = LlmAssumptionDetector(
        llm=s["llm_client"],
        prompt_loader=s["prompt_loader"],
        errors_sink=e.get("report_assurance_errors", []),
    )
    from vigilancia_multiagente.application.graph.knowledge_graph_service import (
        KnowledgeGraphService,
    )

    da["dependency_mapper"] = LlmCriticalDependencyMapper(
        llm=s["llm_client"],
        graph_service=KnowledgeGraphService(),
        errors_sink=e.get("report_assurance_errors", []),
    )
    da["counterfactual_synthesizer"] = LlmCounterfactualSynthesizer(
        llm=s["llm_client"],
        prompt_loader=s["prompt_loader"],
        errors_sink=e.get("report_assurance_errors", []),
    )
    da["deep_analysis_step"] = DeepAnalysisStep(
        forecaster=da["forecaster"],
        meta_analyzer=da["meta_analyzer"],
        assumption_detector=da["assumption_detector"],
        dependency_mapper=da["dependency_mapper"],
        counterfactual_synthesizer=da["counterfactual_synthesizer"],
    )
    return da
