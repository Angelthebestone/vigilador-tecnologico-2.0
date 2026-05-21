# Tasks: Sistema de Evaluacion Inteligente — Reemplazo de Heuristicas Hardcodeadas

**Input**: `specs/007-evaluacion-inteligente/spec.md`, `plan.md`, `data-model.md`, `contracts/`, `quickstart.md`, `research.md`
**Feature**: 5 workstreams (WS-A..E) que reemplazan heuristicas con puertos de dominio, clases concretas en `application/evaluation/`, y pipeline steps. 23 Protocols nuevos + 8 clases concretas (calculos puros sin Protocol por YAGNI). Coexistencia controlada via flags `VT_EVAL_WS_*_ENABLED` con default `false`.

**User Story mapping**:

- **US1 = WS-E (Output Assurance)** — golden cases, calibracion, gate de calidad, falsificacion, sesgos, trazabilidad. **MVP minimo** — la golden suite es la spec ejecutable del resto.
- **US2 = WS-A (Source Quality)** — reputacion de autor, conflicto intereses, retractaciones, fact-checking, reproducibilidad.
- **US3 = WS-B (Data Intelligence)** — busqueda hibrida, deduplicacion, esquemas, multilingue, deteccion IA, consenso/disputa.
- **US4 = WS-C (Deep Analysis)** — curvas-S, meta-analisis, asunciones implicitas, contrafactual, dependencias criticas.
- **US5 = WS-D (Strategic Signals)** — convergencia, colaboracion, linaje, narrativa, movilidad, brechas de patentamiento.

---

## Phase 1: Setup

Goal: Cimiento comun. Sin estos artefactos ningun WS arranca.
Independent Test Criteria: `alembic upgrade head` aplica las 6 tablas; `pytest tests/test_settings.py` valida defaults de flags.

- [ ] T001 Anadir flags `VT_EVAL_WS_A_ENABLED` ... `VT_EVAL_WS_E_ENABLED` (default `false`) y claves opcionales `VT_GOOGLE_FACTCHECK_API_KEY`, `VT_RETRACTION_WATCH_CSV_URL`, `VT_OPENALEX_EMAIL` (default `None`) en `src/vigilancia_multiagente/config/settings.py`
- [ ] T002 [P] Anadir entradas correspondientes en `.env.example` con comentarios sobre opt-in y defaults
- [ ] T003 [P] Crear migration `migrations/versions/<id>_add_evaluation_tables.py` con las 6 tablas: `author_reputation`, `temporal_decay_config`, `extraction_schema`, `golden_case`, `golden_case_run`, `calibration_curve`
- [ ] T004 [P] Crear columnas JSONB opcionales `assumptions`, `external_validation`, `reproducibility`, `forensic_trace`, `authenticity` en tabla `findings` (mismo archivo de migration)
- [ ] T005 Crear `src/vigilancia_multiagente/application/agents/pipeline/errors.py` con dataclass `StepError(workstream, step_name, reason, exception_type, context, occurred_at, severity)` y extender `ToolLoopContext` con campo `errors: list[StepError]`
- [X] T006 [P] Crear directorio `prompts/evaluation/` con plantillas vacias placeholder: `assumption_detection.txt`, `counterfactual.txt`, `falsification.txt`, `stakeholder_investor.txt`, `stakeholder_regulator.txt`, `stakeholder_competitor.txt`, `stakeholder_academic.txt`, `query_expand.txt`
- [ ] T007 [P] Crear estructura de carpetas nuevas: `src/vigilancia_multiagente/application/evaluation/{analytics,authenticity,audit,calibration,forensic,ws_a,ws_b,ws_c,ws_d,ws_e}/__init__.py`, `src/vigilancia_multiagente/infra/{factcheck,retraction,search}/__init__.py`
- [ ] T008 [P] Crear `tests/application/evaluation/__init__.py`, `tests/integration/__init__.py`, `tests/golden/__init__.py`

---

## Phase 2: Foundational

Goal: Protocols base y manejo de errores listos antes de cualquier WS.
Independent Test Criteria: `python -m basedpyright src/vigilancia_multiagente/domain/ports/` reporta 0 errores; `scripts/check-layer-imports.py` sigue limpio.

- [ ] T009 [P] Definir entities frozen en `src/vigilancia_multiagente/domain/evaluation_entities.py` (referencia: data-model.md): `AuthorReputation`, `ConflictOfInterest`, `TemporalDecayConfig`, `ClaimExternalValidation`, `RetractionRecord`, `ReproducibilityScore`, `DedupedSource`, `ExtractionSchema`, `ConsensusDisputeMap`, `ContentAuthenticitySignal`, `ImplicitAssumption`, `SCurveProjection`, `CriticalDependency`, `CounterfactualScenario`, `MetaAnalysisResult`, `ConvergenceCluster`, `CollaborationNetwork`, `CollaborationNode`, `IdeaLineage`, `NarrativeShift`, `TalentMobility`, `Affiliation`, `PatentingGap`, `GoldenCase`, `GoldenCaseRun`, `ExpectedFinding`, `StakeholderSimulation`, `FalsificationScenario`, `BiasAudit`, `BiasThresholds`, `ForensicTrace`, `TraceStep`, `CalibrationCurve`, `HybridSearchQuery`
- [ ] T010 [P] Re-exportar entities en `src/vigilancia_multiagente/domain/__init__.py` (sub-modulo `evaluation`)
- [ ] T011 [P] Definir 6 Protocols WS-A en `src/vigilancia_multiagente/domain/ports/`: `author_reputation.py` (`AuthorReputationGateway`), `conflict_of_interest.py` (`ConflictOfInterestAnalyzer`), `temporal_decay.py` (`TemporalDecayConfigStore`), `fact_checker.py` (`ExternalFactChecker`), `retraction_monitor.py` (`RetractionMonitor`), `reproducibility.py` (`ReproducibilityChecker`)
- [ ] T012 [P] Definir 6 Protocols WS-B en `domain/ports/`: `hybrid_search.py` (`HybridSearchEngine`), `query_expander.py` (`ContextualQueryExpander`), `dedup.py` (`SemanticDeduplicator`), `extraction_schema.py` (`ExtractionSchemaRegistry`), `multilingual.py` (`MultilingualNormalizer`), `consensus_dispute.py` (`ConsensusDisputeMapper`)
- [ ] T013 [P] Definir 3 Protocols WS-C en `domain/ports/`: `assumption_detector.py` (`AssumptionDetector`), `critical_dependency.py` (`CriticalDependencyMapper`), `counterfactual.py` (`CounterfactualSynthesizer`)
- [ ] T014 [P] Definir 4 Protocols WS-D en `domain/ports/`: `collaboration_network.py` (`CollaborationNetworkBuilder`), `idea_lineage.py` (`IdeaLineageTracer`), `talent_mobility.py` (`TalentMobilityAnalyzer`), `patenting_gap.py` (`PatentingGapAnalyzer`)
- [ ] T015 [P] Definir 4 Protocols WS-E en `domain/ports/`: `golden_case_repository.py` (`GoldenCaseRepository`), `golden_case_runner.py` (`GoldenCaseRunner`), `stakeholder_simulator.py` (`StakeholderSimulator`), `falsification.py` (`FalsificationProber`)
- [ ] T016 Actualizar `src/vigilancia_multiagente/domain/ports/__init__.py` re-exportando los 23 Protocols nuevos en orden alfabetico, y actualizar la lista `__all__`
- [ ] T017 Anadir helper `add_step_error(context, workstream, step_name, exc, severity="warning")` en `src/vigilancia_multiagente/application/agents/pipeline/errors.py` y tests unitarios en `tests/application/agents/pipeline/test_step_error.py`
- [ ] T018 Anadir `errors: list[StepError]` al modelo `FinalReport` en `src/vigilancia_multiagente/domain/models.py` y exponerlo en el serializer

---

## Phase 3: US1 — WS-E Output Assurance (Golden Cases + Quality Gate) — MVP

Goal: La golden suite y el quality gate operan como spec ejecutable del resto. Habilitable con `VT_EVAL_WS_E_ENABLED=true`. Reemplaza `confidence_calibrator.py` por curva isotonica empirica.
Independent Test Criteria: `scripts/run_golden_cases.py --case alphafold-baseline` ejecuta y reporta delta vs expected; `grep -rn "buzz = max(0, substance" src/` retorna vacio; bloqueo HTTP 409 verificable cuando `BiasAudit.critical_bias_detected=true`.

### Persistencia y runner

- [ ] T019 [P] [US1] Implementar `PostgresGoldenCaseRepository` en `src/vigilancia_multiagente/infra/persistence/golden_case_repository.py` con `list_active`, `record_run`, `recent_runs` contra tablas `golden_case` / `golden_case_run`
- [ ] T020 [P] [US1] Implementar `PostgresCalibrationCurveRepository` en `src/vigilancia_multiagente/infra/persistence/calibration_curve_repository.py` con persistencia de mappings y activacion por `model_version`
- [X] T021 [US1] Implementar `OrchestratorGoldenCaseRunner` en `src/vigilancia_multiagente/application/evaluation/ws_e/orchestrator_golden_case_runner.py`: invoca el flujo completo en modo sandbox (sin escribir produccion) y compara con `expected_findings` / `expected_confidence`

### Clases concretas (sin Protocol — YAGNI)

- [ ] T022 [P] [US1] Implementar `IsotonicConfidenceCalibrator` en `src/vigilancia_multiagente/application/evaluation/calibration/isotonic_calibrator.py` usando `sklearn.isotonic.IsotonicRegression`: `calibrate`, `retrain(runs)`, `active_curve()`. Persiste via `CalibrationCurveRepository`
- [ ] T023 [P] [US1] Implementar `BiasAuditor` en `src/vigilancia_multiagente/application/evaluation/audit/bias_auditor.py`: agrega distribuciones geografica/genero/institucional desde metadatos del reporte; aplica `BiasThresholds` y produce `BiasAudit`
- [ ] T024 [P] [US1] Implementar `JsonbForensicTraceWriter` en `src/vigilancia_multiagente/application/evaluation/forensic/jsonb_trace_writer.py`: `record_step(claim_id, step, confidence)` y `finalize(claim_id)` persistiendo en columna JSONB de `findings`

### Adapters LLM-driven (Protocols)

- [ ] T025 [P] [US1] Implementar `LlmStakeholderSimulator` en `src/vigilancia_multiagente/application/evaluation/ws_e/llm_stakeholder_simulator.py` (un prompt por tipo de stakeholder en `prompts/evaluation/stakeholder_<type>.txt`); fallo LLM -> `StepError(workstream=WS-E, severity=warning)`
- [ ] T026 [P] [US1] Implementar `LlmFalsificationProber` en `src/vigilancia_multiagente/application/evaluation/ws_e/llm_falsification_prober.py` usando `prompts/evaluation/falsification.txt`; lista vacia -> `falsifiable=False`

### Quality gate orquestador

- [X] T027 [US1] Implementar `ReportQualityGate` en `src/vigilancia_multiagente/application/evaluation/report_quality_gate.py` orquestando en orden: (1) `ForensicTraceWriter.finalize` por claim, (2) `BiasAuditor.audit` -> si critical_bias_detected lanza `QualityGateBlocked`, (3) `FalsificationProber.probe` por conclusion, (4) `StakeholderSimulator.simulate` para 4 perfiles, (5) `IsotonicConfidenceCalibrator.calibrate` ajusta confianzas. Output anexado a `FinalReport.assurance` (nuevo campo)
- [ ] T028 [US1] Anadir campo `assurance: ReportAssurance | None` a `FinalReport` en `src/vigilancia_multiagente/domain/models.py` con sub-entidad serializable

### Wiring

- [ ] T029 [US1] En `src/vigilancia_multiagente/api/dependencies.py` anadir factory `_build_assurance_services(s, g, e)` que instancia los 6 servicios de WS-E y registra `report_quality_gate`. Llamar solo si `settings.eval_ws_e_enabled`
- [ ] T030 [US1] En `src/vigilancia_multiagente/application/fusion/report_synthesizer.py` invocar `ReportQualityGate.run(report)` tras sintetizar cuando el gate este inyectado. Si lanza `QualityGateBlocked`, propagar la excepcion al endpoint
- [X] T031 [US1] En `src/vigilancia_multiagente/api/routes/research_outputs.py` capturar `QualityGateBlocked` y responder HTTP 409 con detalle del sesgo critico

### Migracion legacy

- [X] T032 [US1] Reescribir `src/vigilancia_multiagente/application/evaluation/golden_cases_runner.py` como thin adapter sobre `GoldenCaseRunner` Protocol (delega al runner inyectado). Quitar marca `# DEPRECATED: migrar a spec 007`
- [X] T033 [US1] Reescribir `src/vigilancia_multiagente/application/evaluation/prompt_regression_service.py` como sub-fase del runner: cada `GoldenCase` puede incluir `expected_prompts`; el runner compara salidas. Quitar marca `# DEPRECATED`
- [X] T034 [US1] Reescribir `src/vigilancia_multiagente/application/evaluation/branch_kpi_service.py` para que `ReportQualityGate` lo invoque como sub-fase. KPIs (coverage, precision, latency, cost) van a `FinalReport.assurance.kpis`. Quitar marca `# DEPRECATED`

### Eliminacion controlada de heuristicas WS-E

- [ ] T035 [US1] Tras 3 semanas de golden suite verde con `VT_EVAL_WS_E_ENABLED=true` en prod: eliminar `src/vigilancia_multiagente/application/evaluation/confidence_calibrator.py` y todos sus imports. Verificar `grep -rn "from .*evaluation.confidence_calibrator import" src/` vacio
- [ ] T036 [US1] Reemplazar `buzz = max(0, substance // 2)` en `src/vigilancia_multiagente/application/evaluation/hype_detector.py:60` por llamada a `IsotonicConfidenceCalibrator.calibrate(substance / max_substance_seen)`. La `verdict` (`exagerada`/`real`) se deriva del valor calibrado vs umbrales aprendidos
- [ ] T037 [US1] Verificar `grep -rn "buzz = max(0, substance" src/` retorna vacio tras T036

### Scripts y golden cases iniciales

- [ ] T038 [P] [US1] Crear `scripts/seed_golden_cases.py --suite minimum` que inserta 3 golden cases: `alphafold-baseline`, `llm-chem`, `convergence-ai-bio` en tabla `golden_case` con expected_findings y expected_confidence
- [ ] T039 [P] [US1] Crear `scripts/run_golden_cases.py [--case <name>]` que ejecuta uno o todos via `OrchestratorGoldenCaseRunner` y reporta delta vs expected
- [ ] T040 [P] [US1] Crear `tests/golden/test_golden_suite.py` que parametriza un test por golden case activo (fixture leyendo `GoldenCaseRepository.list_active`), corre el runner y aserta delta de confianza <= 0.05

### Tests

- [ ] T041 [P] [US1] `tests/application/evaluation/ws_e/test_isotonic_calibrator.py`: verifica curva identidad con < 50 muestras, curva ajustada con dataset sintetico, persistencia/recarga
- [ ] T042 [P] [US1] `tests/application/evaluation/ws_e/test_bias_auditor.py`: dataset sintetico con sobre-representacion geografica > 70% -> `critical_bias_detected=true`
- [ ] T043 [P] [US1] `tests/application/evaluation/ws_e/test_falsification_prober.py`: LLM mock devuelve 0 escenarios -> `falsifiable=False`; >= 1 escenario -> `falsifiable=True`
- [ ] T044 [P] [US1] `tests/application/evaluation/ws_e/test_quality_gate.py`: orquesta el orden correcto; cuando bias critical -> levanta `QualityGateBlocked`
- [ ] T045 [P] [US1] `tests/integration/test_research_outputs_409.py`: con flag activo y fixture de sesgo critico, endpoint responde 409
- [ ] T046 [P] [US1] `tests/application/evaluation/ws_e/test_forensic_trace_writer.py`: anota 3 pasos para un claim_id, `finalize` retorna `ForensicTrace` con cadena ordenada y confianzas

---

## Phase 4: US2 — WS-A Source Quality

Goal: Reemplazar SourceScorer por reputacion multidimensional. Habilitable con `VT_EVAL_WS_A_ENABLED=true`.
Independent Test Criteria: SCs A01..A06 del spec verificables; `SourceQualityStep` enriquece findings con `author_reputation`, `conflict_of_interest`, `claim_external_validation`, `retraction_status`, `reproducibility_score`, `decay_weight`.

### Repositorio y config

- [ ] T047 [P] [US2] Implementar `PostgresAuthorReputationRepository` en `src/vigilancia_multiagente/infra/persistence/author_reputation_repository.py` (CRUD sobre tabla `author_reputation`, validacion `last_refreshed > now() - 30d`)
- [ ] T048 [P] [US2] Implementar `PostgresTemporalDecayConfigRepository` en `src/vigilancia_multiagente/infra/persistence/temporal_decay_repository.py` (`get`, `upsert`)
- [ ] T049 [P] [US2] Seed inicial de `TemporalDecayConfig` por dominio en `scripts/seed_temporal_decay.py` (AI=12 meses, MATH=60, BIO=24, etc.) ejecutable manualmente

### Adapters externos

- [ ] T050 [P] [US2] Implementar `OpenAlexAuthorReputationGateway` en `src/vigilancia_multiagente/infra/openalex/openalex_author_gateway.py` con `lookup`, `search_by_name`, `refresh` reusando `httpx` client + polite pool via `VT_OPENALEX_EMAIL`; fallo -> `None` + `StepError(severity=warning)`
- [ ] T051 [P] [US2] Implementar `GoogleFactCheckAdapter` en `src/vigilancia_multiagente/infra/factcheck/google_factcheck.py` (lee `VT_GOOGLE_FACTCHECK_API_KEY`; sin clave -> degrada a `ClaimExternalValidation(status="not_found")`)
- [ ] T052 [P] [US2] Implementar `WikidataFactCheckAdapter` en `src/vigilancia_multiagente/infra/factcheck/wikidata_factcheck.py` (sin clave, public SPARQL endpoint)
- [ ] T053 [P] [US2] Implementar `RetractionWatchCSVAdapter` en `src/vigilancia_multiagente/infra/retraction/retraction_watch_csv.py` con `is_retracted(doi)` (lookup en cache local) y `daily_sync()` (descarga CSV via `VT_RETRACTION_WATCH_CSV_URL`)
- [ ] T054 [P] [US2] Implementar `GithubBasedReproducibilityChecker` en `src/vigilancia_multiagente/application/evaluation/ws_a/github_reproducibility_checker.py`: inspecciona URLs referenciadas en finding (repo publico, README, Dockerfile/nix/conda) y produce `ReproducibilityScore`

### Analyzer y step

- [ ] T055 [P] [US2] Implementar `LlmConflictOfInterestAnalyzer` en `src/vigilancia_multiagente/application/evaluation/ws_a/llm_conflict_analyzer.py` (parsea menciones de financiadores en metadatos via prompts dirigidos al LLM)
- [ ] T056 [US2] Implementar `SourceQualityStep` en `src/vigilancia_multiagente/application/agents/pipeline/source_quality_step.py` que inserta antes de `AssembleBranchResultStep`. Para cada `Finding` consulta los 6 servicios y anota: `author_reputation`, `conflict_of_interest`, `claim_external_validation`, `retraction_status`, `reproducibility_score`, `decay_weight`. Fallos -> `StepError`

### Wiring + cron

- [ ] T057 [US2] En `dependencies.py` anadir factory `_build_source_quality_services` que instancia los 6 servicios y registra `source_quality_step`. Llamar solo si `settings.eval_ws_a_enabled`
- [ ] T058 [US2] En `src/vigilancia_multiagente/application/agents/base.py:_build_pipeline()` concatenar `SourceQualityStep` antes de `AssembleBranchResultStep` cuando esta inyectado
- [ ] T059 [US2] Crear cron job `scripts/cron_retraction_sync.py` que invoca `RetractionMonitor.daily_sync()` y registra metricas; documentar en `docs/api-endpoints-reference.md`

### Migracion legacy (WS-A externaliza pesos)

- [ ] T060 [US2] Refactor `src/vigilancia_multiagente/application/evaluation/source_scorer.py`: `SourceScorerService.CONFIRMATION_BONUS/CONTRADICTION_PENALTY/CONFIRMER_BONUS` pasan a leer de `TemporalDecayConfig` por dominio cuando WS-A activo. Mantener constantes hardcoded como fallback con flag off

### Tests

- [ ] T061 [P] [US2] `tests/application/evaluation/ws_a/test_openalex_author_gateway.py` (mock httpx, valida estructura `AuthorReputation`)
- [ ] T062 [P] [US2] `tests/application/evaluation/ws_a/test_retraction_monitor.py` (CSV fixture con 5 DOIs, valida invalidacion)
- [ ] T063 [P] [US2] `tests/application/evaluation/ws_a/test_conflict_analyzer.py` (LLM mock; ratio >= 0.7 -> high)
- [ ] T064 [P] [US2] `tests/application/evaluation/ws_a/test_reproducibility_checker.py` (fixtures con repo Github + repo sin repo)
- [ ] T065 [P] [US2] `tests/application/evaluation/ws_a/test_source_quality_step.py` (integracion: pipeline + 6 servicios mockeados, valida anotacion completa)
- [ ] T066 [P] [US2] `tests/golden/test_source_quality_golden.py`: golden case `author-reputation-baseline` con fuente conocida (h_index documentado)

---

## Phase 5: US3 — WS-B Data Intelligence

Goal: Busqueda hibrida, deduplicacion, esquemas pydantic, multilingue, deteccion IA, consenso/disputa. Habilitable con `VT_EVAL_WS_B_ENABLED=true`.
Independent Test Criteria: SCs B01..B05 verificables; `benchmark_recall.py` mide recall@10 con/sin flag; `ai_probability` y `effective_freshness` poblados para >= 95% de fuentes.

### Repositorio

- [ ] T067 [P] [US3] Implementar `PostgresExtractionSchemaRepository` en `src/vigilancia_multiagente/infra/persistence/extraction_schema_repository.py` con versionado

### Adapters

- [ ] T068 [P] [US3] Anadir dep `rank_bm25` en `pyproject.toml` (justificacion ya en research.md)
- [ ] T069 [P] [US3] Implementar `BM25PlusEmbeddingSearchEngine` en `src/vigilancia_multiagente/infra/search/bm25_plus_embedding.py`: combina scores BM25 (rank_bm25) + cosine similarity (EmbeddingGateway) con pesos `HybridSearchQuery.{vector_weight,keyword_weight}`
- [ ] T070 [P] [US3] Implementar `LlmContextualQueryExpander` en `src/vigilancia_multiagente/application/evaluation/ws_b/llm_query_expander.py` (prompts en `prompts/evaluation/query_expand.txt`) que aprende terminos de `IterationResult` previas
- [ ] T071 [P] [US3] Implementar `EmbeddingBasedDeduplicator` en `src/vigilancia_multiagente/application/evaluation/ws_b/embedding_dedup.py` que reusa `Reranker` (006) con umbral configurable (default 0.92)
- [ ] T072 [P] [US3] Implementar `PydanticExtractionSchemaRegistry` en `src/vigilancia_multiagente/application/evaluation/ws_b/pydantic_schema_registry.py`: define schemas pydantic por `(source_type, domain)` y expone `validate(raw, schema)`
- [ ] T073 [P] [US3] Implementar `LlmMultilingualNormalizer` en `src/vigilancia_multiagente/application/evaluation/ws_b/llm_multilingual.py` (`detect_language`, `translate`, `language_distribution` via LLM, una sola llamada por documento)
- [ ] T074 [P] [US3] Implementar `ConsensusDisputeMapper` en `src/vigilancia_multiagente/application/evaluation/ws_b/consensus_dispute_mapper.py` reusando `ContradictionAnalyzer` (006) extendido con embeddings y triangulacion

### Detector de autenticidad (clase concreta, sin Protocol — YAGNI)

- [ ] T075 [P] [US3] Implementar `LocalPerplexityAuthenticityDetector` en `src/vigilancia_multiagente/application/evaluation/authenticity/local_perplexity_detector.py` combinando perplejidad/burstiness (LLM log-prob) + heuristicas boilerplate. Output: `ContentAuthenticitySignal` con `ai_probability` y `effective_freshness`

### Step y wiring

- [ ] T076 [US3] Implementar `DataIntelligenceStep` en `src/vigilancia_multiagente/application/agents/pipeline/data_intelligence_step.py` que se inserta dentro de `ToolLoopStep` como sub-fase post-extraccion. Ejecuta: hybrid_search -> dedup -> schema validate -> authenticity -> multilingual -> consensus_dispute
- [ ] T077 [US3] En `dependencies.py` anadir factory `_build_data_intelligence_services` y inyectar en `ToolLoopStep` cuando `settings.eval_ws_b_enabled`
- [ ] T078 [US3] Modificar `src/vigilancia_multiagente/application/agents/pipeline/tool_loop_step.py` para invocar `DataIntelligenceStep.run(sub_context)` como sub-fase opcional cuando WS-B activo

### Migracion legacy WS-B

- [ ] T079 [US3] Modificar `src/vigilancia_multiagente/application/research/followup_strategist.py`: cuando `ContextualQueryExpander` esta inyectado, delegar `expand`; sino comportamiento actual (fallback)
- [ ] T080 [US3] Modificar `src/vigilancia_multiagente/application/research/ad_hoc_tools_service.py`: validar respuestas MCP con `ExtractionSchemaRegistry.validate()` cuando flag activo, eliminando `.get("results", [])` ad-hoc
- [ ] T081 [US3] Modificar `src/vigilancia_multiagente/api/routes/research_outputs.py`: reemplazar todos los `.get("results", [])` ad-hoc por DTOs ya validados desde `ad_hoc_tools_service`
- [ ] T082 [US3] Modificar `src/vigilancia_multiagente/application/evaluation/contradiction_analyzer.py`: `analyze()` delega en `ConsensusDisputeMapper` cuando inyectado; sino conserva solapamiento lexico como fallback. Quitar marca `# DEPRECATED` si la tenia
- [ ] T083 [US3] Modificar `src/vigilancia_multiagente/application/evaluation/source_scorer.py`: `score_source` lee `effective_freshness` (de `ContentAuthenticitySignal`) como peso multiplicativo cuando esta presente en el contexto

### Eliminacion controlada

- [ ] T084 [US3] Tras 3 semanas de WS-B verde en prod: verificar `grep -rn "\.get(\"results\", \[\])" src/` retorna 0 ocurrencias fuera de tests (SC-PLAN-09)

### Tests

- [ ] T085 [P] [US3] `tests/application/evaluation/ws_b/test_hybrid_search.py`: corpus sintetico; recall@10 hibrido > keyword-only >= 20%
- [ ] T086 [P] [US3] `tests/application/evaluation/ws_b/test_dedup.py`: 5 fuentes sindicadas con redaccion distinta -> 1 grupo
- [ ] T087 [P] [US3] `tests/application/evaluation/ws_b/test_schema_registry.py`: respuesta MCP malformada -> `ValidationError`; valida 100% de respuestas
- [ ] T088 [P] [US3] `tests/application/evaluation/ws_b/test_multilingual.py`: distribucion correcta de 3 idiomas, traduccion deterministica con mock
- [ ] T089 [P] [US3] `tests/application/evaluation/ws_b/test_authenticity_detector.py`: muestra humana vs muestra LLM, precision >= 0.7
- [ ] T090 [P] [US3] `tests/application/evaluation/ws_b/test_consensus_dispute.py`: 3 afirmaciones contradictorias -> 3 mapas
- [ ] T091 [P] [US3] `scripts/benchmark_recall.py`: compara recall@10 con flag off vs on; salida JSON con SC-B01
- [ ] T092 [P] [US3] `tests/golden/test_data_intelligence_golden.py`: golden `dedup-syndicated` con 8 fuentes sindicadas

---

## Phase 6: US4 — WS-C Deep Analysis

Goal: Curvas-S, meta-analisis, asunciones implicitas, dependencias criticas, contrafactual. Habilitable con `VT_EVAL_WS_C_ENABLED=true`.
Independent Test Criteria: SCs C01..C05 verificables; `DeepAnalysisStep` post-`AssembleBranchResultStep` produce `SCurveProjection`, `MetaAnalysisResult`, `CounterfactualScenario[]`, `ImplicitAssumption[]` por finding.

### Clases concretas (sin Protocol — YAGNI)

- [ ] T093 [P] [US4] Implementar `ScipyLogisticForecaster` en `src/vigilancia_multiagente/application/evaluation/analytics/scipy_logistic_forecaster.py` con `fit_s_curve(technology, domain, timeseries)` (usa `scipy.optimize.curve_fit`) y `detect_inflection(projection)`
- [ ] T094 [P] [US4] Implementar `DerSimonianLairdMetaAnalyzer` en `src/vigilancia_multiagente/application/evaluation/analytics/dersimonian_laird_meta.py` con `aggregate(topic, numeric_studies)` (numpy puro): extrae effect_size_range, consensus_value, i_squared, q_test_pvalue, outliers

### Adapters LLM

- [ ] T095 [P] [US4] Implementar `LlmAssumptionDetector` en `src/vigilancia_multiagente/application/evaluation/ws_c/llm_assumption_detector.py` usando `prompts/evaluation/assumption_detection.txt`; fallo -> `StepError(severity=warning)` y lista vacia
- [ ] T096 [P] [US4] Implementar `LlmCriticalDependencyMapper` en `src/vigilancia_multiagente/application/evaluation/ws_c/llm_critical_dependency_mapper.py` combinando `KnowledgeGraphService` (006) con prompts dirigidos
- [ ] T097 [P] [US4] Implementar `LlmCounterfactualSynthesizer` en `src/vigilancia_multiagente/application/evaluation/ws_c/llm_counterfactual_synthesizer.py` usando `prompts/evaluation/counterfactual.txt` con `scenarios_n` configurable (default 3)

### Step y wiring

- [ ] T098 [US4] Implementar `DeepAnalysisStep` en `src/vigilancia_multiagente/application/agents/pipeline/deep_analysis_step.py` que se inserta despues de `AssembleBranchResultStep`. Anota cada `Finding` con `implicit_assumptions`, `critical_dependencies`. Anade al contexto: `SCurveProjection`, `MetaAnalysisResult`, `CounterfactualScenario[]`
- [ ] T099 [US4] En `dependencies.py` anadir factory `_build_deep_analysis_services` y concatenar `DeepAnalysisStep` en pipeline cuando `settings.eval_ws_c_enabled`
- [ ] T100 [US4] En `src/vigilancia_multiagente/application/agents/base.py:_build_pipeline()` concatenar `DeepAnalysisStep` post-`AssembleBranchResultStep` cuando inyectado

### Migracion legacy WS-C

- [ ] T101 [US4] Modificar `src/vigilancia_multiagente/application/evaluation/hype_detector.py:_infer_maturity()`: cuando `SCurveProjection` esta presente en contexto, derivar TRL de `growth_rate` e `inflection_year`; sino fallback a reglas if/else actuales
- [ ] T102 [US4] Modificar `src/vigilancia_multiagente/application/evaluation/obsolescence_detector.py`: cuando `SCurveProjection` presente con `growth_rate < 0`, reportar obsolescencia con base en cola descendente; sino fallback heuristico
- [ ] T103 [US4] Modificar `src/vigilancia_multiagente/api/routes/research_outputs.py:GET /research/{id}/maturity` para devolver `SCurveProjection` + calibracion cuando WS-C activo (preserva DTO de respuesta via adapter)

### Eliminacion controlada

- [ ] T104 [US4] Tras 3 semanas WS-C verde en prod: verificar `grep -rn "from .*evaluation.hype_detector import" src/ | grep -v api/routes/research_outputs.py` vacio (SC verifiable). Eliminar `_infer_maturity` fallback de `hype_detector.py`

### Tests

- [ ] T105 [P] [US4] `tests/application/evaluation/ws_c/test_scipy_logistic_forecaster.py`: 3 dominios con series sinteticas, R^2 >= 0.8
- [ ] T106 [P] [US4] `tests/application/evaluation/ws_c/test_dersimonian_laird.py`: 5 estudios sinteticos, valida i_squared y consensus_value
- [ ] T107 [P] [US4] `tests/application/evaluation/ws_c/test_assumption_detector.py`: 4 textos con asunciones explicitas vs implicitas
- [ ] T108 [P] [US4] `tests/application/evaluation/ws_c/test_counterfactual_synthesizer.py`: genera >= 3 escenarios
- [ ] T109 [P] [US4] `tests/application/evaluation/ws_c/test_critical_dependency.py`: 3 tecnologias con dependencias conocidas
- [ ] T110 [P] [US4] `tests/application/evaluation/ws_c/test_deep_analysis_step.py`: integracion del step completo
- [ ] T111 [P] [US4] `tests/golden/test_deep_analysis_golden.py`: golden `alphafold-baseline` valida curva-S y meta-analisis

---

## Phase 7: US5 — WS-D Strategic Signals

Goal: Convergencia, colaboracion, linaje, narrativa, movilidad, brechas. Habilitable con `VT_EVAL_WS_D_ENABLED=true`.
Independent Test Criteria: SCs D01..D06 verificables; `StrategicSignalsStep` post-DeepAnalysis produce los 6 entities de WS-D.

### Clases concretas (sin Protocol — YAGNI)

- [ ] T112 [P] [US5] Anadir deps `vaderSentiment`, `scikit-learn` (si no estan) en `pyproject.toml`
- [ ] T113 [P] [US5] Implementar `SklearnAgglomerativeConvergenceDetector` en `src/vigilancia_multiagente/application/evaluation/analytics/agglomerative_convergence.py` (clustering jerarquico + ventana temporal deslizante)
- [ ] T114 [P] [US5] Implementar `VaderNarrativeShiftDetector` en `src/vigilancia_multiagente/application/evaluation/analytics/vader_narrative_shift.py` (VADER + ventanas deslizantes 90 dias + change-point con z-score)

### Adapters (Protocols cruzando frontera)

- [ ] T115 [P] [US5] Implementar `OpenAlexIdeaLineageTracer` en `src/vigilancia_multiagente/infra/openalex/openalex_idea_lineage.py` que navega `referenced_works` hasta hojas y detecta circularidad via set membership
- [ ] T116 [P] [US5] Implementar `CollaborationNetworkBuilderImpl` en `src/vigilancia_multiagente/application/evaluation/ws_d/collaboration_network_builder.py` extendiendo `GraphBuilder` (006) con nodos `Author`/`Inventor` y edges `co_author`/`co_inventor`; incluye `detect_bubbles(max_bubble_size=8)`
- [ ] T117 [P] [US5] Implementar `TalentMobilityAnalyzerImpl` en `src/vigilancia_multiagente/application/evaluation/ws_d/talent_mobility_analyzer.py` cruzando historial OpenAlex con USPTO/Google Patents (via Serper 006)
- [ ] T118 [P] [US5] Implementar `PatentingGapAnalyzerImpl` en `src/vigilancia_multiagente/application/evaluation/ws_d/patenting_gap_analyzer.py` que consulta OpenAlex (papers) y Serper Patents y divide densidades por subdominio

### Step y wiring

- [ ] T119 [US5] Implementar `StrategicSignalsStep` en `src/vigilancia_multiagente/application/agents/pipeline/strategic_signals_step.py` que se inserta despues de `DeepAnalysisStep`. Produce los 6 entities WS-D y los anade a `BranchResult.intelligence_sections`
- [ ] T120 [US5] En `dependencies.py` anadir factory `_build_strategic_signals_services` y concatenar `StrategicSignalsStep` en pipeline cuando `settings.eval_ws_d_enabled`
- [ ] T121 [US5] En `src/vigilancia_multiagente/application/agents/base.py:_build_pipeline()` concatenar `StrategicSignalsStep` post-`DeepAnalysisStep` cuando inyectado

### Migracion legacy WS-D

- [ ] T122 [US5] Modificar `src/vigilancia_multiagente/application/evaluation/weak_signal_detector.py`: heuristica por frecuencia degradada a sub-senal cuando `ConvergenceCluster[]` presente en contexto; el resultado primario lo dan los nuevos detectores
- [ ] T123 [US5] Modificar `src/vigilancia_multiagente/application/evaluation/obsolescence_detector.py`: anadir senal de `NarrativeShift` con sentimiento negativo creciente (extra a la senal de SCurve de T102)
- [ ] T124 [US5] Modificar `src/vigilancia_multiagente/api/routes/research_outputs.py:GET /research/{id}/obsolescence` para incluir `NarrativeShift` cuando WS-D activo

### Tests

- [ ] T125 [P] [US5] `tests/application/evaluation/ws_d/test_convergence_detector.py`: corpus AI+bio con embeddings temporales -> 1 cluster
- [ ] T126 [P] [US5] `tests/application/evaluation/ws_d/test_collaboration_network.py`: 30 papers con co-autorias -> red de 10+ nodos, detecta 1 burbuja
- [ ] T127 [P] [US5] `tests/application/evaluation/ws_d/test_idea_lineage.py`: cadena de citas con circularidad
- [ ] T128 [P] [US5] `tests/application/evaluation/ws_d/test_narrative_shift.py`: serie temporal 12 meses con shift de tono
- [ ] T129 [P] [US5] `tests/application/evaluation/ws_d/test_talent_mobility.py`: 5 autores con transiciones academia->industria
- [ ] T130 [P] [US5] `tests/application/evaluation/ws_d/test_patenting_gap.py`: subdominio con pub/patent ratio 5:1 -> `blue_ocean`
- [ ] T131 [P] [US5] `tests/golden/test_strategic_signals_golden.py`: golden `convergence-ai-bio` valida deteccion temprana >= 6 meses

---

## Phase 8: Polish & Cross-Cutting

Goal: Observabilidad, runbook, verificacion arquitectonica final.
Independent Test Criteria: SC-PLAN-01..09 todos verificables; latencia P95 <= 1.5x baseline; rollback funcional.

- [ ] T132 [P] Anadir metricas Prometheus por step (`evaluation_step_duration_seconds`, `evaluation_step_errors_total`) en `src/vigilancia_multiagente/application/observability/metrics_service.py`
- [ ] T133 [P] Crear `scripts/benchmark_latency.py` que mide P95 latencia con todos los flags `false` vs `true` (SC-PLAN-06)
- [ ] T134 [P] Documentar runbook de rollback en `docs/runbook-eval-rollback.md`: como deshabilitar cada WS, criterios de canary, plan de recuperacion
- [ ] T135 [P] Actualizar `docs/api-endpoints-reference.md` documentando: 409 por bias critical (US1), cambios en `/maturity` (US4), cambios en `/obsolescence` (US5)
- [ ] T136 [P] Anadir tests SC-PLAN: `tests/test_constitution_compliance.py` con asserts sobre los SC-PLAN-01..09 (greps + invariantes)
- [ ] T137 Ejecutar `scripts/check-layer-imports.py` y validar 0 violaciones tras todos los nuevos modulos (SC-PLAN-01)
- [ ] T138 Ejecutar `python -m basedpyright src/vigilancia_multiagente/` y validar 0 errores (SC-PLAN-02)
- [ ] T139 Ejecutar `pytest` con todos los flags `false` y validar pasada completa sin regresiones (SC-PLAN-03)
- [ ] T140 Ejecutar `pytest` con todos los flags `true` y validar pasada completa + golden suite (SC-PLAN-04)
- [ ] T141 Eliminacion final post-rollout (3 semanas verde por WS): borrar `confidence_calibrator.py` (SC-PLAN-07), reescribir definitivamente `branch_kpi_service.py`/`golden_cases_runner.py`/`prompt_regression_service.py` sin marcas DEPRECATED (SC-PLAN-08), eliminar parseo manual `.get("results", [])` (SC-PLAN-09)

---

## Dependencies

### Inter-phase

- **Phase 1 (Setup)** -> **Phase 2 (Foundational)** -> **Phase 3 (US1/WS-E)**.
- **Phase 3 (US1/WS-E)** debe completarse antes de cualquier otra story porque la golden suite es la spec ejecutable de los demas WS.
- **Phase 4-7 (US2-US5)** pueden ejecutarse en paralelo entre si una vez completada Phase 3, **excepto** las tareas de wiring en `dependencies.py` y `base.py` que deben serializarse manualmente (T029/T057/T077/T099/T120 tocan el mismo archivo).
- **Phase 8 (Polish)** depende de todas las anteriores.

### Inter-task (criticas)

- T001 antes de T029, T057, T077, T099, T120 (todos leen `settings.eval_ws_*_enabled`).
- T005 + T017 + T018 antes de cualquier step (los steps escriben `StepError`).
- T009 + T011..T015 + T016 antes de los adapters (los adapters tipan contra Protocols).
- T019 + T020 antes de T021 (runner usa repositorios).
- T021 + T022..T026 antes de T027 (gate orquesta los servicios).
- T027 + T028 antes de T030 (synthesizer invoca gate).
- T038 + T039 + T040 al final de Phase 3 (verifican el flujo completo de US1).
- Por cada Phase US: el step (T056/T076/T098/T119) depende de los adapters de su WS y debe completarse antes del wiring (T057/T077/T099/T120).
- T035, T037, T084, T104, T141 son tareas de **eliminacion controlada**: requieren 3 semanas de flag activo en prod antes de ejecutarse.

---

## Parallel Execution Examples

### Phase 1 Setup Parallel Block

- Run T002, T003, T004, T006, T007, T008 en paralelo (archivos diferentes).
- T001 secuencial primero (define settings que otros leen).
- T005 depende de la estructura de carpetas (T007).

### Phase 2 Foundational Parallel Block

- Run T009, T011, T012, T013, T014, T015 en paralelo (archivos diferentes).
- T010 + T016 + T017 + T018 secuenciales al final (consolidan exports).

### Phase 3 US1 Parallel Blocks

- **Repositorios + clases concretas**: T019, T020, T022, T023, T024 en paralelo.
- **Adapters LLM**: T025, T026 en paralelo.
- **T021 (runner)** depende de T019, T020.
- **T027 (gate)** depende de T021, T022, T023, T024, T025, T026.
- **Tests T041..T046** en paralelo, despues de sus servicios respectivos.
- **Scripts T038, T039, T040** en paralelo al final.

### Phase 4 US2 Parallel Blocks

- **Repositorios + adapters externos**: T047, T048, T050, T051, T052, T053, T054, T055 en paralelo.
- **T049** (seed) puede correr en paralelo pero requiere T048.
- **T056 (step)** depende de todos los adapters (T050..T055).
- **Tests T061..T066** en paralelo, despues de sus servicios.

### Phase 5 US3 Parallel Blocks

- **Adapters**: T067, T068, T069, T070, T071, T072, T073, T074, T075 en paralelo.
- **T076 (step)** depende de todos los adapters.
- **Migracion legacy T079..T083** en paralelo (archivos diferentes).
- **Tests T085..T092** en paralelo.

### Phase 6 US4 Parallel Blocks

- **Clases + adapters**: T093, T094, T095, T096, T097 en paralelo.
- **T098 (step)** depende de las 5 anteriores.
- **Migracion T101..T103** en paralelo (archivos diferentes).
- **Tests T105..T111** en paralelo.

### Phase 7 US5 Parallel Blocks

- **Clases + adapters**: T112, T113, T114, T115, T116, T117, T118 en paralelo (T112 primero si las libs no estan instaladas).
- **T119 (step)** depende de los anteriores.
- **Migracion T122..T124** en paralelo.
- **Tests T125..T131** en paralelo.

### Phase 8 Parallel Block

- T132, T133, T134, T135, T136 en paralelo.
- T137, T138, T139, T140 secuenciales (cada uno verifica el estado final).
- T141 al final, tras 3 semanas de verde en prod.

---

## Implementation Strategy

1. **MVP minimo = Phase 1 + Phase 2 + Phase 3 (US1/WS-E)**. Con esto:
   - El sistema tiene golden cases ejecutables como spec.
   - El `ReportQualityGate` esta en su lugar (con flag opt-in).
   - El `confidence_calibrator.py` queda reemplazado por la curva isotonica (post-rollout).
   - `buzz = max(0, substance // 2)` desaparece.
   - Resto del sistema NO cambia (todas las flags `false` por default — preserva comportamiento actual del vigilador).

2. **Despues de US1**, las stories US2-US5 pueden asignarse a equipos distintos en paralelo:
   - **US2 (WS-A)** = mayor impacto en confianza (reputacion de autor).
   - **US3 (WS-B)** = mayor impacto en recall/calidad de fuentes.
   - **US4 (WS-C)** = mayor impacto en analisis (curvas-S, meta-analisis).
   - **US5 (WS-D)** = mayor impacto en insights estrategicos.
   - Los wiring en `dependencies.py`/`base.py` (T057/T077/T099/T120) se serializan por archivo compartido.

3. **Activacion en produccion**: orden recomendado segun plan: WS-E -> WS-A -> WS-B -> WS-C -> WS-D, una flag a la vez, observando metricas de T132 antes de habilitar la siguiente.

4. **Eliminacion controlada**: las tareas T035, T037, T084, T104, T141 NO se ejecutan automaticamente al final de su phase — requieren que el flag de su WS haya estado `true` en prod durante 21 dias consecutivos con 0 regresiones en la golden suite (criterio del Rollout Strategy).

5. **Cero cambio funcional por default**: gracias a las flags con default `false` y los adapters degradables (defaults `None` en claves externas), el sistema arranca byte-por-byte igual que antes del 007. Cada WS se opt-in explicitamente.

6. **Constitution gates**:
   - SC-PLAN-01..06 (gates tecnicos) en T137-T140.
   - SC-PLAN-07..09 (gates de deprecation) en T141.
   - Constitution Check del plan: PASS pre-design y post-design.
