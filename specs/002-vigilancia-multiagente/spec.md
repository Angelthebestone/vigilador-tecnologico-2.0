# Feature Specification: Vigilancia Tecnologica Multiagente

## Problem Statement
El proceso de vigilancia tecnologica actual no permite responder con suficiente velocidad y profundidad a preguntas estrategicas cuando se requieren analisis simultaneos (comercial, normativo, innovacion, riesgo y entorno competitivo). La version previa resolvio parte del problema, pero su enfoque iterativo y estructura de investigacion limita la escalabilidad, la especializacion por dominio y la calidad de las decisiones en escenarios de alta incertidumbre.

## Scope Boundaries
### In Scope
- Flujo completo de investigacion desde consulta inicial hasta reporte final accionable.
- Coordinacion de multiples agentes especializados ejecutando analisis en paralelo por tipo de estado tecnologico.
- Definicion de ramas de investigacion configurables por enfoque (comercial, normativo, innovacion, riesgo y competitivo).
- Consolidacion de hallazgos en un reporte unico con trazabilidad de evidencias.
- Construccion y exploracion de un grafo de conocimiento con relaciones entre aprendizajes.
- Visualizacion de fuentes asociadas al seleccionar un nodo del grafo.
- Integracion con 9+ proveedores MCP (Tavily, Exa, Jina, Brave, Firecrawl, Serper, Google Scholar, ArXiv, Fetch).

### Out of Scope
- Automatizacion de decisiones finales de negocio sin revision humana.
- Reemplazo de procesos legales, regulatorios o de due diligence formales.
- Integraciones con sistemas corporativos no relacionados con vigilancia tecnologica.
- Frontend UI (separado en spec 004).

## Implementation Status

| Componente | Estado |
|------------|--------|
| API v2 endpoints | ✅ Completo |
| Orchestracion multiagente | ✅ Completo |
| Sistema de grafo (NetworkX) | ✅ Completo |
| Rama AVANCES | ✅ Completo |
| Rama COMERCIAL | ✅ Completo |
| Rama RIESGO | ✅ Completo |
| Rama PI_NORMATIVA | ✅ Completo |
| Rama COMPETITIVO | ✅ Completo |
| Rama OPORTUNIDADES | ✅ Completo |
| Consolidacion/reporte | ✅ Completo (FinalReport) |
| SSE events | ✅ Completo (12+ eventos) |
| Content extraction pipeline | ✅ Completo |
| Cross-session search | ✅ Completo |
| MCP Smart Cache | ✅ Completo |
| SmartToolRouter | ✅ Completo |
| SourceScorer | ✅ Completo |
| ObsolescenceDetector | ✅ Completo |
| HypeDetector | ✅ Completo |
| DecisionAssistant | ✅ Completo |
| Branch Signaling | ✅ Completo |
| Prompt HTML restructuring | ✅ Completo (21 archivos) |
| MiniMax roles (7 roles) | ✅ Completo (sin API key) |
| MCP Fetch | ✅ Completo (pip install) |
| Google Scholar MCP | ✅ Completo |
| System Base / BranchOverlay | ✅ Completo |
| Golden cases / regression tests | ✅ Completo |
| 59 tests unitarios | ✅ Pasando |
| Ruff 0 issues | ✅ Completo |
| Postgres + pgvector | ⏳ Pendiente (BD no disponible) |
| MiniMax API key | ❌ Bloqueado (sin key) |
| Frontend UI | 📅 Spec 004 futuro |

## Assumptions
- La plataforma sigue una estrategia de orquestacion centralizada para gobernar todo el flujo de investigacion.
- Las capacidades de embedding se usan para mejorar relacion semantica y navegacion del conocimiento (Gemini activo).
- La persona usuaria define el alcance inicial (tema, geografia, prioridades) antes de ejecutar el analisis.
- La calidad del resultado depende de la disponibilidad y diversidad de fuentes externas consultables.
- Los MCP STDIO requieren `npx`/`uvx`/Python runtime disponibles en el entorno de ejecucion.
- Archivos de proveedores MCP de terceros se almacenan en `.mcp-servers/` (gitignored).

## User Scenarios & Testing
### Primary User Story
Como lider de vigilancia tecnologica, quiero lanzar una investigacion con agentes especializados en paralelo y recibir un reporte consolidado con un grafo navegable para identificar riesgos, oportunidades y decisiones de accion con respaldo en evidencia.

### Acceptance Scenarios
1. **Given** una consulta de vigilancia tecnologica con objetivos de negocio, **When** la persona usuaria inicia la investigacion, **Then** el sistema crea una sesion con ramas especializadas listas para ejecutarse en paralelo.
2. **Given** una sesion activa con ramas definidas, **When** se ejecuta el analisis, **Then** cada rama produce hallazgos de su dominio con evidencia trazable y estado de progreso visible.
3. **Given** resultados parciales o completos de las ramas, **When** finaliza la consolidacion, **Then** el sistema entrega un reporte unico con conclusiones, riesgos, oportunidades y recomendaciones priorizadas.
4. **Given** un reporte consolidado con grafo generado, **When** la persona usuaria selecciona un nodo del grafo, **Then** el sistema muestra los enlaces y aprendizajes relacionados con ese nodo.

### Edge Cases
- Si una o varias ramas no logran suficiente evidencia, el reporte debe marcar cobertura incompleta y su impacto en la confianza de conclusiones.
- Si existen conflictos entre hallazgos de ramas distintas, el sistema debe resaltar contradicciones y solicitar validacion humana.
- Si el volumen de resultados supera lo manejable, el sistema debe priorizar y resumir sin perder trazabilidad hacia las fuentes.
- Si una fuente aparece repetida en diferentes ramas, el sistema debe deduplicar manteniendo referencia cruzada por contexto.

## Functional Requirements
- **FR-001**: El sistema debe permitir registrar una solicitud de vigilancia tecnologica en lenguaje natural y asociarla a una sesion unica. ✅
- **FR-002**: El sistema debe crear un plan de investigacion con ramas especializadas alineadas a los objetivos declarados por la persona usuaria. ✅
- **FR-003**: El sistema debe ejecutar ramas especializadas de forma paralela y monitorear su estado individual. ✅
- **FR-004**: Cada rama debe generar hallazgos estructurados con evidencia, nivel de relevancia y contexto de negocio. ✅
- **FR-005**: El sistema debe consolidar resultados de todas las ramas en un reporte final coherente, no redundante y trazable. ✅
- **FR-006**: El reporte final debe incluir secciones de estado tecnologico, riesgo, entorno comercial, normativo, innovacion y oportunidades. ✅
- **FR-007**: El sistema debe construir un unico grafo de conocimiento por sesion y aplicar analiticas sobre el. ✅
- **FR-008**: Al interactuar con un nodo del grafo, mostrar todas las fuentes y hallazgos conectados. ✅
- **FR-009**: El sistema debe mantener historial de decisiones y cambios de estado de la sesion. ✅
- **FR-010**: El sistema debe permitir reejecutar investigaciones con nuevos parametros. ✅
- **FR-011**: El sistema debe integrar 9+ proveedores MCP para busqueda y extraccion de informacion. ✅
- **FR-012**: Los prompts de agente deben usar estructura HTML semantica para mejor adherencia del modelo. ✅

## MCP Provider Map

| Provider | Transport | Status | Tools |
|----------|-----------|--------|-------|
| Tavily | HTTP | ✅ Verificado | search, extract |
| Exa | HTTP | ✅ Verificado | web_search, web_fetch, advanced |
| Jina | HTTP | ✅ Verificado | read_url, search_web, guess_datetime |
| Brave | STDIO (npx) | ✅ Instalado | web_search, news_search |
| Firecrawl | STDIO (npx) | ✅ Instalado | scrape, search, crawl, map, extract |
| Serper | HTTP | ✅ Verificado | web_search, news, patents |
| Google Scholar | STDIO (python) | ✅ Integrado | keywords_search, advanced_search, author_info |
| ArXiv | STDIO (uvx/pip) | ✅ Instalado | search, download, read |
| Fetch | STDIO (pip) | ✅ Instalado | fetch (URL→markdown) |

## Prompt Architecture
Los 21 archivos de prompt usan estructura HTML semantica con los siguientes tags:

- `<system>` / `<user_system>` / `<sample_message_user>` / `<sample_message_ai>` — Roles MiniMax
- `<tool name="...">` — Definiciones de herramientas con `<function_signature>`, `<best_for>`, `<usage>`, `<limits>`, `<selection_heuristics>`, `<chaining>`, `<fallback>`
- `<task>` — Objetivos de rama y pasos de analisis
- `<context>` — Variables de entrada y resultados
- `<rules type="do|dont">` — Restricciones de comportamiento
- `<output_schema>` — Especificacion de JSON de salida
- `<confidence_guidelines>` — Calibracion de confianza 0.0-1.0
- `<evidence_quality>` — Requisitos minimos de evidencia
- `<contradiction_handling>` — Manejo de fuentes contradictorias
- `<next_query_guidelines>` — Reglas para consultas de seguimiento

Ubicacion: `src/vigilancia_multiagente/prompts/`

## Graph Analytics
- Community detection: Leiden (NetworkX).
- Centrality metrics: degree, betweenness, PageRank.
- Shortest path: Dijkstra.
- Traversal: BFS and DFS.
- Semantic linking: embedding similarity for node relationship scoring.
- Bipartite projection for `related_to` edges.
- Tipos de nodo: SOURCE, FINDING, CONCEPT, TECHNOLOGY, PATENT.
- El sistema mantiene un grafo por sesion y aplica multiples algoritmos sobre la misma superficie.

## Key Entities
- **Sesion de Investigacion**: Contenedor principal de objetivo, alcance, estado y resultados.
- **Rama Especializada**: Unidad de analisis enfocada en un dominio (comercial, normativo, innovacion, riesgo o competitivo).
- **Hallazgo**: Insight relevante derivado del analisis de una rama.
- **Evidencia**: Fuente trazable que respalda un hallazgo.
- **Reporte Consolidado**: Documento final (FinalReport) que integra resultados y recomendaciones priorizadas.
- **Grafo de Conocimiento**: Estructura NetworkX por sesion que conecta hallazgos, evidencias y conceptos.
- **Nodo de Conocimiento**: SOURCE/FINDING/CONCEPT/TECHNOLOGY/PATENT.
- **SourceRef**: Referencia a fuente con URL, provider, confidence.
- **MCPProviderConfig**: Configuracion de proveedor MCP (HTTP o STDIO).

## Success Criteria
- **SC-001**: Al menos 90% de las sesiones iniciadas completan el ciclo de ejecucion y consolidacion de reporte.
- **SC-002**: Al menos 85% de los reportes incluyen cobertura valida en todas las ramas definidas para la sesion.
- **SC-003**: La mediana de tiempo desde inicio de sesion hasta reporte consolidado es menor a 20 minutos en investigaciones estandar.
- **SC-004**: Al menos 95% de las conclusiones del reporte final tienen evidencia trazable asociada.
- **SC-005**: Al menos 80% de usuarios confirma que el grafo de conocimiento facilita localizar rapidamente la evidencia de un hallazgo.
- **SC-006**: Al menos 75% de investigaciones generan minimo una oportunidad accionable y priorizada para decision de negocio.
- **SC-007**: 9+ proveedores MCP funcionales con soporte HTTP y STDIO.
- **SC-008**: 59+ tests unitarios pasando, 0 issues de Ruff.
- **SC-009**: 21 prompts con estructura HTML semantica y contenido en ingles.
