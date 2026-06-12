"""Source Quality services — WS-A."""

from __future__ import annotations

from typing import Any


def build_source_quality_services(
    s: dict[str, Any], g: dict[str, Any], e: dict[str, Any]
) -> dict[str, Any]:
    """SourceQualityStep + los 6 adapters WS-A. Solo cuando flag activo."""
    from vigilancia_multiagente.application.agents.pipeline.source_quality_step import (
        SourceQualityStep,
    )
    from vigilancia_multiagente.application.evaluation.ws_a.github_reproducibility_checker import (
        GithubBasedReproducibilityChecker,
    )
    from vigilancia_multiagente.application.evaluation.ws_a.llm_conflict_analyzer import (
        LlmConflictOfInterestAnalyzer,
    )
    from vigilancia_multiagente.infra.factcheck.google_factcheck import GoogleFactCheckAdapter
    from vigilancia_multiagente.infra.factcheck.wikidata_factcheck import WikidataFactCheckAdapter
    from vigilancia_multiagente.infra.openalex.openalex_author_gateway import (
        OpenAlexAuthorReputationGateway,
    )
    from vigilancia_multiagente.infra.persistence.temporal_decay_repository import (
        PostgresTemporalDecayConfigRepository,
    )
    from vigilancia_multiagente.infra.retraction.retraction_watch_csv import (
        RetractionWatchCSVAdapter,
    )

    sq: dict[str, Any] = {}
    if not s["settings"].eval_ws_a_enabled:
        sq["source_quality_step"] = None
        return sq

    errors_sink: list[Any] = e.get("report_assurance_errors", [])
    temporal_repo = PostgresTemporalDecayConfigRepository(s["database"])
    sq["author_gateway"] = OpenAlexAuthorReputationGateway(errors_sink=errors_sink)
    sq["conflict_analyzer"] = LlmConflictOfInterestAnalyzer(
        llm=s["llm_client"],
        errors_sink=errors_sink,
    )
    sq["fact_checker_google"] = GoogleFactCheckAdapter(errors_sink=errors_sink)
    sq["fact_checker_wikidata"] = WikidataFactCheckAdapter()
    sq["retraction_monitor"] = RetractionWatchCSVAdapter(errors_sink=errors_sink)
    sq["reproducibility_checker"] = GithubBasedReproducibilityChecker(
        errors_sink=errors_sink,
    )
    sq["temporal_decay_store"] = temporal_repo
    sq["source_quality_step"] = SourceQualityStep(
        author_reputation_gateway=sq["author_gateway"],
        conflict_analyzer=sq["conflict_analyzer"],
        fact_checker=sq["fact_checker_google"],
        retraction_monitor=sq["retraction_monitor"],
        reproducibility_checker=sq["reproducibility_checker"],
        temporal_decay_store=sq["temporal_decay_store"],
    )
    return sq
