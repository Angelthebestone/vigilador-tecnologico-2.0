# Implementation Plan: Sistema de Evaluacion Inteligente — Reemplazo de Heuristicas Hardcodeadas

## Problem

El sistema actual de evaluacion usa heuristicas codificadas a mano que
limitan precision, adaptabilidad y escalabilidad: `SourceScorer` solo mira
dominio padre, `ConfidenceCalibrator` aplica `buzz = max(0, substance // 2)`
sin validacion empirica ni persistencia, TRL se infiere por senales
relativas, `ContradictionAnalyzer` usa solapamiento lexico, y la sintesis
no incluye meta-analisis, falsificacion, auditoria de sesgos ni trazabilidad
forense. Anadir cada nueva metrica requiere codigo ad-hoc, y nada de esto
corre en paralelo. La spec 006 dejo la base arquitectonica (hexagonal,
puertos, pipeline) lista; falta llenarla con inteligencia real.

## Approach

Construir cinco workstreams **independientes y paralelizables** (WS-A a
WS-E), cada uno con sus propios puertos en `domain/ports/`, adapters
concretos en `infra/`, y un `PipelineStep` que se inserta en el flujo del
spec 006 sin modificarlo. WS-E define golden cases primero — son la
especificacion ejecutable que el resto debe satisfacer. Toda heuristica
actual permanece en su sitio detras de un feature flag (`VT_EVAL_WS_*_ENABLED`);
el reemplazo se activa workstream-por-workstream cuando su golden case
suite pasa. La coexistencia controlada permite rollback inmediato y
respeta el constraint del spec ("sistema nuevo corre en paralelo").

---

## Technical Context

| Area | Decision |
|------|----------|
| Lenguaje / runtime | Python 3.11, asyncio, FastAPI (reuso 006). |
| Persistencia | PostgreSQL via SQLAlchemy/asyncpg. Migrations con alembic. 6 tablas nuevas (ver `data-model.md`). |
| LLM | `LLMClient` (006) reusado para deteccion de asunciones, simulacion stakeholders, falsificacion, expansion contextual. |
| Embeddings | `EmbeddingGateway` (006) reusado para busqueda hibrida, deduplicacion, convergencia. |
| Reranker | `Reranker` (006) reusado para deduplicacion semantica. |
| Busqueda hibrida | `rank_bm25` (nueva dep, ~200 LOC) + embeddings. |
| Modelado estadistico | `scipy.optimize.curve_fit` (curvas-S), DerSimonian-Laird (meta-analisis, numpy puro). |
| Clustering | `sklearn.cluster.AgglomerativeClustering`. |
| Sentimiento | `vaderSentiment` (~10 KB, sin estado). |
| Calibracion | `sklearn.isotonic.IsotonicRegression`. |
| Validacion JSON | `pydantic v2` (ya transitivo via FastAPI). |
| Fuentes externas WS-A | OpenAlex (autores, citas), Crossref (retracciones), Retraction Watch CSV, Google FactCheck Tools, Wikidata. |
| Pipeline | `Pipeline` (006) con 5 steps nuevos: SourceQualityStep, DataIntelligenceStep, DeepAnalysisStep, StrategicSignalsStep + ReportQualityGate (fuera del pipeline). |
| Flags | `VT_EVAL_WS_A_ENABLED` ... `VT_EVAL_WS_E_ENABLED` en `config/settings.py`. **Default de todas: `false`** — el sistema arranca exactamente igual que hoy. Cada WS se activa solo cuando su flag es explicitamente `true`. |
| Claves externas WS-A | `VT_GOOGLE_FACTCHECK_API_KEY`, `VT_RETRACTION_WATCH_CSV_URL`, `VT_OPENALEX_EMAIL` — todas con **default `None`**. Si una clave falta, el adapter correspondiente degrada (anade `StepError` con severity `warning` y retorna lista vacia/None); el WS sigue funcionando con menos senales. |
| Golden cases | `application/evaluation/golden_cases_runner.py` (heredado de 006 marcado deprecated) se reactiva como `GoldenCaseRunner`. |

## External Constraints

| Constraint | Impact |
|------------|--------|
| Coexistencia obligatoria con heuristicas | Todo componente nuevo va detras de feature flag; no se borra codigo previo hasta que su golden suite pase. |
| Spec 006 ya en main | Ningun cambio del 007 modifica el pipeline base; solo inserta pasos nuevos via `Pipeline(steps=[...])`. |
| Workstreams asignables a equipos distintos | Cada WS tiene su carpeta `application/evaluation/<ws>/` y sus puertos aislados. Cero shared mutable state entre WS. |
| Sin clave MiniMax activa hoy | Pasos LLM (WS-C, WS-E) propagan el fallo de forma trazable: si `LLMClient.complete` falla, el step registra un `StepError(workstream, reason, context)` en `Pipeline.errors[]` y deja su output como `None`. El siguiente step lo lee y decide si continuar o abortar. Cumple la constitucion ("cada error MUST propagarse o transformarse con contexto util") sin romper el pipeline. |
| Latencia maxima por sesion: comparable a 006 (~60s) | WS-A/B/C/D corren en paralelo entre si dentro de su step; WS-E es secuencial pero ligero (< 5s). |
| Sin migracion de datos historicos | Tablas nuevas vacias en startup; back-fill es opcional via cron, no requisito del spec. |

---

## Files to Create / Modify

### New Files (resumen — detalle por workstream en `contracts/`)

| File | Purpose |
|------|---------|
| `src/vigilancia_multiagente/domain/ports/{author_reputation,conflict_of_interest,temporal_decay,fact_checker,retraction_monitor,reproducibility}.py` | Protocols WS-A (6 puertos — todos cruzan frontera externa) |
| `src/vigilancia_multiagente/domain/ports/{hybrid_search,query_expander,dedup,extraction_schema,multilingual,consensus_dispute}.py` | Protocols WS-B (6 puertos). `ContentAuthenticityDetector` se descarta — calculo puro local sin segunda impl, vive como clase concreta `LocalPerplexityAuthenticityDetector` en `application/evaluation/authenticity/`. |
| `src/vigilancia_multiagente/domain/ports/{assumption_detector,critical_dependency,counterfactual}.py` | Protocols WS-C (3 puertos — todos LLM). `MetaAnalyzer` y `TechnologyTrajectoryForecaster` se descartan: calculos puros, viven en `application/evaluation/analytics/`. |
| `src/vigilancia_multiagente/domain/ports/{collaboration_network,idea_lineage,talent_mobility,patenting_gap}.py` | Protocols WS-D (4 puertos — todos cruzan frontera o extienden infra). `ConvergenceDetector` y `NarrativeShiftDetector` se descartan: calculos puros (sklearn/VADER), viven en `application/evaluation/analytics/`. |
| `src/vigilancia_multiagente/domain/ports/{golden_case_repository,golden_case_runner,stakeholder_simulator,falsification}.py` | Protocols WS-E (4 puertos — persistencia + LLM). `BiasAuditor`, `JsonbForensicTraceWriter`, `IsotonicConfidenceCalibrator` se descartan: calculos puros sobre metadatos / persistencia JSONB / IsotonicRegression, viven en `application/evaluation/{audit,forensic,calibration}/`. |
| `src/vigilancia_multiagente/infra/openalex/openalex_author_gateway.py` | Adapter de reputacion de autores |
| `src/vigilancia_multiagente/infra/factcheck/{google_factcheck,wikidata_factcheck}.py` | Adapters fact-checking |
| `src/vigilancia_multiagente/infra/retraction/retraction_watch_csv.py` | Adapter Retraction Watch |
| `src/vigilancia_multiagente/infra/search/bm25_plus_embedding.py` | Busqueda hibrida |
| `src/vigilancia_multiagente/application/evaluation/analytics/{scipy_logistic_forecaster,dersimonian_laird_meta,vader_narrative_shift,agglomerative_convergence}.py` | Implementaciones estadisticas (sin I/O externo — viven en application como clases concretas). |
| `src/vigilancia_multiagente/application/evaluation/calibration/isotonic_calibrator.py` | Calibrador isotonico (sin I/O externo). |
| `src/vigilancia_multiagente/application/evaluation/authenticity/local_perplexity_detector.py` | Deteccion de contenido IA local. |
| `src/vigilancia_multiagente/application/evaluation/audit/bias_auditor.py` | Auditor de sesgos (calculos sobre metadatos). |
| `src/vigilancia_multiagente/application/evaluation/forensic/jsonb_trace_writer.py` | Escritor de trazas (la persistencia ocurre en repositorios de `infra/`; este componente solo orquesta). |
| `src/vigilancia_multiagente/infra/persistence/{author_reputation_repository,temporal_decay_repository,extraction_schema_repository,golden_case_repository,calibration_curve_repository}.py` | Repositorios PostgreSQL |
| `src/vigilancia_multiagente/application/agents/pipeline/{source_quality_step,data_intelligence_step,deep_analysis_step,strategic_signals_step}.py` | 4 pipeline steps nuevos |
| `src/vigilancia_multiagente/application/evaluation/report_quality_gate.py` | Gate WS-E |
| `src/vigilancia_multiagente/application/evaluation/<ws_x>/...` | Logica por workstream (sub-paquetes) |
| `prompts/evaluation/{assumption_detection,counterfactual,falsification,stakeholder_*,query_expand}.txt` | Plantillas LLM |
| `migrations/versions/<id>_add_evaluation_tables.py` | 6 tablas nuevas |
| `scripts/seed_golden_cases.py` | Seed inicial de golden cases |
| `scripts/run_golden_cases.py` | Ejecutor manual |
| `scripts/benchmark_recall.py` | Verificacion SC-B01 |
| `tests/application/evaluation/<ws>/test_*.py` | Tests unitarios por componente |
| `tests/integration/test_pipeline_with_eval.py` | Integracion pipeline completo |
| `tests/golden/test_golden_suite.py` | Suite de golden cases como tests pytest |

### Modified Files

| File | Changes |
|------|---------|
| `src/vigilancia_multiagente/api/dependencies.py` | Anadir factories `_build_evaluation_services()` con los nuevos adapters; cablear los 4 pipeline steps en `BaseBranchAgent` cuando los flags esten activos. |
| `src/vigilancia_multiagente/application/agents/base.py` | `_build_pipeline()` lee flags y concatena los steps WS-A..D condicionalmente. |
| `src/vigilancia_multiagente/application/fusion/report_synthesizer.py` | Tras sintetizar invoca `ReportQualityGate` si flag WS-E activo. |
| `src/vigilancia_multiagente/application/evaluation/confidence_calibrator.py` | Reemplazar `buzz = max(0, substance // 2)` por `IsotonicConfidenceCalibrator.calibrate`; mantener como wrapper deprecado hasta que pase la golden suite. |
| `src/vigilancia_multiagente/application/evaluation/golden_cases_runner.py` | Quitar marca `DEPRECATED`, reescribir contra el nuevo `GoldenCaseRepository`. |
| `src/vigilancia_multiagente/domain/ports/__init__.py` | Re-export de todos los puertos nuevos. |
| `src/vigilancia_multiagente/config/settings.py` | Anadir flags `VT_EVAL_WS_*_ENABLED` y claves de APIs externas. |
| `docs/api-endpoints-reference.md` | Documentar el bloqueo 409 cuando el quality gate detecta sesgo critico. |
| `src/vigilancia_multiagente/application/evaluation/hype_detector.py` | Phase 3+5: la formula `buzz = max(0, substance // 2)` se reemplaza por llamadas a `TechnologyTrajectoryForecaster` + `IsotonicConfidenceCalibrator`. `_infer_maturity()` se elimina; el TRL viene del growth_rate de la curva-S. |
| `src/vigilancia_multiagente/application/evaluation/contradiction_analyzer.py` | Phase 2: el solapamiento lexico se conserva solo como fallback. `analyze()` delega en `ConsensusDisputeMapper` cuando WS-B activo. |
| `src/vigilancia_multiagente/application/evaluation/weak_signal_detector.py` | Phase 4: heuristica por frecuencia degradada a sub-senal; el resultado primario viene de `ConvergenceDetector` + `NarrativeShiftDetector`. |
| `src/vigilancia_multiagente/application/evaluation/obsolescence_detector.py` | Phase 3/4: heuristica por densidad reemplazada por cola descendente de `SCurveProjection`. |
| `src/vigilancia_multiagente/application/evaluation/finding_impact_scorer.py` | Phase 5: pesos fijos sustituidos por outputs del `IsotonicConfidenceCalibrator`; `convergencia` lee `ConvergenceCluster.growth_trend`. |
| `src/vigilancia_multiagente/application/evaluation/branch_kpi_service.py` | Phase 5: re-escrito como sub-fase de `ReportQualityGate`. Quita marca `DEPRECATED` del spec 006. |
| `src/vigilancia_multiagente/application/evaluation/golden_cases_runner.py` | Phase 0: reescrito sobre `GoldenCaseRepository` Protocol. Quita marca `DEPRECATED` del spec 006. |
| `src/vigilancia_multiagente/application/evaluation/prompt_regression_service.py` | Phase 0/5: integrado en `GoldenCaseRunner`. Quita marca `DEPRECATED` del spec 006. |
| `src/vigilancia_multiagente/application/research/followup_strategist.py` | Phase 2: reescrito contra `ContextualQueryExpander` Protocol con prompts en `prompts/evaluation/query_expand.txt`. |
| `src/vigilancia_multiagente/application/research/ad_hoc_tools_service.py` | Phase 2: el parseo manual de respuestas MCP se reemplaza por `ExtractionSchemaRegistry.validate()`. |
| `src/vigilancia_multiagente/api/routes/research_outputs.py` | Phase 3/4: endpoints `/maturity` y `/obsolescence` redirigen a los nuevos forecasters via adapter; preserva forma del DTO. |
| `src/vigilancia_multiagente/api/routes/research_outputs.py` (parseo) | Phase 2: `.get("results", [])` ad-hoc desaparece — el use case recibe DTOs ya validados. |

### Archivos que se ELIMINAN tras Phase 6

| Archivo | Razon |
|---------|-------|
| `src/vigilancia_multiagente/application/evaluation/confidence_calibrator.py` | LEGACY sin consumidores; el reemplazo (`IsotonicConfidenceCalibrator`) vive en `infra/calibration/`. Validado por SC-PLAN-07. |

---

## Deprecation Inventory

Lista exhaustiva del codigo legacy que el spec 007 reemplaza. Cada item
indica el archivo, el sintoma (linea o formula concreta), el reemplazo
en el nuevo sistema, la fase en la que se desactiva, y la fase en la
que se elimina. Cero deprecation queda sin reemplazo planificado.

Estados:
- **FLAG-OFF**: queda en el codigo, no se invoca cuando el flag del WS
  correspondiente esta `true`. Sirve como fallback.
- **DELETE-AFTER**: se borra cuando la golden suite del WS lleva 3
  semanas verde en produccion (criterio del Rollout Strategy).
- **MIGRATE**: el archivo se reescribe sobre el nuevo Protocol; no
  desaparece pero su implementacion cambia.

### A. Heuristicas de scoring (WS-A, WS-E las reemplazan)

| Archivo / sintoma | Linea | Reemplazo (spec 007) | Fase off | Fase delete |
|-------------------|-------|----------------------|----------|-------------|
| `application/evaluation/source_scorer.py` — `SourceScorer` snapshot (dominio padre + frecuencia, sin reputacion de autor) | 38–98 | `SourceQualityStep` ensambla `AuthorReputationGateway` + `ConflictOfInterestAnalyzer` + `TemporalDecayConfigStore` + `ReproducibilityChecker`. El snapshot scorer pasa a leer `AuthorReputation` y `effective_freshness` (WS-B) en vez del peso fijo. | Phase 1 (`VT_EVAL_WS_A_ENABLED`) | DELETE-AFTER (snapshot scorer permanece como adapter sobre `AuthorReputationGateway`) |
| `application/evaluation/source_scorer.py` — `SourceScorerService` (bonus/penalty fijos `+5/-10/+3`) | 116–158 | Mantiene la API pero los pesos `CONFIRMATION_BONUS`/`CONTRADICTION_PENALTY`/`CONFIRMER_BONUS` pasan a `TemporalDecayConfig` por dominio. | Phase 1 | MIGRATE (no se borra; se externalizan constantes) |
| `application/evaluation/hype_detector.py` — `buzz = max(0, substance // 2)` | 60 | `IsotonicConfidenceCalibrator` (WS-E) + meta-analisis cuantitativo (WS-C). El verdict (`exagerada`/`real`) lo determina la curva calibrada empirica, no la division por 2. | Phase 5 (`VT_EVAL_WS_E_ENABLED`) | DELETE-AFTER en Phase 6 |
| `application/evaluation/hype_detector.py` — TRL `_infer_maturity()` por reglas if/else sobre signals | 76 + helpers | `TechnologyTrajectoryForecaster` (WS-C) ajusta curva-S; el TRL se deriva del `growth_rate` e `inflection_year`. La `ReproducibilityChecker` (WS-A) aporta la segunda senal. | Phase 3 | DELETE-AFTER |
| `application/evaluation/confidence_calibrator.py` — buckets fijos sin persistencia, formula `actual_rate / mean_predicted` | 60–80 | `IsotonicConfidenceCalibrator` con `IsotonicRegression` + tabla `calibration_curve` + retrain con `golden_case_run`. | Phase 5 | DELETE en Phase 6 (sin consumidores hoy) |

### B. Analizadores lexicos (WS-B, WS-C, WS-D los reemplazan)

| Archivo / sintoma | Linea | Reemplazo (spec 007) | Fase off | Fase delete |
|-------------------|-------|----------------------|----------|-------------|
| `application/evaluation/contradiction_analyzer.py` — `polarity_conflict()` por solapamiento lexico de 4+ letras | 15, helpers en `claim_polarity.py` | `ConsensusDisputeMapper` (WS-B FR-B06) con embeddings + triangulacion. `claim_polarity.py` queda como helper interno pero deja de ser la fuente unica. | Phase 2 (`VT_EVAL_WS_B_ENABLED`) | MIGRATE (el archivo se reescribe sobre el Protocol; el solapamiento lexico se conserva solo como fallback) |
| `application/evaluation/weak_signal_detector.py` — heuristica por frecuencia de terminos | 129+ | `ConvergenceDetector` (WS-D FR-D01) + `NarrativeShiftDetector` (WS-D FR-D04). La deteccion por frecuencia pasa a ser sub-senal del clustering semantico. | Phase 4 (`VT_EVAL_WS_D_ENABLED`) | MIGRATE |
| `application/evaluation/obsolescence_detector.py` — heuristica por densidad de senales | 16+ | `NarrativeShiftDetector` + `TechnologyTrajectoryForecaster` (curva-S decreciente). La obsolescencia pasa a ser la cola descendente de la curva-S. | Phase 3 / Phase 4 | MIGRATE |
| `application/evaluation/finding_impact_scorer.py` — formula `autoridad × novedad × convergencia` con pesos fijos | 35+ | Mismo esqueleto pero los pesos los calibra `IsotonicConfidenceCalibrator` (WS-E) y `convergencia` consume `ConvergenceCluster.growth_trend`. | Phase 5 | MIGRATE |

### C. Pipeline de followup y queries (WS-B lo reemplaza)

| Archivo / sintoma | Linea | Reemplazo (spec 007) | Fase off | Fase delete |
|-------------------|-------|----------------------|----------|-------------|
| `application/research/followup_strategist.py` — `FollowupStrategist` con expansion estatica por `StrategistContext` | 30+ | `ContextualQueryExpander` (WS-B FR-B02) usa embeddings + LLM con prompts en `prompts/evaluation/query_expand.txt` y aprende de iteraciones previas. | Phase 2 | MIGRATE (el archivo se reescribe contra el Protocol) |
| `application/research/saturation.py` — `SaturationTracker` por umbrales fijos | n/a | Sin cambios funcionales — el saturation tracker es ortogonal. Solo se anota: cuando WS-B activo, el tracker mide saturation sobre candidatos deduplicados (`SemanticDeduplicator`). | — | NO DEPRECATED |
| `application/research/semantic_relations.py` — `build_relations` con score embebido | n/a | Sin cambios — reusa `EmbeddingGateway`. WS-B no toca esto. | — | NO DEPRECATED |

### D. Servicios marcados MIGRATE por spec 006

(Heredados del `evaluation-migration-plan.md` del spec 006; el spec 007
es quien los recibe.)

| Archivo | Estado en 006 | Reemplazo (spec 007) | Fase | Accion |
|---------|---------------|----------------------|------|--------|
| `application/evaluation/golden_cases_runner.py` | DEPRECATED — migrar a 007 | `GoldenCaseRunner` (Protocol) + `PostgresGoldenCaseRepository`; el archivo se reescribe sobre el nuevo Protocol y se quita la marca `DEPRECATED`. | Phase 0 | MIGRATE (reactivar) |
| `application/evaluation/branch_kpi_service.py` | DEPRECATED — migrar a 007 | Forma parte del `ReportQualityGate` como sub-fase de observabilidad: los KPIs (coverage, precision, latency, cost) se computan y se anexan a `FinalReport.assurance.kpis`. | Phase 5 | MIGRATE |
| `application/evaluation/prompt_regression_service.py` | DEPRECATED — migrar a 007 | Se integra en `GoldenCaseRunner`: cada golden case incluye expected prompts y el runner compara salidas LLM contra baseline historico (mismo deltas que el confidence calibrator). | Phase 0 / Phase 5 | MIGRATE |

### E. Parseo post-extraccion (WS-B FR-B04 lo reemplaza)

| Sitio del codigo | Sintoma | Reemplazo | Fase off | Fase delete |
|------------------|---------|-----------|----------|-------------|
| `application/research/ad_hoc_tools_service.py` y consumidores en `api/routes/research_outputs.py` | Parseo manual de respuestas MCP (`.get("results", [])`, splits, regex) | `ExtractionSchemaRegistry.validate()` con pydantic schemas por (`source_type`, `domain`). El parseo post-extraccion se elimina completo. | Phase 2 | DELETE-AFTER (codigo de parseo eliminado en cuanto WS-B este verde) |

### F. Endpoints API legacy

| Endpoint | Funcion legacy invocada | Reemplazo | Fase |
|----------|------------------------|-----------|------|
| `GET /research/{id}/maturity` (research_outputs.py:370) | `HypeDetector().analyze(...)` con `buzz = max(0, substance // 2)` | El mismo endpoint llama al pipeline WS-C (`TechnologyTrajectoryForecaster`) y devuelve `SCurveProjection` + calibrado. La forma del DTO de respuesta se preserva via adapter. | Phase 3 |
| `GET /research/{id}/obsolescence` (research_outputs.py:338) | `ObsolescenceDetector().analyze(...)` | El endpoint reusa `NarrativeShiftDetector` + `TechnologyTrajectoryForecaster` (cola descendente). Adapter mantiene compat. | Phase 4 |

### G. Verificacion automatizada (criterio de eliminacion)

Cada item con estado `DELETE-AFTER` se borra cuando se cumple:

1. Su flag (`VT_EVAL_WS_*_ENABLED`) lleva >= 21 dias consecutivos `true`
   en produccion.
2. La golden suite del WS correspondiente reporta 0 regresiones en ese
   periodo.
3. Un grep en el repo confirma que el simbolo no tiene consumidores
   fuera del propio archivo.

Comandos de verificacion (incluidos en `scripts/run_golden_cases.py`):

```bash
# B-1: la formula prohibida no debe existir
grep -rn "buzz = max(0, substance" src/  # debe ser vacio en Phase 6

# B-2: confidence_calibrator no debe ser importado
grep -rn "from .*evaluation.confidence_calibrator import" src/  # vacio post-007

# B-3: el hype_detector legacy no debe ser importado fuera de routes
grep -rn "from .*evaluation.hype_detector import" src/ \
  | grep -v "api/routes/research_outputs.py"  # vacio post-Phase 3
```

Estos comandos son los SCs **SC-PLAN-05** (ya declarado) + tres SCs
adicionales nuevos: **SC-PLAN-07**, **SC-PLAN-08**, **SC-PLAN-09**
(ver Success Criteria).

---

## Constitution Check (Pre-Design)

- **Gate result**: PASS
- **Alignment**:
  - **Pensar Antes de Codificar**: research.md lista todas las decisiones
    con alternativas evaluadas; los entities estan declarados en
    data-model.md antes de cualquier implementacion; cada Protocol esta
    nombrado en contracts/ con su firma exacta.
  - **Simplicidad Obligatoria**: ninguna dependencia nueva supera 200 KB;
    cada `PipelineStep` < 200 LOC; ningun WS introduce abstracciones para
    "flexibilidad futura"; las heuristicas viejas se conservan textualmente
    detras de un flag (cero refactor lateral). Los Protocols se crean
    solo si cruzan frontera externa o admiten >=2 implementaciones reales
    (criterio YAGNI): 8 calculos puros con unica impl viven como clases
    concretas en `application/evaluation/` (no en `domain/ports/`).
  - **Modularidad Primero**: cada WS tiene su carpeta y sus puertos; cero
    shared mutable state entre WS. La unica frontera comun es el contexto
    del Pipeline (006), que ya esta tipado.
  - **Cambios Quirurgicos y Trazables**: cada archivo modificado en la
    tabla "Modified Files" traza a una FR del spec (heuristica reemplazada
    o wiring de nuevo step). Archivos como `causal_timeline.py` que solo
    se enriquecerian "de paso" se sacan del plan: no se tocan en 007.
    Cero refactor lateral.
  - **Manejo de Errores Estricto**: fallos en pasos LLM o adapters
    externos NO se silencian. Se transforman en `StepError` (dataclass
    en `application/agents/pipeline/errors.py`) y se acumulan en
    `Pipeline.errors[]`. La `FinalReport` los expone para auditoria. El
    siguiente step decide degradacion vs aborto segun `severity`.
  - **Entrega Verificable**: cada workstream tiene SCs medibles en el
    spec; quickstart.md describe cuales endpoints/logs confirman la
    activacion; la golden suite (WS-E) sirve como spec ejecutable que
    bloquea regresiones.
- **Diseno de Software**:
  - **SRP**: cada Protocol cubre una operacion (1-3 metodos); cada step
    tiene una responsabilidad (anotar fuentes / busqueda / analisis /
    senales / gate).
  - **ISP**: los Protocols son pequenos y especializados — un consumer
    nunca depende de metodos que no usa.
  - **DIP**: la application solo conoce Protocols; los adapters
    (sklearn/scipy/httpx) viven en infra. Cero imports desde application
    a infra (validado por el script de 006 T005).
  - **OCP**: agregar un nuevo step (ej WS-F en el futuro) no requiere
    modificar steps existentes — basta concatenarlo en la lista del
    pipeline.
  - **KISS / YAGNI**: ningun puerto ni step se crea "por si acaso"; cada
    uno mapea a una FR del spec.
  - **POLA**: las flags siguen el patron del proyecto (`VT_<feature>_ENABLED`);
    los nombres de step (`SourceQualityStep`, etc.) reflejan su WS.
  - **Convencion sobre Configuracion**: todas las nuevas env vars tienen
    default sensato (`false` para flags; `None` para claves externas).
    Arrancar el sistema sin tocar `.env` produce el comportamiento
    actual del vigilador; cada WS se activa por opt-in explicito.

---

## Phases

### Phase 0 — Cimiento (Week 1)

**Goal**: Tablas, flags, golden cases minimos, esqueleto de Protocols.
**Independent Test Criteria**: `alembic upgrade head` aplica las 6
tablas; `scripts/seed_golden_cases.py` siembra >= 3 cases; `pytest -k golden` corre y pasa el smoke test.

1. Crear `migrations/versions/<id>_add_evaluation_tables.py` con las 6
   tablas (data-model.md).
2. Anadir flags `VT_EVAL_WS_A..E_ENABLED` en `config/settings.py`.
3. Definir los 30 Protocols en `domain/ports/` (firmas vacias, sin
   implementacion).
4. Implementar `GoldenCaseRepository` + `GoldenCaseRunner` (WS-E primero,
   spec ejecutable).
5. Sembrar 3 golden cases iniciales (alphafold-baseline, llm-chem,
   convergence-ai-bio).

### Phase 1 — WS-A Source Quality (Week 2-3)

**Goal**: Reemplazar SourceScorer con reputacion multidimensional.
**Independent Test Criteria**: WS-A corre como step del pipeline con
`VT_EVAL_WS_A_ENABLED=true`; SCs A01–A06 verificables.

1. Implementar adapters: OpenAlexAuthorReputationGateway, GoogleFactCheck,
   RetractionWatchCSV, GithubReproducibilityChecker.
2. `SourceQualityStep` inserta antes de `AssembleBranchResultStep`.
3. Cron job diario para `RetractionMonitor.daily_sync`.
4. Tests unitarios + integracion + 1 golden case dedicado.

### Phase 2 — WS-B Data Intelligence (Week 3-4, paralelo con WS-A)

**Goal**: Busqueda hibrida, deduplicacion semantica, esquemas JSON,
deteccion de contenido IA y frescura efectiva.
**Independent Test Criteria**: SC-B01..B05 verificables; recall medido
con `benchmark_recall.py`; `ai_probability` y `effective_freshness`
poblados para >= 95% de fuentes procesadas.

1. Adapter `BM25PlusEmbeddingSearchEngine`.
2. `DataIntelligenceStep` se inserta dentro de `ToolLoopStep` como
   sub-fase post-extraccion.
3. `ExtractionSchemaRegistry` con schemas pydantic por (source_type,
   domain).
4. `LocalPerplexityAuthenticityDetector` calcula `ContentAuthenticitySignal`
   por fuente; `SourceScorer` consume `effective_freshness` como peso
   multiplicativo cuando WS-B esta activo.
5. Mapas de consenso/disputa anotados en el contexto.

### Phase 3 — WS-C Deep Analysis (Week 4-5)

**Goal**: Curvas-S, meta-analisis, asunciones implicitas,
contrafactual.
**Independent Test Criteria**: SC-C01..C04 verificables; `DeepAnalysisStep`
enriquece todos los findings.

1. Adapters scipy/numpy (sin LLM).
2. Adapter LLM para asunciones y contrafactual con prompts dedicados.
3. Insertar `DeepAnalysisStep` post-`AssembleBranchResultStep`.

### Phase 4 — WS-D Strategic Signals (Week 5-6, paralelo con WS-C)

**Goal**: Convergencia, colaboracion, linaje, narrativa, movilidad,
brechas.
**Independent Test Criteria**: SC-D01..D04 verificables; un cluster de
convergencia detectado en corpus de prueba con > 6 meses de antelacion.

1. Extender `GraphBuilder` con nodos Author/Inventor (`CollaborationNetworkBuilder`).
2. Adapters sklearn (convergencia) + VADER (narrativa).
3. `StrategicSignalsStep` post-DeepAnalysis.

### Phase 5 — WS-E Output Assurance (Week 6-7)

**Goal**: Quality gate completo, falsificacion, sesgos, calibracion empirica.
**Independent Test Criteria**: SC-E01..E06 verificables; `buzz = max(0,
substance // 2)` desaparece del repo; calibrator persiste y se recarga.

1. `ReportQualityGate` orquesta los Protocols.
2. `IsotonicConfidenceCalibrator` reemplaza `ConfidenceCalibrator`.
3. Cron job re-entrena la curva con `golden_case_run`.
4. Bloqueo HTTP 409 cuando `BiasAudit.critical_bias_detected`.
5. Eliminar la heuristica vieja una vez que la golden suite tenga 3
   semanas sin regresiones.

### Phase 6 — Hardening y migracion controlada (Week 7-8)

**Goal**: Habilitar workstreams en produccion uno a la vez con observabilidad.
**Independent Test Criteria**: Metrica `evaluation_step_duration_seconds`
< limite por WS; tasa de errores < 1%; rollback funcional.

1. Anadir metricas Prometheus a cada step.
2. Documentar runbook de rollback.
3. Activar flags progresivamente en staging -> canary -> prod.
4. Retirar heuristicas cuando cada golden suite tenga 3 semanas verde.

---

## Rollout Strategy

- **Coexistencia**: Las heuristicas viejas (`SourceScorer`,
  `ConfidenceCalibrator`, `ContradictionAnalyzer`, etc.) permanecen
  intactas. Los pipeline steps WS-A..D solo se concatenan si su flag esta
  `True`. `ReportQualityGate` se invoca solo con `VT_EVAL_WS_E_ENABLED=true`.
- **Orden de activacion**: WS-E primero (golden cases), luego WS-A
  (mayor impacto en confianza), WS-B, WS-C, WS-D en cualquier orden.
- **Rollback**: cambiar la flag a `false` y reiniciar — sin cambios de
  schema irreversibles. Las 6 tablas nuevas son aditivas; no se modifican
  tablas existentes salvo columnas JSONB opcionales en `findings`.
- **Borrado de heuristicas**: solo despues de 3 semanas consecutivas con
  golden suite verde en produccion. Cada borrado es un PR independiente.
  La lista exhaustiva de archivos/lineas/formulas a eliminar esta en la
  seccion **Deprecation Inventory** mas arriba; ningun deprecation queda
  sin reemplazo planificado ni sin criterio de eliminacion verificable.
- **Migracion de datos**: no se migra historico. La calibracion arranca
  con curva identidad y se afina con runs reales.

---

## Success Criteria

(Se reusan los SCs del spec sin re-numerar. Los criterios verificables
agregados a este plan son:)

- **SC-PLAN-01**: `scripts/check-layer-imports.py` sigue reportando cero
  violaciones tras agregar todos los archivos del 007.
- **SC-PLAN-02**: `python -m basedpyright src/vigilancia_multiagente/`
  reporta 0 errores tras Phase 5.
- **SC-PLAN-03**: `pytest` pasa con todos los flags `false` (regresion
  cero sobre la base 006).
- **SC-PLAN-04**: `pytest` pasa con todos los flags `true` y los 3
  golden cases iniciales aprueban en CI.
- **SC-PLAN-05**: `grep -r "buzz = max(0, substance // 2)" src/` retorna
  vacio en el commit final de la Phase 5.
- **SC-PLAN-06**: latencia P95 de una sesion completa con todos los WS
  activos no excede 1.5× la latencia P95 con flags off (medido en
  benchmark dedicado).
- **SC-PLAN-07**: tras Phase 6, `confidence_calibrator.py` esta
  eliminado del repo y `grep -rn "from .*evaluation.confidence_calibrator
  import"` retorna vacio.
- **SC-PLAN-08**: tras Phase 6, las marcas `# DEPRECATED: migrar a spec
  007` que sobreviven al spec 006 (`branch_kpi_service`,
  `golden_cases_runner`, `prompt_regression_service`) estan reescritas
  contra sus nuevos Protocols (sin la marca) o eliminadas.
- **SC-PLAN-09**: tras Phase 6, el parseo post-extraccion manual
  (`.get("results", [])` ad-hoc en `ad_hoc_tools_service.py` y
  `research_outputs.py`) esta reemplazado por validacion pydantic via
  `ExtractionSchemaRegistry`. Grep `grep -rn "\.get('results', \[\])" src/`
  retorna 0 ocurrencias fuera de tests.

---

## Constitution Check (Post-Design)

- **Status**: PASS
- **Justification**:
  - **DRY**: cada calculo (curva-S, calibracion, BM25, sentimiento)
    existe en exactamente un adapter; no hay duplicacion entre WS.
  - **WET/AHA**: deliberadamente no se crea una abstraccion
    `EvaluationStep` comun por encima de los 4 steps WS-A..D porque
    cada step recibe inputs distintos (la abstraccion comun seria
    una bolsa de `dict[str, Any]` — peor que la duplicacion ligera de
    interfaz). Se preserva el contrato `PipelineStep[Ctx, Ctx]` ya
    existente del 006.
  - **Bajo Acoplamiento + Alta Cohesion**: los workstreams son
    independientes y se ensamblan solo via el Pipeline; el unico shared
    state es el contexto inmutable.
  - **DIP**: 23 nuevos Protocols (criterio: solo se crea Protocol cuando
    cruza frontera externa o admite >=2 impls reales). Cinco calculos
    puros que tenian unica impl (Meta-analisis, Curvas-S, Convergencia,
    Cambios de narrativa, Calibracion isotonica, Auditoria de sesgos,
    Trazas forenses, Deteccion de autenticidad) se quedan como clases
    concretas en `infra/analytics/` o `application/evaluation/` —
    cumple YAGNI. La application sigue sin importar nada de infra (DIP
    se preserva inyectando la clase concreta tipada por su clase, no
    por Protocol).
  - **ISP**: ningun Protocol tiene mas de 3 metodos; ningun cliente
    depende de metodos que no usa.
  - **OCP**: agregar WS-F (futuro) requeriria solo: nuevos Protocols,
    nuevo adapter, nuevo step, registrar en `dependencies.py`. Cero
    modificacion a steps existentes.
  - **CQS**: los Protocols separan claramente lecturas (`lookup`, `score`,
    `audit`) de comandos (`record_run`, `upsert`, `refresh`).
  - **POLA**: flags `VT_EVAL_*` siguen el patron del proyecto; estados
    de salida del gate (`pass`, `bias_blocked`, `calibration_warning`)
    usan los nombres semanticos del dominio.
  - **Verificable**: cada WS tiene SCs medibles ya en el spec; el plan
    anade golden cases como tests pytest reales que corren en CI.

**Gate result**: PASS — listo para `/speckit-tasks`.
