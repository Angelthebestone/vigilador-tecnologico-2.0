"""Data Intelligence services — WS-B."""
from __future__ import annotations

from typing import Any


def build_data_intelligence_services(
    s: dict[str, Any], g: dict[str, Any], e: dict[str, Any]
) -> dict[str, Any]:
    """DataIntelligenceStep + los 6 adapters WS-B. Solo cuando flag activo."""
    from vigilancia_multiagente.application.agents.pipeline.data_intelligence_step import (
        DataIntelligenceStep,
    )
    from vigilancia_multiagente.application.evaluation.authenticity.local_perplexity_detector import (
        LocalPerplexityAuthenticityDetector,
    )
    from vigilancia_multiagente.application.evaluation.ws_b.consensus_dispute_mapper import (
        ConsensusDisputeMapperImpl,
    )
    from vigilancia_multiagente.application.evaluation.ws_b.embedding_dedup import (
        EmbeddingBasedDeduplicator,
    )
    from vigilancia_multiagente.application.evaluation.ws_b.llm_multilingual import (
        LlmMultilingualNormalizer,
    )
    from vigilancia_multiagente.application.evaluation.ws_b.llm_query_expander import (
        LlmContextualQueryExpander,
    )
    from vigilancia_multiagente.application.evaluation.ws_b.pydantic_schema_registry import (
        PydanticExtractionSchemaRegistry,
    )
    from vigilancia_multiagente.infra.persistence.extraction_schema_repository import (
        PostgresExtractionSchemaRepository,
    )
    from vigilancia_multiagente.infra.search.bm25_plus_embedding import (
        BM25PlusEmbeddingSearchEngine,
    )

    di: dict[str, Any] = {}
    if not s["settings"].eval_ws_b_enabled:
        di["data_intelligence_step"] = None
        return di

    di["hybrid_search"] = BM25PlusEmbeddingSearchEngine(
        embedding_gateway=s["embedding_gateway"],
    )
    di["deduplicator"] = EmbeddingBasedDeduplicator(
        reranker=s["reranker"], threshold=0.92,
    )
    di["schema_registry"] = PydanticExtractionSchemaRegistry()
    di["multilingual"] = LlmMultilingualNormalizer(llm_client=s["llm_client"])
    di["authenticity_detector"] = LocalPerplexityAuthenticityDetector(
        llm_client=s["llm_client"],
    )
    from vigilancia_multiagente.application.evaluation.contradiction_analyzer import (
        ContradictionAnalyzer,
    )
    di["consensus_dispute"] = ConsensusDisputeMapperImpl(
        contradiction_analyzer=ContradictionAnalyzer(),
        embedding_gateway=s["embedding_gateway"],
    )
    di["query_expander"] = LlmContextualQueryExpander(llm_client=s["llm_client"])
    di["data_intelligence_step"] = DataIntelligenceStep(
        hybrid_search=di["hybrid_search"],
        deduplicator=di["deduplicator"],
        schema_registry=di["schema_registry"],
        multilingual=di["multilingual"],
        authenticity_detector=di["authenticity_detector"],
        consensus_dispute=di["consensus_dispute"],
    )
    return di
