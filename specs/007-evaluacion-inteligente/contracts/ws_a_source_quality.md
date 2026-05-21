# Contracts: WS-A Source Quality

Protocols nuevos en `domain/ports/`. Cada Protocol nombra su archivo y sus
metodos. Las firmas usan tipos del `data-model.md`. Implementaciones
concretas en `infra/`.

---

## `AuthorReputationGateway` (`domain/ports/author_reputation.py`)

```python
class AuthorReputationGateway(Protocol):
    async def lookup(self, author_id: str) -> AuthorReputation | None: ...
    async def search_by_name(self, name: str, limit: int = 5) -> list[AuthorReputation]: ...
    async def refresh(self, author_id: str) -> AuthorReputation: ...
```

- Resiliencia: `lookup` devuelve `None` si la fuente externa no responde.
- Adapters: `OpenAlexAuthorReputationGateway`, `CrossrefAuthorReputationGateway`.

## `ConflictOfInterestAnalyzer` (`domain/ports/conflict_of_interest.py`)

```python
class ConflictOfInterestAnalyzer(Protocol):
    async def analyze(self, source: SourceRef) -> ConflictOfInterest | None: ...
```

Implementacion: parsea metadatos de fuente, busca menciones de financiadores
con prompts LLM dirigidos.

## `TemporalDecayConfigStore` (`domain/ports/temporal_decay.py`)

```python
class TemporalDecayConfigStore(Protocol):
    async def get(self, domain: str, source_type: str) -> TemporalDecayConfig: ...
    async def upsert(self, config: TemporalDecayConfig) -> None: ...
```

Adapter: `PostgresTemporalDecayConfigRepository`.

## `ExternalFactChecker` (`domain/ports/fact_checker.py`)

```python
class ExternalFactChecker(Protocol):
    async def verify(self, claim: str) -> ClaimExternalValidation: ...
```

Adapters: `GoogleFactCheckAdapter`, `WikidataFactCheckAdapter`.

## `RetractionMonitor` (`domain/ports/retraction_monitor.py`)

```python
class RetractionMonitor(Protocol):
    async def is_retracted(self, doi: str) -> RetractionRecord | None: ...
    async def daily_sync(self) -> int: ...  # returns count of new records
```

Adapter: `RetractionWatchCSVAdapter` (descarga CSV diario).

## `ReproducibilityChecker` (`domain/ports/reproducibility.py`)

```python
class ReproducibilityChecker(Protocol):
    async def score(self, finding: Finding) -> ReproducibilityScore: ...
```

Adapter: `GithubBasedReproducibilityChecker` (inspecciona repos referenciados).

---

## Pipeline step asociado

`SourceQualityStep` (en `application/agents/pipeline/source_quality_step.py`).
Inputs: `ToolLoopContext.executions`. Output: anota cada `Finding` con
- `author_reputation`, `conflict_of_interest`, `claim_external_validation`,
- `retraction_status`, `reproducibility_score`, `decay_weight`.

Inserta antes de `AssembleBranchResultStep` (pipeline del 006 FR-014).
