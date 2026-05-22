# Adapters de evaluación externa

> Este documento complementa a `tools-by-agent.md` y cubre los adapters,
> comprobadores y gateways del pipeline de evaluación (Workstreams A..E)
> que realizan llamadas a servicios externos (APIs, SPARQL, CSV remotos).
> Los módulos puramente internos (cómputo local, LLM vía MiniMax) no se
> listan aquí; para esos consultá `specs/007-evaluacion-inteligente/`.

## Clasificación de transporte

| Categoría | Significado |
|-----------|-------------|
| **HTTP** | Llamada directa a API remota con httpx (con o sin API key). |
| **SPARQL público** | Endpoint SPARQL sin autenticación (Wikidata). |
| **CSV remoto** | Descarga y parseo de CSV público (Retraction Watch). |
| **GitHub API** | Verificación de repositorios vía GitHub REST/raw. |
| **OpenAlex** | Llamadas al gateway interno de OpenAlex que a su vez consulta la API pública de OpenAlex. |

---

## Workstream A — Source Quality (Calidad de Fuentes)

Servicios que validan fuentes desde múltiples ángulos: fact-checking, retractaciones,
conflictos, reproducibilidad.

| Adapter | Archivo | Transporte | ¿Requiere key? | Degrada si falta |
|---------|---------|------------|-----------------|------------------|
| **GoogleFactCheckAdapter** | `infra/factcheck/google_factcheck.py` | HTTP (Google Fact Check Tools API v1alpha1) | `VT_GOOGLE_FACTCHECK_API_KEY` | Sí → `status=not_found` |
| **WikidataFactCheckAdapter** | `infra/factcheck/wikidata_factcheck.py` | SPARQL público (query.wikidata.org) | No | No aplica |
| **RetractionWatchCSVAdapter** | `infra/retraction/retraction_watch_csv.py` | CSV remoto (Retraction Watch database dump) | `VT_RETRACTION_WATCH_CSV_URL` | Sí → sync salteado, cache vacío |
| **GitHubReproducibilityChecker** | `application/evaluation/ws_a/github_reproducibility_checker.py` | GitHub API + raw.githubusercontent.com | No (repos públicos) | Si el paper no declara repo → `reproducibility=NOT_AVAILABLE` |
| **LLMConflictAnalyzer** | `application/evaluation/ws_a/llm_conflict_analyzer.py` | LLM local (MiniMax) | `VT_MINIMAX_API_KEY` (compartida) | Error del pipeline si MiniMax no está configurado |
| **OpenAlexAuthorGateway** | `application/evaluation/ws_a/` (implícito vía `search_authors`) | OpenAlex MCP → OpenAlex REST API pública | `VT_OPENALEX_EMAIL` (polite pool) | Degrada a pool anónimo (rate limits más bajos) |

---

## Workstream B — Data Intelligence (Inteligencia de Datos)

Módulos que enriquecen, deduplican y detectan contenido sintético.

| Módulo | Archivo | Tipo | Dependencia externa |
|--------|---------|------|---------------------|
| **LocalPerplexityDetector** | `application/evaluation/authenticity/local_perplexity_detector.py` | Cómputo local (perplexity estadística) | Ninguna |
| **EmbeddingDedup** | `application/evaluation/ws_b/embedding_dedup.py` | Cómputo local (cosine similarity sobre embeddings Gemini) | `VT_EMBEDDING_API_KEY` |
| **ConsensusDisputeMapper** | `application/evaluation/ws_b/consensus_dispute_mapper.py` | Cómputo local (clustering de claims + NLP) | Ninguna |
| **LLMQueryExpander** | `application/evaluation/ws_b/llm_query_expander.py` | LLM local (MiniMax) | `VT_MINIMAX_API_KEY` |
| **LLMMultilingual** | `application/evaluation/ws_b/llm_multilingual.py` | LLM local (MiniMax, traducción) | `VT_MINIMAX_API_KEY` |
| **PydanticSchemaRegistry** | `application/evaluation/ws_b/pydantic_schema_registry.py` | Validación local con Pydantic | Ninguna |

---

## Workstream C — Deep Analysis (Análisis Profundo)

Proyecciones, detección de asunciones y mapeo de dependencias.

| Módulo | Archivo | Tipo | Dependencia externa |
|--------|---------|------|---------------------|
| **LLMAssumptionDetector** | `application/evaluation/ws_c/llm_assumption_detector.py` | LLM local (MiniMax) | `VT_MINIMAX_API_KEY` |
| **LLMCounterfactualSynthesizer** | `application/evaluation/ws_c/llm_counterfactual_synthesizer.py` | LLM local (MiniMax) | `VT_MINIMAX_API_KEY` |
| **LLMCriticalDependencyMapper** | `application/evaluation/ws_c/llm_critical_dependency_mapper.py` | LLM local (MiniMax) | `VT_MINIMAX_API_KEY` |
| **ScipyLogisticForecaster** | `application/evaluation/analytics/scipy_logistic_forecaster.py` | Cómputo local (scipy curve_fit) | Ninguna |
| **DerSimonianLairdMeta** | `application/evaluation/analytics/dersimonian_laird_meta.py` | Cómputo local (meta-análisis random-effects) | Ninguna |

---

## Workstream D — Strategic Signals (Señales Estratégicas)

Patentes, movilidad de talento, redes de colaboración y convergencia.

| Módulo | Archivo | Tipo | Dependencia externa |
|--------|---------|------|---------------------|
| **PatentingGapAnalyzer** | `application/evaluation/ws_d/patenting_gap_analyzer.py` | Cómputo local (análisis de gaps sobre datos de patentes ya recolectados) | Ninguna (consume datos de OpenAlex/Serper ya obtenidos por el agente) |
| **TalentMobilityAnalyzer** | `application/evaluation/ws_d/talent_mobility_analyzer.py` | Cómputo local (grafos de afiliación) | Ninguna |
| **CollaborationNetworkBuilder** | `application/evaluation/ws_d/collaboration_network_builder.py` | Cómputo local (networkx) | Ninguna (consume datos de OpenAlex) |
| **AgglomerativeConvergence** | `application/evaluation/analytics/agglomerative_convergence.py` | Cómputo local (scipy linkage) | Ninguna |
| **VaderNarrativeShift** | `application/evaluation/analytics/vader_narrative_shift.py` | Cómputo local (VADER sentiment) | Ninguna |

---

## Workstream E — Output Assurance (Aseguramiento de Salida)

Auditoría de sesgos, simulación de stakeholders, calibración y control de calidad.

| Módulo | Archivo | Tipo | Dependencia externa |
|--------|---------|------|---------------------|
| **LLMFalsificationProber** | `application/evaluation/ws_e/llm_falsification_prober.py` | LLM local (MiniMax) | `VT_MINIMAX_API_KEY` |
| **LLMStakeholderSimulator** | `application/evaluation/ws_e/llm_stakeholder_simulator.py` | LLM local (MiniMax) | `VT_MINIMAX_API_KEY` |
| **BiasAuditor** | `application/evaluation/audit/bias_auditor.py` | Cómputo local (estadístico) | Ninguna |
| **IsotonicCalibrator** | `application/evaluation/calibration/isotonic_calibrator.py` | Cómputo local (sklearn isotonic regression) | Ninguna |
| **JsonbTraceWriter** | `application/evaluation/forensic/jsonb_trace_writer.py` | Persistencia local (PostgreSQL jsonb) | `VT_DATABASE_URL` |
| **GoldenCasesRunner** | `application/evaluation/golden_cases_runner.py` | LLM local (MiniMax, batch testing) | `VT_MINIMAX_API_KEY` |
| **ReportQualityGate** | `application/evaluation/report_quality_gate.py` | Cómputo local (validación estructural) | Ninguna |

---

## Resumen de cobertura

Total de adapters con dependencia externa: **6** (más 2 gateways indirectos).

| Adapter | Variable(s) de entorno | Obligatorio |
|---------|------------------------|-------------|
| GoogleFactCheckAdapter | `VT_GOOGLE_FACTCHECK_API_KEY` | No |
| WikidataFactCheckAdapter | — | No aplica |
| RetractionWatchCSVAdapter | `VT_RETRACTION_WATCH_CSV_URL` | No |
| GitHubReproducibilityChecker | — | No |
| EmbeddingDedup | `VT_EMBEDDING_API_KEY` | Sí (Gemini embeddings) |
| JsonbTraceWriter | `VT_DATABASE_URL` | Sí (PostgreSQL) |

Todos los módulos que usan LLM dependen de `VT_MINIMAX_API_KEY` (7 módulos entre WS-A, WS-B, WS-C, WS-E).
Si MiniMax no está configurado, el pipeline de evaluación falla en esos pasos específicos
pero el resto de workstreams continúa (degradación graceful por workstream).
