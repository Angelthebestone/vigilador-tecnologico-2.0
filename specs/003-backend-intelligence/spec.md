# Feature Specification: Backend Intelligence v3

## Problem Statement

El backend actual ejecuta investigaciones bajo demanda pero carece de capacidades avanzadas de inteligencia: no hay memoria entre sesiones, no hay detección proactiva de tendencias, el ruteo de herramientas es fijo, y no se aprovechan las capacidades completas de MiniMax (roles de mensaje, ejemplos few-shot). El sistema investiga pero no "piensa" estratégicamente.

## Scope Boundaries

### In Scope
- Puntaje de confianza por fuente (source scoring)
- Búsqueda semántica cross-sesión
- Mapeo automático de ecosistemas tecnológicos (dependencias, competencias, adopciones)
- Alertas de obsolescencia detectada (declining tech signals)
- Auto-expansión de ramas entre agentes (branch signaling)
- Caché inteligente de resultados MCP (TTL por tool)
- Ruteo inteligente de herramientas por tipo de query
- Detector de tecnología falsa/exagerada (hype analysis)
- Asistente de decisión con análisis riesgo/retorno
- Optimización de MiniMax: roles user_system, sample_message_user/ai, name field
- Instalación y configuración de MCP Fetch
- Google Scholar MCP integration

### Out of Scope
- Frontend UI para estas features
- Monitoreo periódico automatizado (watchdog) — postergado
- Sentimiento por tecnología
- Dashboard de inteligencia competitiva
- Slack/Teams integration

## Assumptions
- MiniMax API key será configurada eventualmente (todo funciona sin ella con fallback)
- Embeddings Gemini están activos (VT_EMBEDDING_API_KEY configurada, funcional)
- Todas las features nuevas usan parámetros opcionales con fallback al comportamiento actual
- La caché MCP usa `diskcache` para persistencia entre sesiones

## Implementation Status

| Feature | FR | Estado | Notas |
|---------|----|--------|-------|
| SourceScorer | FR-001 | ✅ | 45+ dominios, aplicado en dedup |
| Cross-session search | FR-002 | ✅ | Conectado a endpoint |
| Ecosystem map | FR-003 | ✅ | discover_ecosystem() |
| ObsolescenceDetector | FR-004 | ✅ | Conectado a MCPs |
| Branch Signaling | FR-005 | ✅ | Spawns sub-executions reales |
| MCP Smart Cache | FR-006 | ✅ | TTL por tool, lazy imports |
| SmartToolRouter | FR-007 | ✅ | 6 tipos de query |
| ~~ParameterLearner~~ | ~~FR-008~~ | ❌ Eliminado | 0 callers, archivo removido |
| HypeDetector | FR-009 | ✅ | hype_ratio computado |
| DecisionAssistant | FR-010 | ✅ | Heurístico, sin MiniMax |
| MiniMax roles | FR-011 | ✅ | 7 roles, prompts creados |
| MCP Fetch | FR-012 | ✅ | pip install mcp-server-fetch |
| Google Scholar MCP | FR-013 | ✅ | Integrado desde zip |
| Prompts HTML | FR-014 | ✅ | 21 prompts con HTML semántico |

## Existing Environment Verified

### Variables de Entorno

Todas declaradas en `settings.py`. Las de embedding YA están declaradas allí:

```python
embedding_api_key: SecretStr | None = None       # VT_EMBEDDING_API_KEY ✅ Activo
embedding_model: str = "gemini-embedding-2"       # VT_EMBEDDING_MODEL
embedding_dimensions: int = 768                   # VT_EMBEDDING_DIMENSIONS
embedding_batch_size: int = 16                    # VT_EMBEDDING_BATCH_SIZE
```

Variables MCP verificadas funcionales:
- Tavily, Exa, Jina, Serper, Brave, Firecrawl — ✅ Keys configuradas
- Gemini Embedding — ✅ HTTP 200 con x-goog-api-key header
- MiniMax — ❌ Sin API key (único pendiente)

### MiniMax Message Roles (Documentación Verificada)

MiniMax-M2.7 soporta estos roles. Implementados en `MiniMaxMessage`:

| Role | Estado |
|------|--------|
| `system` | ✅ Definir personalidad del modelo |
| `user` | ✅ Consulta del usuario |
| `assistant` | ✅ Respuesta del modelo |
| `user_system` | ✅ Definir rol/persona del usuario |
| `group` | ✅ Nombrar la conversación |
| `sample_message_user` | ✅ Ejemplo few-shot de input |
| `sample_message_ai` | ✅ Ejemplo few-shot de output |

Archivos de ejemplo en `src/vigilancia_multiagente/prompts/minimax_examples/`.

### MCP Fetch

- Paquete: `mcp-server-fetch` v2025.4.7 (pip) ✅
- Tools: `fetch` — HTTP GET → markdown
- Sin API key requerida
- Registrado en `src/vigilancia_multiagente/infra/mcp/mcp-providers.json`

### Google Scholar MCP

- Integrado desde código fuente (zip extraído en `.mcp-servers/`)
- Tools: `search_google_scholar_key_words`, `search_google_scholar_advanced`, `get_author_info`
- Dependencias: requests, bs4, mcp, scholarly
- No requiere API key

---

## Functional Requirements (Features)

### FR-001: ✅ Puntaje de Confianza por Fuente

**Descripción**: Asignar puntajes de confianza a URLs basados en el dominio, permitiendo que los hallazgos de fuentes confiables pesen más.

**Archivo**: `src/vigilancia_multiagente/application/evaluation/source_scorer.py`

**Integración**: Aplicado en `EvidenceLinker.deduplicate_sources()` y `SourceRef.confidence`.

### FR-002: ✅ Búsqueda Semántica Cross-Sesión

**Descripción**: Buscar hallazgos de sesiones anteriores usando embeddings, no solo de la sesión actual.

**Archivo**: `application/graph/knowledge_graph_service.py` — `search_across_sessions()`

**Endpoint**: Conectado vía API.

### FR-003: ✅ Mapeo Automático de Ecosistemas Tecnológicos

**Descripción**: Dado un término tecnológico semilla, descubrir relaciones: compite con, adoptado por, depende de, emergente.

**Archivo**: `application/graph/knowledge_graph_service.py` — `discover_ecosystem()`

### FR-004: ✅ Alertas de Obsolescencia Detectada

**Descripción**: Detectar tecnologías en declive cruzando datos de hiring, alternativas, actividad de core team.

**Archivo**: `application/evaluation/obsolescence_detector.py`

**Integración**: Conectado a MCPs (Tavily, Exa, Brave).

### FR-005: ✅ Auto-expansión de Rama (Branch Signaling)

**Descripción**: Cuando un agente encuentra información relevante para otra rama, notificarla automáticamente.

**Archivos**: `application/agents/base.py`, `application/execution/branch_coordinator.py`

### FR-006: ✅ Caché Inteligente de Resultados MCP

**Descripción**: Cachear resultados de MCP tools para evitar llamadas duplicadas y reducir costos.

**Archivo**: `infra/mcp/mcp_cache.py`

**TTL configurado por tool** (horas/días según volatilidad de cada fuente).

### FR-007: ✅ Ruteo Inteligente de Herramientas

**Descripción**: Reemplazar el orden fijo de tools por selección dinámica según tipo de query.

**Archivo**: `application/governance/smart_router.py`

**Tipos**: academic, company, patent, news, deep_research, general.

### FR-008: ❌ ELIMINADO — ParameterLearner

**Razón**: 0 callers en todo el proyecto. Archivo `parameter_learner.py` removido completamente.

### FR-009: ✅ Detector de Tecnología Falsa/Exagerada (Hype Detector)

**Descripción**: Cruzar papers, prototipos, funding real y patentes para detectar hype sin sustento.

**Archivo**: `application/evaluation/hype_detector.py`

### FR-010: ✅ Asistente de Decisión con Análisis Riesgo/Retorno

**Descripción**: Dada una pregunta estratégica, analizar upside, downside, riesgos, y recomendar acción.

**Archivo**: `application/evaluation/decision_assistant.py`

### FR-011: ✅ Optimización de MiniMax — Roles Avanzados

**Descripción**: Usar los roles adicionales de MiniMax para mejorar calidad de output.

**Cambios implementados**:
- MiniMaxMessage con 7 roles (system, user, assistant, user_system, group, sample_message_user, sample_message_ai)
- Archivos de ejemplo en `src/vigilancia_multiagente/prompts/minimax_examples/`
- Pendiente: activar con VT_MINIMAX_API_KEY

### FR-012: ✅ MCP Fetch

**Descripción**: Herramienta gratuita de extracción de URLs.

- Instalado: `mcp-server-fetch` v2025.4.7
- Herramienta: `fetch`
- Sin API key
- Provider registrado en `mcp-providers.json`

### FR-013: ✅ Google Scholar MCP

**Descripción**: Búsqueda académica en Google Scholar vía MCP.

- Tools: keywords_search, advanced_search, get_author_info
- Código en `.mcp-servers/google-scholar/` (gitignored)
- No requiere API key

### FR-014: ✅ Prompts con HTML Semántico

**Descripción**: Los 21 archivos .txt de prompt usan estructura HTML para mejor adherencia del modelo.

**Tags utilizados**: `<system>`, `<task>`, `<rules>`, `<output_schema>`, `<confidence_guidelines>`, `<evidence_quality>`, `<contradiction_handling>`, `<next_query_guidelines>`, `<tool>`, `<selection_heuristics>`, `<chaining>`, `<fallback>`, `<context>`

---

## Key Entities

- **SourceScore**: Puntaje de confianza 0.0-1.0 por dominio
- **CrossSessionResult**: Hallazgo de sesión anterior con metadata de origen
- **EcosystemMap**: Grafo de relaciones tecnológicas
- **ObsolescenceReport**: Señales de declive + recomendación
- **SignalPayload**: Mensaje cross-branch con query + source + relevancia
- **CacheEntry**: Resultado MCP cacheado con TTL y timestamp
- **ToolRoute**: Selección dinámica de herramientas según tipo de query
- **HypeReport**: Análisis de hype con ratio y veredicto
- **DecisionReport**: Análisis riesgo/retorno con recomendación
- **FinalReport**: Reporte estructurado con 12 campos + Recommendation

---

## Success Criteria

- **SC-001**: SourceScorer asigna puntaje correcto para 45+ dominios conocidos ✅
- **SC-002**: Búsqueda cross-sesión retorna hallazgos de sesiones previas ✅
- **SC-003**: EcosystemMap detecta relaciones de 3+ tipos ✅
- **SC-004**: ObsolescenceDetector correlaciona señales de múltiples fuentes ✅
- **SC-005**: Branch signaling entrega payload y otra rama lo procesa ✅
- **SC-006**: MCPSmartCache reduce llamadas MCP duplicadas ✅
- **SC-007**: SmartToolRouter selecciona herramienta óptima por tipo de query ✅
- **SC-008**: ~~ParameterLearner mejora cobertura en >10%~~ ❌ Feature removida
- **SC-009**: HypeDetector clasifica con hype_ratio computado ✅
- **SC-010**: DecisionAssistant produce análisis estructurado ✅
- **SC-011**: MiniMaxMessages incluyen 7 roles (sin API key) ✅
- **SC-012**: MCP Fetch responde a fetch() con markdown ✅
- **SC-013**: Google Scholar MCP integrado con 3 tools ✅
- **SC-014**: 21 prompts con HTML semántico y contenido en inglés ✅

## Delivery Constraints

- Ninguna feature nueva debe romper el flujo actual (parámetros opcionales, fallbacks)
- Sin API key de MiniMax: todo funciona con comportamiento actual
- Código limpio, sin abstracciones innecesarias, cambios quirúrgicos (Karpathy guidelines)
- 59+ tests deben seguir pasando
- Ruff 0 issues
