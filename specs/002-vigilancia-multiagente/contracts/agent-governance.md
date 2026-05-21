# Agent Governance Contract

> **Global rules (tool usage, safety, error handling, output style, model behavior, embeddings) are defined in `system-base.md` (v1.0.0).** This contract contains only branch-specific MCP tool configuration and per-agent prompt contracts.

---

## 1) Matriz agente→skill MCP

| Rama | Tools MCP permitidas (orden de uso) | Timeout por tool | Retry por tool | Sustitucion automatica |
|---|---|---|---|---|
| Avances y Tendencias | `tavily-search` -> `exa-search` -> `jina-read_url` | 20s / 25s / 30s | 2 / 2 / 1 | none |
| Comercial | `exa-company-search` -> `serper-news` -> `tavily-extract` | 25s / 20s / 25s | 2 / 2 / 1 | none |
| Riesgo | `brave-web-search` -> `firecrawl-scrape` -> `jina-guess_datetime_url` | 20s / 35s / 15s | 2 / 1 / 1 | none |
| PI y Normativa | `google-scholar-search` -> `arxiv-search` -> `serper-patents` -> `jina-read_url` | 25s / 25s / 25s / 30s | 2 / 2 / 2 / 1 | none |
| Competitivo | `exa-company-search` -> `serper-news` -> `brave-news-search` | 25s / 20s / 20s | 2 / 2 / 2 | none |
| Oportunidades | `tavily-search` -> `exa-search` -> `brave-web-search` | 20s / 25s / 20s | 2 / 2 / 2 | none |

## 2) Prompt contracts por agente (Branch Overlays)

Cada rama define su propio overlay con instrucciones específicas de dominio.
Estos overlays se componen con `system-base.md` en runtime.

### Avances y Tendencias

- **Objective**: Identificar señales de avances tecnológicos y tendencias emergentes en el dominio de la consulta.
- **Required context**: `user_query`, `temporal_window`, `prior_findings`
- **Output schema**: `{"findings": "array", "sources": "array", "confidence": "float", "needs_follow_up": "bool", "next_query": "string"}`
- **Quality criteria**: evidencia verificable por hallazgo, cobertura por subtema, sin duplicados
- **Do**: citar fuentes con URL, declarar incertidumbre
- **Don't**: inventar datos, inferir causalidad sin soporte
- **Uncertainty handling**: confidence < 0.6 → next_query concreto (≤20 palabras)

### Comercial

- **Objective**: Identificar dinámicas comerciales, movimientos de mercado y posicionamiento de actores relevantes.
- **Required context**: `user_query`, `temporal_window`, `prior_findings`
- **Output schema**: `{"findings": "array", "sources": "array", "confidence": "float", "needs_follow_up": "bool", "next_query": "string"}`
- **Quality criteria**: evidencia de fuente corporativa, cobertura geográfica, sin duplicados
- **Do**: priorizar fuentes oficiales o de prensa especializada, declarar incertidumbre
- **Don't**: inventar métricas financieras, inferir participación de mercado sin datos
- **Uncertainty handling**: confidence < 0.6 → next_query concreto (≤20 palabras)

### Riesgo

- **Objective**: Detectar señales de riesgo tecnológico, regulatorio o de mercado que puedan afectar el dominio.
- **Required context**: `user_query`, `temporal_window`, `prior_findings`
- **Output schema**: `{"findings": "array", "sources": "array", "confidence": "float", "needs_follow_up": "bool", "next_query": "string"}`
- **Quality criteria**: fuente autoritativa, actualidad del dato, nivel de riesgo explícito
- **Do**: etiquetar nivel de riesgo (bajo/medio/alto), citar fuente
- **Don't**: especular sin evidencia, mezclar riesgo operativo con estratégico sin distinción
- **Uncertainty handling**: confidence < 0.6 → next_query concreto (≤20 palabras)

### PI y Normativa

- **Objective**: Identificar cambios normativos, patentes relevantes y obligaciones legales en el dominio.
- **Required context**: `user_query`, `temporal_window`, `prior_findings`
- **Output schema**: `{"findings": "array", "sources": "array", "confidence": "float", "needs_follow_up": "bool", "next_query": "string"}`
- **Quality criteria**: referencia a documento oficial/legal, jurisdicción clara, fecha de vigencia
- **Do**: identificar jurisdicción aplicable, citar número de patente/norma
- **Don't**: interpretar textos legales sin disclaimer, inferir aplicabilidad sin verificar jurisdicción
- **Uncertainty handling**: confidence < 0.6 → next_query concreto (≤20 palabras)

### Competitivo

- **Objective**: Analizar el panorama competitivo, posicionamiento de competidores y ventajas diferenciales.
- **Required context**: `user_query`, `temporal_window`, `prior_findings`
- **Output schema**: `{"findings": "array", "sources": "array", "confidence": "float", "needs_follow_up": "bool", "next_query": "string"}`
- **Quality criteria**: competidor identificado nominalmente, fuente verificable, diferenciación clara
- **Do**: nombrar competidores específicos, citar fuente de inteligencia competitiva
- **Don't**: hacer juicios de valor sin respaldo, mezclar rumours con hechos confirmados
- **Uncertainty handling**: confidence < 0.6 → next_query concreto (≤20 palabras)

### Oportunidades

- **Objective**: Identificar oportunidades de innovación, colaboración o nuevos mercados en el dominio.
- **Required context**: `user_query`, `temporal_window`, `prior_findings`
- **Output schema**: `{"findings": "array", "sources": "array", "confidence": "float", "needs_follow_up": "bool", "next_query": "string"}`
- **Quality criteria**: oportunidad concreta, actor identificable, ventana de tiempo
- **Do**: cuantificar impacto potencial cuando sea posible, citar fuente
- **Don't**: prometer retornos sin datos, confundir oportunidad con riesgo
- **Uncertainty handling**: confidence < 0.6 → next_query concreto (≤20 palabras)

## 3) Contrato de artefactos y rutas

> Este contrato es global y pertenece al system base. Se mantiene aquí por cercanía al equipo de desarrollo.

Raiz por sesion:

`sessions/{session_id}/`

Subestructura:

- `sessions/{session_id}/prompts/{branch}/{version}.json`
- `sessions/{session_id}/iterations/{branch}/iter-{n}.json`
- `sessions/{session_id}/raw/{branch}/iter-{n}.json`
- `sessions/{session_id}/findings/{branch}.json`
- `sessions/{session_id}/semantic/relations.json`
- `sessions/{session_id}/report/final-report.md`
- `sessions/{session_id}/graph/graph.json`
- `sessions/{session_id}/metrics/branch-kpis.json`
- `sessions/{session_id}/traces/{branch}/trace-{timestamp}.jsonl`

Reglas:

- Naming estable: `iter-{n}`, `v{major.minor.patch}`, `trace-{iso8601}`.
- Retencion:
  - `raw/` 30 dias,
  - `traces/` 60 dias,
  - `findings/`, `report/`, `graph/`, `metrics/` 180 dias.
- Ownership:
  - cada agente escribe solo en su carpeta de rama,
  - el orquestador consolida `semantic/`, `report/`, `graph/`, `metrics/`.

## 4) Capa de evaluacion operativa

KPIs obligatorios por rama:

- `coverage_kpi` (0..1): cobertura de subtemas planificados.
- `precision_kpi` (0..1): proporcion de hallazgos validados por fuente fuerte.
- `latency_ms_kpi`: tiempo total de ejecucion de la rama.
- `cost_kpi`: costo estimado de tokens + llamadas MCP.

Calidad de prompts:

- Regression suite por rama (minimo 10 casos por contrato).
- Gate de aprobacion: no bajar >5% en `coverage_kpi` o `precision_kpi`.

Golden cases:

- Conjunto fijo de casos representativos (minimo 12 casos, 2 por rama).
- Evaluacion en cada cambio de prompt/modelo/tool schema.
