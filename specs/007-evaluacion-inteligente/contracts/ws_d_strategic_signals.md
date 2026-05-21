# Contracts: WS-D Strategic Signals

---

## Detector de convergencia — clase concreta (sin Protocol)

`SklearnAgglomerativeConvergenceDetector` vive en
`application/evaluation/analytics/agglomerative_convergence.py`. **No
tiene Protocol** — sklearn-puro, unica impl. YAGNI.

```python
class SklearnAgglomerativeConvergenceDetector:
    async def detect(
        self,
        embeddings: list[tuple[str, list[float], datetime]],
    ) -> list[ConvergenceCluster]: ...
```

## `CollaborationNetworkBuilder` (`domain/ports/collaboration_network.py`)

```python
class CollaborationNetworkBuilder(Protocol):
    async def build(
        self,
        sources: list[SourceRef],
    ) -> CollaborationNetwork: ...
    def detect_bubbles(
        self,
        network: CollaborationNetwork,
        max_bubble_size: int = 8,
    ) -> list[list[str]]: ...
```

Adapter: extiende `GraphBuilder` (006) con nodos `Author`, `Inventor`,
edges `co_author`, `co_inventor`.

## `IdeaLineageTracer` (`domain/ports/idea_lineage.py`)

```python
class IdeaLineageTracer(Protocol):
    async def trace(
        self,
        idea: str,
        sources: list[SourceRef],
    ) -> IdeaLineage: ...
```

Adapter: navega citaciones via OpenAlex (`referenced_works`) hasta llegar
a hojas. Detecta circularidad con set membership.

## Detector de cambios de narrativa — clase concreta (sin Protocol)

`VaderNarrativeShiftDetector` vive en
`application/evaluation/analytics/vader_narrative_shift.py`. **No tiene
Protocol** — VADER + numpy puros. YAGNI.

```python
class VaderNarrativeShiftDetector:
    async def detect(
        self,
        topic: str,
        timeline: list[tuple[datetime, str]],
    ) -> list[NarrativeShift]: ...
```

## `TalentMobilityAnalyzer` (`domain/ports/talent_mobility.py`)

```python
class TalentMobilityAnalyzer(Protocol):
    async def analyze(
        self,
        author_ids: list[str],
    ) -> list[TalentMobility]: ...
```

Adapter: cruza historial OpenAlex con USPTO / Google Patents (via Serper
ya integrado en 006).

## `PatentingGapAnalyzer` (`domain/ports/patenting_gap.py`)

```python
class PatentingGapAnalyzer(Protocol):
    async def analyze(
        self,
        subdomains: list[str],
    ) -> list[PatentingGap]: ...
```

Adapter: query a OpenAlex (papers) y Serper Patents (patentes), divide
densidades.

---

## Pipeline step asociado

`StrategicSignalsStep` (en `application/agents/pipeline/strategic_signals_step.py`)
se inserta despues de `DeepAnalysisStep`. Produce los entities de WS-D y
los anade al `BranchResult.intelligence_sections`.
