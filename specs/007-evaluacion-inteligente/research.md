# Research: Sistema de Evaluacion Inteligente (Spec 007)

Resolucion de incertidumbres tecnicas previas al diseno. Cada decision lista
las alternativas evaluadas y la razon por la que se eligio la opcion final.

---

## Datos externos por workstream

### WS-A — Reputacion de autores, retractaciones, fact-checking

- **Decision**: Reusar `OpenAlexScholarlyWorksGateway` (creado en spec 006)
  para reputacion. Anadir adapter Crossref (retracciones) y `RetractionWatch`
  via su API publica.
- **Rationale**: OpenAlex ya esta integrado, sin clave, devuelve h-index
  proxy (citas y total works). Crossref expone la flag `is-referenced-by-count`
  y Retraction Watch publica un CSV publico diario que basta para un cron
  job de invalidacion. Fact-checking se cubre con la API de Google FactCheck
  Tools (gratuita con clave OAuth).
- **Alternativas**:
  - Scopus / Web of Science: requieren licencia institucional cara — descartado.
  - Construir base propia: violacion de YAGNI y mantenimiento perpetuo —
    descartado.

### WS-B — Busqueda hibrida, deduplicacion semantica, esquemas JSON

- **Decision**: La busqueda hibrida usa el `EmbeddingGateway` (006) + BM25
  via `rank_bm25` (libreria pura python, sin dependencias C). La deduplicacion
  reusa `SemanticReranker` con umbral `>= 0.92`. Los esquemas JSON se
  definen con `pydantic v2` (ya en el proyecto) y se aplican en el momento
  del extractor MCP.
- **Rationale**: Evita servicios externos para algo que es matematica local.
  `rank_bm25` cabe en ~200 LOC, no agrega ruido. Pydantic ya es transitiva
  por FastAPI.
- **Alternativas**:
  - Elasticsearch para BM25: sobre-ingenieria — descartado.
  - JSON Schema crudo (`jsonschema`): pierde generacion de tipos — descartado.

### WS-B — Deteccion de contenido IA y refinamiento de frescura

- **Decision**: Combinar tres senales locales para clasificar el grado
  de autenticidad y frescura de cada fuente:
  1. **Perplejidad y burstiness** del texto (proxy ligero de
     contenido generado por LLM) — calculadas con `LLMClient` (006)
     en modo log-prob solicitando perplejidad sobre fragmentos.
  2. **Heuristicas estructurales** (frases boilerplate frecuentes en
     salida de LLMs publicos, ausencia de errores ortograficos
     humanos, densidad de listados perfectamente paralelos).
  3. **Frescura ajustada por autenticidad**: `effective_freshness =
     raw_freshness * (1 - ai_probability * penalty_factor)`, donde
     `penalty_factor` es configurable por dominio (alto en noticias,
     bajo en blogs tecnicos).
- **Rationale**: Modelos dedicados de detección de IA (GPTZero, Turnitin)
  son cajas negras de pago con falsos positivos altos sobre texto
  cientifico legitimo. La combinacion local + frescura ajustada da
  precision suficiente para penalizar (no eliminar) sin dependencias
  externas. La señal se publica como un campo `ai_probability` en
  `[0, 1]` y feed-fowardea a `SourceScorer` como peso multiplicativo.
- **Alternativas**:
  - API externa GPTZero: costo + black-box + falsos positivos —
    descartado.
  - Modelo fine-tuneado local: violacion de YAGNI con corpus inicial
    chico — descartado.
  - Eliminacion dura de fuentes con `ai_probability > X`: viola POLA
    (perdida silenciosa de contenido potencialmente valido) —
    descartado.

### WS-C — Curvas-S, meta-analisis, asunciones implicitas

- **Decision**: `scipy.optimize.curve_fit` para ajuste logistico (curvas-S).
  Meta-analisis con `numpy` + formulas DerSimonian-Laird (I^2, Q-test).
  Asunciones implicitas se detectan con prompts LLM via `LLMClient` (006)
  reusando el `PromptLoader` con plantillas en `prompts/evaluation/`.
- **Rationale**: SciPy/NumPy ya son dependencias transitivas (via gensim/
  embeddings). LLM-based assumption detection es el unico camino tractable
  — los patrones lexicos no escalan a lenguaje natural.
- **Alternativas**:
  - Modelo dedicado fine-tuneado: violacion de YAGNI con corpus tan chico —
    descartado.
  - Regex sobre frases "asumiendo que": ya probado en heuristicas previas,
    falla en >70% de casos — descartado.

### WS-D — Convergencia, redes colaboracion, linaje, narrativa

- **Decision**: Reusar `KnowledgeGraphService` (006) extendido con
  `CollaborationNetworkBuilder` (subclase de `GraphBuilder`). Clustering
  con `sklearn.cluster.AgglomerativeClustering` sobre embeddings. Cambios
  de narrativa con `VADER` para sentimiento + ventanas deslizantes.
- **Rationale**: La infraestructura grafo del 006 ya analiza nodos PERSON/
  COMPANY; extenderla a co-autoria/co-invencion es zero-cost. sklearn ya
  esta como dep transitiva. VADER es ~10 KB y compatible con multiples
  idiomas via traduccion previa (WS-B FR-B05).
- **Alternativas**:
  - NetworkX con community detection (`python-louvain`): demasiado pesado
    para el caso de uso — descartado.
  - Modelo de sentimiento LLM: costo desproporcionado por consulta —
    descartado.

### WS-E — Golden cases, simulacion stakeholders, falsificacion, calibracion

- **Decision**: Los golden cases ya existen en `application/evaluation/
  golden_cases_runner.py` (006 marcado como `# DEPRECATED: migrar a spec 007`).
  La spec 007 lo reactiva creando `GoldenCaseRepository` (DB) y
  `GoldenCaseRunner` (orquesta ejecucion). Simulacion de stakeholders con
  agentes LLM dedicados (1 prompt por perfil). Calibracion con `sklearn.
  isotonic.IsotonicRegression` sobre historial de golden cases.
- **Rationale**: Reutilizar codigo deprecado en lugar de re-escribir.
  IsotonicRegression es el algoritmo estandar de calibracion (Platt scaling
  alternativo), no requiere muchas muestras (50-100 ya da curva utilizable).
- **Alternativas**:
  - Calibracion bayesiana: complejidad innecesaria sin volumen de datos —
    descartado.
  - Stakeholders como reglas hardcoded: pierde flexibilidad — descartado.

---

## Integracion con el pipeline del spec 006

- **Decision**: Cada workstream se materializa como `PipelineStep`
  adicional. WS-A y WS-B se insertan **antes** de `AssembleBranchResultStep`
  (afectan que findings sobreviven al ensamblado). WS-C y WS-D se insertan
  **despues** (analizan el conjunto final). WS-E corre fuera del pipeline
  como gate post-`ReportSynthesizer`.
- **Rationale**: Respeta el contrato de Pipeline (006 FR-014). Los steps
  son enumerables y testeables aislados, conforme Constitucion (Modularidad
  Primero, ISP).
- **Alternativas**:
  - Sub-pipeline embebido en `ToolLoopStep`: rompe SRP del step — descartado.
  - Servicio externo asincrono: agrega complejidad de I/O sin valor —
    descartado.

---

## Persistencia

- **Decision**: Tres tablas nuevas en PostgreSQL:
  - `author_reputation` (FR-A01): h-index, citas, retracciones, afiliacion.
  - `golden_case_run` (FR-E01): id_case, timestamp, success, confianza
    estimada, confianza real, delta.
  - `calibration_curve` (FR-E06): segmento, score_in, score_out, sample_n.
  Las tablas existentes (`source_trust` de 006) NO se duplican — se
  reutilizan via puertos.
- **Rationale**: Reusa `infra/persistence` y `Database` ya inyectado.
  Migration con `alembic` (ya configurado en el proyecto).
- **Alternativas**:
  - Almacenamiento JSON en disco: pierde transaccionalidad — descartado.
  - Reusar `source_trust` para autores: viola SRP (fuente != autor) —
    descartado.

---

## Coexistencia y migracion

- **Decision**: Cada componente nuevo se controla por feature flag en
  `config/settings.py` (`VT_EVAL_WS_A_ENABLED`, etc.). Cuando esta off,
  el sistema usa la heuristica antigua (que sigue presente). Activacion
  workstream-por-workstream, no big-bang.
- **Rationale**: Coexistencia es requisito del spec ("Out of Scope:
  Migracion de datos"). Permite rollback inmediato si una regresion
  aparece en produccion sin tocar codigo.
- **Alternativas**:
  - Replace-in-place: viola el constraint del spec — descartado.

---

## Resumen de dependencias nuevas (justificacion individual)

| Libreria | Workstream | Justificacion |
|----------|-----------|---------------|
| `rank_bm25` | WS-B | BM25 puro python, ~200 LOC, sin servicios externos. |
| `scipy` | WS-C | Ya transitiva (numpy ya esta); `curve_fit` para curvas-S. |
| `sklearn` | WS-D, WS-E | Ya transitiva; `AgglomerativeClustering`, `IsotonicRegression`. |
| `vaderSentiment` | WS-D | ~10 KB, sin estado, sentimiento offline. |
| `httpx` para Crossref/RetractionWatch | WS-A | Ya en proyecto. Reuso. |

Ninguna dependencia nueva es de >100 KB ni introduce subprocesos C
adicionales. Constitucion (Simplicidad Obligatoria) preservada.
