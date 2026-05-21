# Implementation Plan: Backend Intelligence v3

**Constraint principal**: Sin `VT_MINIMAX_API_KEY`. Todo feature con LLM debe tener fallback funcional. El código MiniMax se ejecuta solo si la key está presente.
**Quality**: Código Python optimizado, sin abstracciones innecesarias, cambios quirúrgicos. 50+ tests deben pasar siempre.

---

## Risk Analysis: Código que podría quedar huérfano

| Feature | Riesgo | Mitigación |
|---------|--------|-----------|
| FR-004 ObsolescenceDetector | 🔴 Sin endpoint ni caller | Se expone vía endpoint `POST /research/{id}/obsolescence` |
| FR-005 Branch Signaling | 🔴 `signal_branch()` nunca llamado | Se llama desde `BaseBranchAgent.run()` al detectar findings cross-branch |
| FR-006 MCP Cache | 🔴 Cache creado pero no conectado | Se integra en `MCPExecutionClient.execute_tool()` como wrapper transparente |
| FR-008 ParameterLearner | 🔴 Sin caller | Se llama desde `BranchCoordinator` post-ejecución de cada rama |
| FR-009 HypeDetector | 🔴 Sin endpoint | Se expone vía endpoint `POST /research/{id}/hype-analysis` |
| FR-010 DecisionAssistant | 🔴 Sin endpoint | Se expone vía endpoint `POST /research/{id}/decision` |
| FR-011 MiniMax Roles | 🟡 Roles no usados por callers | `ClarificationService`, `PlanBuilder`, `ReportSynthesizer` actualizados para usar `system` + `user_system` + `sample_message_*` |
| FR-007 SmartRouter | 🟡 Sin fallback si falla | Se mantiene orden fijo como fallback; SmartRouter por feature flag |

**Regla de oro**: Ningún archivo nuevo sin integration task. Ningún método nuevo sin caller.

---

## MCP Tool Usage Guide (para incluir en system prompt de cada agente)

Investigación de cada tool MCP con parámetros reales, basado en documentación oficial:

### Tavily

| Tool | Parámetros clave | Output | Notas |
|------|-----------------|--------|-------|
| `tavily_search` | `query` (str), `search_depth` ("basic"\|"advanced"), `max_results` (5-20), `include_answer` (bool), `include_raw_content` (bool), `include_images` (bool) | `{results[], answer?, raw_content?, images[]}` | Advanced depth da mejor calidad. `include_answer=True` para respuesta directa. Timeout 20s. |
| `tavily_extract` | `urls` (string[]) | `{results[{url, raw_content, images}]}` | Extrae contenido de URLs ya conocidas. Timeout 25s. Usar después de search. |

**Regla**: Siempre empezar con `tavily_search(include_answer=True)` para obtener contexto rápido. Si se necesita profundidad, usar `search_depth="advanced"`.

### Exa

| Tool | Parámetros clave | Output | Notas |
|------|-----------------|--------|-------|
| `web_search_exa` | `query` (str), `numResults` (1-100), `type` ("auto"\|"fast"\|"deep") | `{results[{url, title, snippet, publishedDate}]}` | Búsqueda general. Timeout 20s. |
| `web_search_advanced_exa` | `query` (str), `numResults`, `type`, `category` ("company"\|"news"\|"people"\|"research paper"\|"personal site"\|"financial report"), `includeDomains[]`, `startPublishedDate`, `endPublishedDate` | `{results[{url, title, snippet, ...}]}` | Búsqueda avanzada con filtros. Timeout 25s. Para company: category="company". Para news: category="news". |
| `web_fetch_exa` | `url` (str) | `{content}` | Obtener contenido completo de una URL. |

**Atención**: `category="company"` NO acepta `includeDomains` ni `startPublishedDate`. `includeText` solo soporta arrays de 1 elemento.

### Jina Reader

| Tool | Parámetros clave | Output | Notas |
|------|-----------------|--------|-------|
| `read_url` | `url` (str) | `{content: "# Title\n\nMarkdown content..."}` | Convierte HTML a markdown limpio. Sin API key funciona con rate limits. Timeout 20s. |
| `search_web` | `query` (str) | `{results[{url, title, content}]}` | Busca y extrae top resultados. Requiere API key Jina. |
| `guess_datetime_url` | `url` (str) | `{datetime?, confidence}` | Detecta fecha de última actualización de una URL. Timeout 15s. |

**Regla**: `read_url` es la herramienta más usada — extrae contenido limpio de cualquier URL. Siempre intentar Jina antes de Firecrawl (gratis).

### Brave Search

| Tool | Parámetros clave | Output | Notas |
|------|-----------------|--------|-------|
| `brave_web_search` | `query` (str, max 400 chars), `count` (1-20), `offset` (0-9), `freshness` ("pd"\|"pw"\|"pm"\|"py"), `safesearch` ("off"\|"moderate"\|"strict") | `{web:{results[{url, title, description}]}}` | Búsqueda web general. Timeout 20s. |
| `brave_news_search` | `query` (str), `count` (1-50), `freshness` (default: "pd"=24h) | `{news:{results[{url, title, description, age}]}}` | Noticias en tiempo real. Timeout 15s. Usar freshness="pd" por defecto. |

**Regla**: Brave es mejor para news en tiempo real. `freshness="pd"` da resultados de últimas 24h.

### Firecrawl

| Tool | Parámetros clave | Output | Notas |
|------|-----------------|--------|-------|
| `firecrawl_scrape` | `url` (str), `formats` (["markdown"]\|["json"]), `onlyMainContent` (bool) | `{content: "markdown...", metadata: {...}}` | Scrapea URLs con JS. Timeout 35s. Preferir `formats: ["markdown"]` + `onlyMainContent: true`. |

**Regla**: Usar solo cuando Jina no pueda extraer (sitios con JS pesado, SPAs). Firecrawl consume créditos.

### Google Scholar

| Tool | Parámetros clave | Output | Notas |
|------|-----------------|--------|-------|
| `search_google_scholar_key_words` | `query` (str), `num_results` (int, default 5) | `[{title, authors, year, url, citations?}]` | Búsqueda por palabras clave. Sin API key. Timeout 25s. |
| `search_google_scholar_advanced` | `query` (str), `author` (str?), `year_range` ([start, end]?), `num_results` (int) | `[{title, authors, year, url}]` | Búsqueda avanzada con filtros. |

**Regla**: La búsqueda académica es lenta (scrapea Google Scholar). Usar `num_results` bajo (5-10) y combinarlo con ArXiv.

### ArXiv

| Tool | Parámetros clave | Output | Notas |
|------|-----------------|--------|-------|
| `search_papers` | `query` (str), `max_results` (int), `date_from` (YYYY-MM-DD), `categories` (["cs.AI", "cs.LG", ...]), `sort_by` ("date"\|"relevance") | `[{id, title, authors, summary, published, link}]` | Busca papers en ArXiv. Timeout 25s. |
| `download_paper` | `paper_id` (str, ej: "2401.12345") | `{content: "markdown..."}` | Descarga paper completo. Llamar después de search_papers. |
| `read_paper` | `paper_id` (str) | `{content: "full text..."}` | Lee paper descargado. Requiere download_paper primero. |

**Regla**: Usar `search_papers(categories=["cs.AI","cs.LG"], sort_by="date")` para papers recientes. Siempre llamar `download_paper` antes de `read_paper`.

### MCP Fetch

| Tool | Parámetros clave | Output | Notas |
|------|-----------------|--------|-------|
| `fetch` | `url` (str), `max_length` (int, default 5000), `start_index` (int, default 0), `raw` (bool, default false) | `{content: "markdown..."}` | HTTP GET → markdown. Gratis, sin API key. Timeout 20s. |

**Regla**: Alternativa gratuita a Jina para URLs simples. Si el contenido es largo, usar `start_index` para paginar. Para contenido LLM-optimized, preferir Jina.

---

## Phases & Tasks

### Phase 0 — Foundation + Integración en DI

| ID | Feature | Archivo(s) | Subagente |
|----|---------|-----------|-----------|
| **T001** | FR-012: MCP Fetch — ✅ ya instalado y configurado en mcp-providers.json | `mcp-providers.json`, `dependencies.py` | ✅ Hecho |
| **T002** | FR-001: SourceScorer — clase con DOMAIN_SCORES + `score(url)` | `application/evaluation/source_scorer.py` | ✅ |
| **T003** | FR-001: Integrar SourceScorer en EvidenceLinker.deduplicate_sources() — scoring opcional, default True | `application/fusion/evidence_linker.py` | ✅ |
| **T004** | FR-006: MCPSmartCache — wrapper thread-safe con TTL por tool + diskcache | `infra/mcp/mcp_cache.py` | ✅ |
| **T005** | FR-011: MiniMaxMessage — agregar field `name: str = ""`, serializar en payload | `domain/system_base.py`, `infra/llm/minimax_client.py` | ✅ |
| **T006** | FR-011: Agregar mensaje `system` + `user_system` + `sample_message_*` en `MiniMaxClient.complete()` + actualizar `ClarificationService`, `PlanBuilder`, `ReportSynthesizer` para usar los nuevos roles | `infra/llm/minimax_client.py`, `prompts/minimax_examples/`, `application/clarification/`, `application/planning/`, `application/fusion/` | ⛓️ |
| **T007** | Wire new services (`source_scorer`, `mcp_cache`, `smart_router`, `parameter_learner`) en `api/dependencies.py` | `api/dependencies.py` | ⛓️ |
| **T008** | Tests: SourceScorer, MCPSmartCache | `tests/test_source_scorer.py`, `tests/test_mcp_cache.py` | ✅ |

### Phase 1 — Knowledge Graph

| ID | Feature | Archivo(s) | Subagente |
|----|---------|-----------|-----------|
| **T009** | FR-002: `search_across_sessions()` — extender `PostgresVectorIndex.list_by_session()` con `session_id: UUID \| None`. Cuando None, busca en TODAS las sesiones. | `infra/persistence/vector_index.py`, `application/graph/knowledge_graph_service.py` | ⛓️ Serial |
| **T010** | FR-003: `discover_ecosystem(seed, graph, depth)` — recorrer KnowledgeGraph desde nodo semilla clasificando relaciones como "compete", "adopted_by", "depends_on", "emerging" | `application/graph/knowledge_graph_service.py` | ⛓️ |
| **T011** | Endpoint `GET /research/{id}/graph/ecosystem?seed=...&depth=2` en research_outputs.py + registro en router | `api/routes/research_outputs.py`, `api/router.py` | ✅ |
| **T012** | Tests: cross-session search, ecosystem map | `tests/test_graph_api_contract.py` | ✅ |

### Phase 2 — Agent Intelligence

| ID | Feature | Archivo(s) | Subagente |
|----|---------|-----------|-----------|
| **T013** | FR-007: SmartToolRouter — clasificar query por keywords, devolver orden óptimo de tools. Gated por feature flag. | `application/governance/smart_router.py` | ✅ |
| **T014** | FR-007: Integrar SmartToolRouter en BaseBranchAgent.run() — si SmartToolRouter está activo, usarlo; si no, usar orden fijo actual. | `application/agents/base.py` | ⛓️ |
| **T015** | FR-005: Agregar `signal_branch(target, payload)` en BaseBranchAgent + llamarlo desde run() cuando un finding tiene tags de otra rama | `application/agents/base.py` | ⛓️ |
| **T016** | FR-005: Cola de señales en BranchCoordinator + `_process_cross_signals()` post-ejecución de cada rama | `application/execution/branch_coordinator.py` | ⛓️ |
| **T017** | FR-008: ParameterLearner — `record_outcome(branch, params, success, coverage)` + `suggest(branch)`. Llamado desde BranchCoordinator después de cada BranchResult. | `application/evaluation/parameter_learner.py` | ✅ |
| **T018** | FR-004: ObsolescenceDetector — heurística sin LLM. Expuesto vía endpoint `POST /research/{id}/obsolescence?tech=...` | `application/evaluation/obsolescence_detector.py` + `api/routes/research_outputs.py` | ✅ |
| **T019** | Tests: SmartToolRouter, ObsolescenceDetector | `tests/test_smart_router.py` | ✅ |
| **T020** | FR-006: Integrar MCPSmartCache en MCPExecutionClient.execute_tool() — wrapper transparente que consulta cache antes de ejecutar | `infra/mcp/execution_client.py` | ⛓️ |

### Phase 3 — Advanced Analysis (MiniMax opcional)

| ID | Feature | Archivo(s) | Subagente |
|----|---------|-----------|-----------|
| **T021** | FR-009: HypeDetector — cruzar papers, prototipos, funding, patentes. Sin LLM: ratio. Con LLM: análisis narrativo. Expuesto vía endpoint `POST /research/{id}/hype-analysis` | `application/evaluation/hype_detector.py` + `api/routes/research_outputs.py` | ✅ |
| **T022** | FR-010: DecisionAssistant — análisis upside/downside/riesgos/recomendación. Sin LLM: template básico. Con LLM: análisis profundo. Expuesto vía endpoint `POST /research/{id}/decision` | `application/fusion/decision_assistant.py` + `api/routes/research_outputs.py` | ✅ |
| **T023** | Tests: HypeDetector, DecisionAssistant | `tests/test_evaluation_advanced.py` | ✅ |

### Phase 4 — Tool Usage Prompts Integration

| ID | Feature | Archivo(s) | Subagente |
|----|---------|-----------|-----------|
| **T024** | Crear tool usage guides en `src/prompts/tools/` con parámetros reales de cada MCP | `prompts/tools/tavily.txt`, `exa.txt`, `jina.txt`, `brave.txt`, `firecrawl.txt`, `scholar.txt`, `arxiv.txt`, `fetch.txt` | ✅ |
| **T025** | Integrar tool usage guides en PromptComposer para que cada agente reciba instrucciones de cómo usar cada tool según su skill matrix | `application/governance/prompt_composer.py` | ⛓️ |
| **T026** | Verificación final: `python -m pytest -q` — 50+ tests pasando. Validar que con `VT_SYSTEM_BASE_ENABLED=false` o sin API keys todo funciona con comportamiento legacy. | Suite completa | ❌ |

---

## Phase 5 — Completar Features Parciales (6 features)

**Goal**: Cerrar las 6 features que quedaron parciales conectándolas con providers reales o endpoints faltantes.

### P5.1: SourceScorer → Conectar a Findings

**Estado actual**: SourceScorer existe con 45+ dominios, está en DI, pero no modifica el confidence de los findings.

**Fix**: Agregar campo `confidence` a `SourceRef` y aplicar `SourceScorer.score()` en `EvidenceLinker.deduplicate_sources()`.

```python
# domain/models.py — SourceRef
@dataclass(slots=True)
class SourceRef:
    ...
    confidence: float = 0.7  # NEW: default neutral
```

```python
# evidence_linker.py
if use_scoring:
    for source in sources:
        source.confidence = min(
            source.confidence, 
            self._source_scorer.score(source.url)
        )
```

**Archivos**: `domain/models.py`, `application/fusion/evidence_linker.py`

### P5.2: Cross-Session Search → Endpoint REST

**Estado actual**: `search_across_sessions()` existe en `KnowledgeGraphService` pero no hay endpoint HTTP.

**Fix**: Agregar endpoint `GET /research/{id}/graph/search-cross-session?query=...` que usa `vector_index.list_by_session(None)` + `search_across_sessions()`.

**Archivo**: `api/routes/research_outputs.py`

### P5.3: Obsolescencia → Conectar Providers

**Estado actual**: Endpoint existe pero siempre devuelve `confidence=0.3`. No consulta brave, exa ni serper.

**Fix**: Conectar `ObsolescenceDetector.analyze()` con:
- `brave_news_search` para detectar descenso de menciones
- `web_search_advanced_exa` para detectar alternativas nuevas
- Calcular confidence basado en señales reales (con fallback si no hay API keys)

```python
async def analyze(self, tech_name: str) -> ObsolescenceSignal:
    signal = ObsolescenceSignal(tech=tech_name)
    try:
        news = await brave_client.search_news(...)
        signal.signals.append(f"{len(news.items)} news mentions found")
    except Exception:
        signal.signals.append("Brave news unavailable")
    # Heurística: si hay noticias viejas y pocas recientes → declive
    signal.confidence = compute_from_signals(signal.signals)
    signal.recommendation = build_recommendation(signal)
    return signal
```

**Archivo**: `application/evaluation/obsolescence_detector.py`

### P5.4: Branch Signaling → Re-ejecución Real

**Estado actual**: `_process_cross_signals()` solo logea la señal, no ejecuta una sub-investigación.

**Fix**: En `BranchCoordinator.execute()`, después de la ejecución principal, procesar señales y spawnear sub-ejecuciones con `agent.run()`. Los resultados se mergean al reporte final.

```python
async def _process_cross_signals(self, session, plan, results):
    while self._signal_queue:
        signal = self._signal_queue.pop(0)
        agent = self._agents.get(signal.target_branch)
        if agent:
            sub_branch = BranchConfig(
                branch_type=signal.target_branch,
                focus_queries=[signal.query],
                mcp_providers=DEFAULT_PROVIDERS.get(signal.target_branch, []),
            )
            sub_result = await agent.run(session, sub_branch, depth_limit=2)
            results.append(sub_result)
    return results
```

**Archivos**: `application/execution/branch_coordinator.py`, `application/agents/base.py`

### P5.5: Hype Detector → Conectar Providers Reales

**Estado actual**: Endpoint existe pero no consulta arxiv, exa, firecrawl ni serper.

**Fix**: Conectar `HypeDetector.analyze()` con los 4 providers:
- `search_papers` → contar papers académicos (real signal)
- `web_search_advanced_exa` + `category="company"` → detectar funding real
- `firecrawl_scrape` → buscar prototipos funcionales
- Calcular `hype_ratio = (social_mentions / academic_papers)`

```python
async def analyze(self, tech_name: str, 
                   arxiv_client=None, exa_client=None,
                   firecrawl_client=None) -> HypeReport:
    # Cada provider es opcional; si falta, se salta esa señal
    ...
```

**Archivo**: `application/evaluation/hype_detector.py`

### P5.6: Decision Assistant → Heurística sin LLM

**Estado actual**: Sin MiniMax API key, devuelve "Enable VT_MINIMAX_API_KEY". Debe funcionar también sin LLM.

**Fix**: Agregar heurística basada en branch_results reales:
- Si hay findings con confianza alta → upside real
- Si hay findings sobre riesgos → downside real
- Template estructurado que funciona sin MiniMax

```python
async def analyze(self, question: str, branch_results: list | None = None) -> DecisionReport:
    if branch_results:
        # Extraer upside/downside de findings reales
        for result in branch_results:
            for finding in result.findings:
                if finding.confidence > 0.8:
                    report.upside.append(finding.statement)
    return report
```

**Archivo**: `application/fusion/decision_assistant.py`

---

## Phase 5 Tasks

| ID | Feature | Archivo(s) | Esfuerzo |
|----|---------|-----------|----------|
| T027 | P5.1: Agregar `confidence` a SourceRef + aplicar SourceScorer | `domain/models.py`, `evidence_linker.py` | 🟢 Bajo |
| T028 | P5.2: Endpoint cross-session search | `research_outputs.py`, `knowledge_graph_service.py` | 🟢 Bajo |
| T029 | P5.3: Conectar providers a ObsolescenceDetector | `obsolescence_detector.py` | 🟡 Medio |
| T030 | P5.4: Re-ejecución real en Branch Signaling | `branch_coordinator.py`, `base.py` | 🟡 Medio |
| T031 | P5.5: Conectar 4 providers a HypeDetector | `hype_detector.py` | 🟡 Medio |
| T032 | P5.6: Heurística sin LLM en DecisionAssistant | `decision_assistant.py` | 🟢 Bajo |
| T033 | Tests + verificación final 59+ tests | Suite completa | 🟢 Bajo |

---

## Verificación de Código Muerto

| Ítem | Estado | Acción |
|------|--------|--------|
| `PromptContract` + `load_prompt_template()` | 🟡 En uso (backward compat) | No eliminar — se usa en endpoint `/agent-contracts` y en fallback de `base.py` |
| `VectorRecord` import en research_outputs | ✅ Ya limpio | No aplica |
| `branch_kpi_service` en research_approve | ✅ En uso | No eliminar |
| Phase 9 services (SourceScorer, MCPSmartCache, etc.) | ✅ Todos conectados vía DI o endpoints | No eliminar |
| Phase 9 endpoints (obsolescence, hype, decision) | ✅ Todos importados y registrados | No eliminar |

**Conclusión**: No hay código muerto que eliminar. Todo lo creado está conectado. Lo que falta es que 6 features parciales reciban datos de providers reales o endpoints para ser completamente funcionales.

| Código existente | Por qué no se rompe |
|-----------------|-------------------|
| `EvidenceLinker.deduplicate_sources()` | SourceScorer es opcional, default `use_scoring=True`. Tests mockean EvidenceLinker. |
| `BaseBranchAgent.run()` | SmartToolRouter es gated por flag. Señales son post-ejecución. |
| `BranchCoordinator.execute()` | ParameterLearner y señales son post-procesamiento. El flujo principal no cambia. |
| `MCPExecutionClient.execute_tool()` | MCPSmartCache es wrapper opcional. Sin cache, ejecuta igual. |
| `MiniMaxClient.complete()` | Roles adicionales se agregan antes del user message. No cambia la estructura de respuesta. |
| `ClarificationService.generate_questions()` | `llm=None` → fallback a preguntas fijas igual que antes. |
| `PlanBuilder.build()` | `llm=None` → fallback a templates igual que antes. |
| `ReportSynthesizer.synthesize()` | `llm=None` → fallback a concatenación igual que antes. |
| Tests existentes | Nuevos tests cubren solo código nuevo. 50 tests existentes no se modifican. |

## Lo que se debe actualizar en conftest.py

| Nuevo servicio | Monkeypatch requerido |
|---------------|---------------------|
| `source_scorer` | Si se usa en endpoint de ruta, monkeypatch en conftest.py |
| `mcp_cache` | Mockear `MCPExecutionClient` — el cache es interno, no requiere monkeypatch |
| `smart_router` | Si se activa, monkeypatch en `BaseBranchAgent` |

---

## Dependency Graph

```
Phase 0: T002 ─ T003 ─ T007 ─ T008
         T004 ─ T007 ─ T020 (en Phase 2)
         T005 ─ T006 ─ T007
         
Phase 1: T009 ─ T012
         T010 ─ T011 ─ T012
         
Phase 2: T013 ─ T014 ─ T015 ─ T016
         T017 ─ T019
         T018 ─ T019
         T020
         
Phase 3: T021 ─ T023
         T022 ─ T023
         
Phase 4: T024 ─ T025 ─ T026
```

## Parallelism

| Bloque | Tasks | Subagentes |
|--------|-------|------------|
| Foundation A | T002, T004, T005, T008 | ✅ 4 en paralelo |
| Foundation B | T003 (tras T002), T006 (tras T005), T007 (tras T003+T006) | ⛓️ Serial |
| Graph | T009+T010 serial, T011+T012 paralelo | ⛓️ + ✅ |
| Agent A | T013, T017, T018 | ✅ 3 en paralelo |
| Agent B | T014 (tras T013), T015+T016 serial, T019 (tras T017+T018) | ⛓️ |
| Agent C | T020 (independiente) | ✅ |
| Analysis | T021, T022 | ✅ 2 en paralelo |
| Tools | T024, T025 (tras T024), T026 (final) | ⛓️ |

## Implementation Strategy

1. **Phase 0** primero — foundation + DI wiring. Sin esto, nada nuevo funciona.
2. **Phase 1** — extender grafo con búsqueda cross-sesión y ecosistemas.
3. **Phase 2** — inteligencia de agente (router, signaling, cache, tuning, obsolescencia). Cada feature tiene su caller definido.
4. **Phase 3** — análisis avanzado con endpoints REST explícitos.
5. **Phase 4** — tool usage guides + verificación final.
6. **Tests** después de cada fase. `python -m pytest -q` antes y después.
7. **Validación**: probar con `VT_SYSTEM_BASE_ENABLED=false` y sin API keys para verificar comportamiento legacy intacto.
