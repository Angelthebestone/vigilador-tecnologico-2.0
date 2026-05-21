# Contracts: WS-C Deep Analysis

---

## `AssumptionDetector` (`domain/ports/assumption_detector.py`)

```python
class AssumptionDetector(Protocol):
    async def detect(
        self,
        finding: Finding,
        source_text: str,
    ) -> list[ImplicitAssumption]: ...
```

Adapter: `LlmAssumptionDetector` usa `LLMClient` con prompts en
`prompts/evaluation/assumption_detection.txt`.

## Forecaster de curvas-S — clase concreta (sin Protocol)

`ScipyLogisticForecaster` vive en
`application/evaluation/analytics/scipy_logistic_forecaster.py`. **No
tiene Protocol** — es calculo puro con `scipy.optimize.curve_fit`, sin
frontera externa, unica implementacion plausible. YAGNI.

```python
class ScipyLogisticForecaster:
    def fit_s_curve(
        self,
        technology: str,
        domain: str,
        timeseries: list[tuple[int, int]],
    ) -> SCurveProjection: ...
    def detect_inflection(
        self,
        projection: SCurveProjection,
    ) -> int | None: ...
```

## `CriticalDependencyMapper` (`domain/ports/critical_dependency.py`)

```python
class CriticalDependencyMapper(Protocol):
    async def map(
        self,
        technology: str,
        findings: list[Finding],
    ) -> list[CriticalDependency]: ...
```

Adapter: combina `KnowledgeGraphService` (006) con prompts dirigidos al
LLM para clasificar dependencias.

## `CounterfactualSynthesizer` (`domain/ports/counterfactual.py`)

```python
class CounterfactualSynthesizer(Protocol):
    async def synthesize(
        self,
        report_draft: FinalReport,
        scenarios_n: int = 3,
    ) -> list[CounterfactualScenario]: ...
```

Adapter: `LlmCounterfactualSynthesizer`.

## Meta-analizador — clase concreta (sin Protocol)

`DerSimonianLairdMetaAnalyzer` vive en
`application/evaluation/analytics/dersimonian_laird_meta.py`. **No tiene
Protocol** — calculo puro con numpy, sin frontera externa. YAGNI.

```python
class DerSimonianLairdMetaAnalyzer:
    async def aggregate(
        self,
        topic: str,
        numeric_studies: list[dict],
    ) -> MetaAnalysisResult: ...
```

---

## Pipeline step asociado

`DeepAnalysisStep` (en `application/agents/pipeline/deep_analysis_step.py`)
se inserta despues de `AssembleBranchResultStep`. Anota cada Finding
con `implicit_assumptions`, `critical_dependencies`. Anade al contexto:
`SCurveProjection`, `MetaAnalysisResult`, `CounterfactualScenario[]`.
