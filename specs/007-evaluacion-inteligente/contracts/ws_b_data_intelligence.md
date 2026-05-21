# Contracts: WS-B Data Intelligence

---

## `HybridSearchEngine` (`domain/ports/hybrid_search.py`)

```python
class HybridSearchEngine(Protocol):
    async def search(
        self,
        query: HybridSearchQuery,
        candidates: list[SourceRef],
        top_k: int = 10,
    ) -> list[SourceRef]: ...
```

Adapter: `BM25PlusEmbeddingSearchEngine` (combina `EmbeddingGateway` del 006
con `rank_bm25`).

## `ContextualQueryExpander` (`domain/ports/query_expander.py`)

```python
class ContextualQueryExpander(Protocol):
    async def expand(
        self,
        base_query: str,
        prior_iterations: list[IterationResult],
    ) -> list[str]: ...
```

Adapter: reusa `EmbeddingGateway` para terminos cercanos + LLM para
expansion contextual con prompts en `prompts/evaluation/query_expand.txt`.

## `SemanticDeduplicator` (`domain/ports/dedup.py`)

```python
class SemanticDeduplicator(Protocol):
    async def deduplicate(
        self,
        sources: list[SourceRef],
        threshold: float = 0.92,
    ) -> list[DedupedSource]: ...
```

Adapter: `EmbeddingBasedDeduplicator` reusa `Reranker` (006) sobre los
textos completos.

## `ExtractionSchemaRegistry` (`domain/ports/extraction_schema.py`)

```python
class ExtractionSchemaRegistry(Protocol):
    def get_schema(self, source_type: str, domain: str) -> ExtractionSchema: ...
    def validate(self, raw: dict, schema: ExtractionSchema) -> dict: ...
```

Adapter: `PydanticExtractionSchemaRegistry` (resuelve por tipo+dominio,
valida con pydantic v2).

## `MultilingualNormalizer` (`domain/ports/multilingual.py`)

```python
class MultilingualNormalizer(Protocol):
    async def detect_language(self, text: str) -> str: ...
    async def translate(self, text: str, target: str = "en") -> str: ...
    async def language_distribution(
        self, sources: list[SourceRef]
    ) -> dict[str, float]: ...
```

Adapter: `LlmMultilingualNormalizer` (usa `LLMClient` del 006 para
deteccion + traduccion en una sola llamada por documento).

## Deteccion de autenticidad — clase concreta (sin Protocol)

`LocalPerplexityAuthenticityDetector` vive en
`application/evaluation/authenticity/local_perplexity_detector.py`.
**No tiene Protocol** porque tiene una unica implementacion sin frontera
externa (combina perplejidad/burstiness via `LLMClient` en modo
log-prob con heuristicas de boilerplate). YAGNI: si en el futuro
aparece una segunda estrategia (modelo dedicado, API externa), entonces
se promueve a Protocol.

API:

```python
class LocalPerplexityAuthenticityDetector:
    def __init__(self, llm_client: LLMClient) -> None: ...

    async def analyze(
        self,
        source: SourceRef,
        raw_text: str,
        raw_freshness: float,
    ) -> ContentAuthenticitySignal: ...
```

Consumidor: la senal se anexa a cada Finding como `ai_probability` y
`effective_freshness`; `SourceScorer` (006) la lee como peso
multiplicativo en `score_source` cuando WS-B esta activo.

## `ConsensusDisputeMapper` (`domain/ports/consensus_dispute.py`)

```python
class ConsensusDisputeMapper(Protocol):
    async def build(
        self,
        findings: list[Finding],
    ) -> list[ConsensusDisputeMap]: ...
```

Reusa logica del `ContradictionAnalyzer` (006) extendida para mapear
graficamente quien dice que.

---

## Pipeline step asociado

`DataIntelligenceStep` (en `application/agents/pipeline/data_intelligence_step.py`).
Se inserta dentro de `ToolLoopStep` como sub-fase post-extraccion.
Reordena candidates con `HybridSearchEngine`, deduplica con
`SemanticDeduplicator`, valida con `ExtractionSchemaRegistry`, anota
`ContentAuthenticitySignal` por fuente y publica `ConsensusDisputeMap`
en el contexto.
