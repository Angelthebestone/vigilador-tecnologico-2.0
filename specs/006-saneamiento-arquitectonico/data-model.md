# Data Model: Saneamiento Arquitectonico

## Domain Protocols (domain/ports/)

### LLMClient

**Archivo**: `src/vigilancia_multiagente/domain/ports/llm_client.py`

```python
class LLMClient(Protocol):
    async def generate(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> LLMResponse: ...
```

**Contrato**:
- `messages`: lista de mensajes en formato estandar (role, content).
- `temperature`: control de creatividad (0.0 = deterministico, 1.0 = creativo).
- `max_tokens`: maximo de tokens en la respuesta.
- Retorna `LLMResponse` con `content: str`, `finish_reason: str`, `usage: TokenUsage`.

**Implementaciones**: MiniMaxClient (infra/llm/minimax_client.py)

---

### EmbeddingGateway

**Archivo**: `src/vigilancia_multiagente/domain/ports/embedding_gateway.py`

```python
class EmbeddingGateway(Protocol):
    async def embed(self, texts: list[str]) -> list[list[float]]: ...
    async def embed_query(self, query: str) -> list[float]: ...
```

**Contrato**:
- `embed`: texto → vector. Batch de textos.
- `embed_query`: query → vector (puede usar estrategia diferente).
- Dimension de vectores definida por implementacion (tipicamente 768 o 1536).

**Implementaciones**: GeminiEmbeddingGateway (infra/embeddings/gemini_gateway.py)

---

### ToolExecutor

**Archivo**: `src/vigilancia_multiagente/domain/ports/tool_executor.py`

```python
class ToolExecutor(Protocol):
    async def execute(
        self,
        tool_name: str,
        params: dict[str, Any],
        context: ExecutionContext | None = None,
    ) -> ToolResult: ...
```

**Contrato**:
- `tool_name`: nombre registrado de la herramienta (ej: "tavily_search").
- `params`: parametros especificos de la herramienta.
- `context`: contexto de ejecucion (cache, timeout, etc.).
- Retorna `ToolResult` con `success: bool`, `data: Any`, `error: str | None`.

**Implementaciones**: MCPExecutionClient (infra/mcp/execution_client.py)

---

### VectorIndex

**Archivo**: `src/vigilancia_multiagente/domain/ports/vector_index.py`

```python
class VectorIndex(Protocol):
    async def upsert(self, vectors: list[VectorRecord]) -> None: ...
    async def search(
        self,
        query_vector: list[float],
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]: ...
    async def delete(self, ids: list[str]) -> None: ...
```

**Contrato**:
- `upsert`: inserta o actualiza vectores con metadata.
- `search`: similaridad coseno, retorna top_k resultados con score.
- `delete`: elimina por IDs.
- `VectorRecord`: `{id: str, vector: list[float], metadata: dict}`.
- `SearchResult`: `{id: str, score: float, metadata: dict}`.

**Implementaciones**: VectorIndex (infra/persistence/vector_index.py) via pgvector.

---

### GlobalKnowledgeStore

**Archivo**: `src/vigilancia_multiagente/domain/ports/global_knowledge_store.py`

```python
class GlobalKnowledgeStore(Protocol):
    async def store(self, snapshot: GlobalKnowledgeSnapshot) -> None: ...
    async def get_recent(
        self,
        session_ids: list[str] | None = None,
        limit: int = 10,
    ) -> list[GlobalKnowledgeSnapshot]: ...
    async def merge(
        self, snapshots: list[GlobalKnowledgeSnapshot]
    ) -> GlobalKnowledgeSnapshot: ...
```

**Contrato**:
- `store`: persiste un snapshot de conocimiento global.
- `get_recent`: recupera snapshots recientes (por sesion o global).
- `merge`: fusiona multiples snapshots en uno consolidado.
- `GlobalKnowledgeSnapshot`: entidad del dominio con grafo de entidades, relaciones, hallazgos.

**Implementaciones**: GlobalKnowledgeRepository (infra/persistence/global_knowledge_repository.py)

---

### SourceTrustStore

**Archivo**: `src/vigilancia_multiagente/domain/ports/source_trust_store.py`

```python
class SourceTrustStore(Protocol):
    async def record_interaction(
        self, source: str, outcome: TrustOutcome
    ) -> None: ...
    async def get_trust_score(self, source: str) -> float: ...
    async def get_reputation(
        self, author: str
    ) -> AuthorReputation | None: ...
```

**Contrato**:
- `record_interaction`: registra resultado de interaccion con fuente.
- `get_trust_score`: retorna score [0,1] para una fuente.
- `get_reputation`: retorna reputacion multidimensional de un autor.
- `TrustOutcome`: `{source: str, verified: bool, timestamp, confidence}`.
- `AuthorReputation`: `{h_index, retractions, affiliation, citation_count}`.

**Implementaciones**: SourceTrustRepository (infra/persistence/source_trust_repository.py)

---

### EventPublisher

**Archivo**: `src/vigilancia_multiagente/domain/ports/event_publisher.py`

```python
class EventPublisher(Protocol):
    async def publish(
        self, event: DomainEvent
    ) -> None: ...
    async def subscribe(
        self, event_type: str, handler: Callable
    ) -> None: ...
```

**Contrato**:
- `publish`: publica un evento de dominio.
- `subscribe`: registra handler para tipo de evento.
- `DomainEvent`: `{event_type, session_id, payload, timestamp}`.
- Eventos tipicos: `session_created`, `branch_completed`, `source_retracted`.

**Implementaciones**: EventLogDB (infra/persistence/event_log_repository.py)

---

## MCP Response Types (application/mcp/types.py)

```python
@dataclass(frozen=True)
class NavigationResult:
    url: str
    title: str
    content: str
    screenshot_path: str | None
    blocked: bool
    block_reason: str | None

@dataclass(frozen=True)
class ScreenshotResult:
    path: str
    width: int
    height: int
    format: str

@dataclass(frozen=True)
class SearchResult:
    query: str
    results: list[SourceResult]
    total_results: int
    source: str  # provider name

@dataclass(frozen=True)
class SourceResult:
    url: str
    title: str
    snippet: str
    source: str
    published_date: str | None
    trust_score: float | None

@dataclass(frozen=True)
class DocumentConversionResult:
    path: str
    format: str  # pdf, docx, pptx, etc.
    markdown: str
    page_count: int | None
    error: str | None
```

## Pipeline Types (application/agents/pipeline/)

```python
@dataclass
class PipelineContext:
    session_id: str
    branch_type: BranchType
    query: str
    findings: list[Finding]
    signals: list[Signal]
    state: dict[str, Any]  # paso a paso

class PipelineStep[T](Protocol):
    async def execute(self, context: PipelineContext) -> T: ...

class Pipeline:
    steps: list[PipelineStep]
    async def run(self, context: PipelineContext) -> BranchResult:
        for step in self.steps:
            result = await step.execute(context)
            context.state[step.__class__.__name__] = result
        return context.state.get("branch_result")
```

## Graph Types (application/graph/)

```python
@dataclass
class GraphEntity:
    id: str
    name: str
    entity_type: str  # PERSON | COMPANY | TECHNOLOGY | ...
    properties: dict[str, Any]

@dataclass
class GraphRelation:
    source: str  # entity id
    target: str  # entity id
    relation_type: str  # WORKS_FOR | DEVELOPS | ...
    weight: float
    evidence: list[str]  # source URLs

class GraphBuilder:
    async def build(
        self, findings: list[Finding]
    ) -> tuple[list[GraphEntity], list[GraphRelation]]: ...

class GraphAnalytics:
    async def centrality(
        self, entities: list[GraphEntity], relations: list[GraphRelation]
    ) -> dict[str, float]: ...
    async def detect_clusters(
        self, relations: list[GraphRelation]
    ) -> list[list[str]]: ...
    async def find_bridges(
        self, entities: list[GraphEntity], relations: list[GraphRelation]
    ) -> list[str]: ...
```
