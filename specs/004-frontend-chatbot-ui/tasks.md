# Tasks: Frontend Chatbot UI — Vigilador Tecnológico

**Input**: `specs/004-frontend-chatbot-ui/spec.md`
**Feature**: Frontend SPA chatbot para lanzar investigaciones de vigilancia tecnológica, monitorear agentes en tiempo real, explorar grafo de conocimiento interactivo y visualizar reportes/métricas/recomendaciones.

**Stack**: Vite + React 18 + TypeScript strict + Tailwind CSS 4 + Zustand + D3.js 7

---

## Phase 1: Setup (Project Initialization)

**Goal**: Scaffold del proyecto Vite + React + TypeScript con todas las herramientas de desarrollo configuradas y la estructura de directorios lista.

- [X] T001 [P] Initialize Vite + React 18 + TypeScript project in `./` with `npm create vite@latest`
- [X] T002 [P] Configure TypeScript strict mode in `tsconfig.json` (strict: true, noUncheckedIndexedAccess, exactOptionalPropertyTypes)
- [X] T003 [P] ~~Configure Tailwind CSS 4+~~ → Sistema de diseño CSS propio "Atlas Científico" en `src/index.css` + `src/App.css` (tokens, paleta institucional Pantone 382/Cool Gray 5/Pantone 877, tipografía editorial Fraunces/Spectral/IBM Plex Mono). Tailwind descartado deliberadamente: CSS con tokens da más control para la estética de cuaderno de laboratorio.
- [ ] T004 [P] Configure ESLint with import rules (no-duplicates, order, no-cycle) in `eslint.config.js`
- [X] T005 [P] Add project dependencies: `zustand`, `d3@7`, `@types/d3` in `package.json`
- [ ] T006 [P] Create environment config: `VITE_API_BASE_URL` with default `http://localhost:8000/api/v2` in `.env.example` and `src/config.ts`
- [X] T007 [P] Configure path aliases `@/` pointing to `src/` in `vite.config.ts` and `tsconfig.json`
- [X] T008 Create project directory structure: `src/{types,api,state,components,chat,history,agents,analysis,graph}` with `index.ts` files

## Phase 2: Foundation (Types, API Client, Store, Base Components)

**Goal**: Establecer la base sobre la cual todos los módulos de UI se construyen: tipos compartidos, cliente API, store global, SSE client y componentes base reutilizables.

- [X] T009 Create shared TypeScript types in `src/types/index.ts`: Session, SessionStatus, BranchType enum, ChatMessage (discriminated union por type), ThinkingStep, BranchAgent, GraphNode, GraphEdge, GraphData, Source, Recommendation, ProviderMetric, SessionSummary, FinalReport
- [X] T010 Create generic HTTP client in `src/api/client.ts` with `apiGet<T>()`, `apiPost<T>()`, error handling, timeout via AbortController, and response type parsing
- [X] T011 Create API endpoint functions in `src/api/endpoints.ts`: `startResearch()`, `clarifySession()`, `getPlan()`, `approvePlan()`, `getReport()`, `getSources()`, `getGraph()`, `searchGraph()`, `getMetrics()`, `sendFollowUp()`
- [X] T012 Create SseClient class in `src/api/sse.ts`: `connect(sessionId)`, event handler mapping, auto-reconnect with exponential backoff (1s/2s/4s/8s/max 30s), `disconnect()`, connection status observable, heartbeat ignore
- [X] T013 Create Zustand store in `src/state/useStore.ts` with slices: session (sessions[], activeSessionId, sessionStatus), chat (messages[], addMessage), agents (Record<BranchType, BranchAgent>, updateAgent), report (report, setReport), graph (graphData, setGraphData), sse (connectionStatus). Persist activeSessionId and messages to localStorage.
- [X] T014 Create custom store hooks in `src/state/hooks.ts`: `useActiveSession()`, `useChatMessages()`, `useAgents()`, `useGraph()`, `useReport()`
- [X] T015 [P] Create reusable base components in `src/components/`: Button.tsx (primary/secondary/ghost), Input.tsx (with label/error), Spinner.tsx, Badge.tsx (success/warning/error/info), Modal.tsx (overlay+content), CollapsibleSection.tsx (expand/collapse with CSS transition), TabNav.tsx (generic tab navigation) + Icon.tsx (set SVG propio) + StateBlock.tsx (loading/empty/error reutilizable, FR-051)
- [X] T016 Create App.tsx with MainLayout (`src/MainLayout.tsx`): header (marca + ConnectionStatus), TabNav ([Chat] [Análisis]), conditional render of ChatView/AnalysisView

## Phase 3: US1 — Chat Core

**Story Goal**: El usuario puede escribir una consulta, recibir preguntas de clarificación con inputs integrados, ver el plan generado con botón de aprobar, y recibir el resumen ejecutivo al completarse la investigación.

**Independent Test Criteria**: 
- Al escribir una consulta y presionar Enter, se llama a POST /research/start
- Las preguntas de clarificación aparecen como mensajes del sistema con inputs
- Al responder, se llama a POST /research/{id}/clarify
- El plan aparece con botón "Aprobar" que llama a POST /research/{id}/approve
- El resumen ejecutivo se renderiza como mensaje del sistema al completarse

- [X] T017 [US1] Create ChatMessageItem component in `src/chat/ChatMessageItem.tsx` that renders different layouts based on `message.type`: user, system, event (compact timeline), plan (full-width block), report (styled summary), clarification
- [X] T018 [US1] Create ClarificationInput component in `src/chat/ClarificationInput.tsx` that renders each question with its text input and a submit button that fires onSubmit(answers)
- [X] T019 [US1] Create InputBar component in `src/chat/InputBar.tsx` with textarea and send button. Enter sends, Shift+Enter newlines. disabled prop for EXECUTING state.
- [X] T020 [US1] Create PlanBlock component in `src/chat/PlanBlock.tsx` wrapping PlanningChain (via thinkingChain slot) with "Aprobar" / "Modificar" buttons
- [X] T021 [US1] Create ReportSummary component in `src/chat/ReportSummary.tsx` that renders the executiveSummary from FinalReport with structured formatting + stats
- [X] T022 [US1] Create ChatPanel container in `src/chat/ChatPanel.tsx` using useChatMessages, auto-scroll via useRef+useEffect, rendering message list and InputBar
- [X] T023 [US1] Create chat store slice in `src/state/chatStore.ts`: messages array, addMessage(), addClarification(), clearMessages(), persist to localStorage

## Phase 4: US2 — Planning Chain & Agent Sidebar

**Story Goal**: El usuario puede expandir/colapsar la cadena de pensamiento del planner en el chat principal, y monitorear cada agente individualmente en una barra lateral navegable con tool calls, respuestas y progreso.

**Independent Test Criteria**:
- El bloque del planner se puede expandir/colapsar con un clic
- Cuando colapsado muestra texto resumen; expandido muestra pasos de razonamiento
- La barra lateral muestra un agente a la vez con navegacion izquierda/derecha
- La tira de estado muestra los 6 agentes con colores de estado
- Cada iteracion del agente se puede expandir/colapsar individualmente

- [X] T024 [P] [US2] Create PlanningChain collapsible component in `src/agents/PlanningChain.tsx` using CollapsibleSection. Collapsed: resumen "N ramas — listo para aprobar". Expanded: list of ThinkingStep items.
- [X] T025 [P] [US2] Create AgentStatusStrip component in `src/agents/AgentStatusStrip.tsx` showing all 6 agents with color-coded dial status (waiting/running/completed/failed via paleta institucional, sin emojis), highlighting selected agent
- [X] T026 [P] [US2] Create AgentIterationCard collapsible component in `src/agents/AgentIterationCard.tsx` showing query, tool used, response summary, confidence score per iteration
- [X] T027 [P] [US2] Create AgentDetailPanel in `src/agents/AgentDetailPanel.tsx` showing selected agent's name, status, iteration list, and progress indicator
- [X] T028 [US2] Create AgentSidebar container in `src/agents/AgentSidebar.tsx` integrating AgentStatusStrip + AgentDetailPanel with prev/next navigation buttons and hide/show toggle
- [X] T029 [US2] Create AgentProgressBar in `src/agents/AgentProgressBar.tsx` showing current/total iterations with CSS width transition
- [X] T030 [US2] Create agents store slice in `src/state/agentsStore.ts`: agents map, updateAgentStatus(), addIteration(), setAgentComplete(), setAgentFailed()
- [X] T031 [US2] Wire AgentSidebar into ChatView in `src/chat/ChatView.tsx`: render sidebar as right panel when visible, shrink chat area accordingly (toggle a lomo vertical "atlas-spine")

## Phase 5: US3 — SSE Streaming Integration

**Story Goal**: La aplicación recibe eventos SSE del backend en tiempo real y actualiza el store sin necesidad de recargar la página. La UI refleja instantáneamente el progreso de la investigación.

**Independent Test Criteria**:
- Al conectar SSE, los eventos BranchStarted/BranchCompleted actualizan la UI sin recarga
- Los tool calls de agentes aparecen en AgentSidebar a medida que llegan BranchProgress eventos
- Al desconectarse, el indicador de conexión cambia a "Reconectando..."
- La reconexion es automática y los eventos perdidos se recuperan
- Los heartbeats no afectan la UI

- [X] T032 [US3] Create SSE event handler map in `src/state/sseHandlers.ts`: pure functions mapping each SSE event type to store actions (SessionStarted, ClarificationRequested, PlanGenerated, BranchStarted, BranchProgress, BranchCompleted, BranchFailed, AllBranchesCompleted, FusionStarted, FusionProgress, ReportGenerated, GraphBuildingStarted, GraphAnalyticsComputed)
- [X] T033 [US3] Create useSSE hook in `src/chat/useSSE.ts` that instantiates SseClient on mount, connects handlers to store dispatches, exposes connectionStatus, cleans up on unmount
- [X] T034 [US3] Create ConnectionStatus indicator in `src/components/ConnectionStatus.tsx`: "Enlace activo" (beacon lima) / "Reconectando" / "Sin enlace" — colores CSS, sin emojis
- [X] T035 [US3] Integrate useSSE into ChatView in `src/chat/ChatView.tsx`: activate when session is in EXECUTING, deactivate on session change

## Phase 6: US4 — Analysis Tabs (Metrics & Recommendations)

**Story Goal**: El usuario puede cambiar a la pestaña Análisis y navegar entre sub-vistas de Métricas y Recomendaciones para explorar los resultados cuantitativos de la investigación.

**Independent Test Criteria**:
- Al hacer clic en Análisis, se muestran las sub-pestañas Grafo, Métricas, Recomendaciones
- Al cambiar de sub-pestaña, el contenido cambia sin recargar la página
- Las métricas muestran KPIs por rama y datos de proveedores
- Las recomendaciones aparecen agrupadas por prioridad

- [X] T036 [US4] Create AnalysisPanel component in `src/analysis/AnalysisPanel.tsx` with sub-tab navigation (Grafo, Métricas, Recomendaciones), preserving inactive tab content via CSS `hidden` toggle (no desmonta)
- [X] T037 [US4] Create MetricsTab in `src/analysis/MetricsTab.tsx`: summary cards (confidence, total sources, total findings), branch KPIs table, provider metrics table, with loading/error/empty states
- [X] T038 [US4] Create RecommendationsTab in `src/analysis/RecommendationsTab.tsx`: groups recommendations by priority (Alta/Media/Baja), cards with text, priority badge, evidence source links, with loading/empty/error states
- [X] T039 [US4] Create analysis store slice in `src/state/analysisStore.ts`: metricsData, recommendations, loading/error states, fetchMetrics(sessionId), fetchRecommendations(sessionId) actions

## Phase 7: US5 — Knowledge Graph Core

**Story Goal**: El usuario ve un grafo de conocimiento unificado estilo VOSviewer con nodos escalados por importancia, coloreados por rama de origen, etiquetas visibles y una leyenda explicativa.

**Independent Test Criteria**:
- El grafo se renderiza con layout force-directed (tendencia circular)
- Los nodos más importantes son visualmente más grandes
- Cada rama tiene un color distinto explicado en la leyenda
- Las etiquetas de los nodos son visibles
- Es un único grafo que relaciona conceptos entre ramas

- [X] T040 [P] [US5] Create graph utility functions in `src/graph/graphUtils.ts`: `mapCentralityToRadius()`, `getBranchColor()`, `getFontSize()`, `filterOverlappingLabels()`, `getBranchLabel()`, `buildAdjacency()` (hover highlight)
- [X] T041 [P] [US5] Create GraphNode SVG component in `src/graph/GraphNode.tsx` rendering circle (radius from centrality, fill from branch color) with text label, selected/dimmed states
- [X] T042 [P] [US5] Create GraphEdge SVG component in `src/graph/GraphEdge.tsx` rendering line between source/target with opacity/width from similarity score, path highlight
- [X] T043 [US5] Create GraphCanvas SVG container in `src/graph/GraphCanvas.tsx` with D3 forceSimulation, zoom/pan transform group, rendering GraphEdge + GraphNode lists
- [X] T044 [P] [US5] Create GraphLegend in `src/graph/GraphLegend.tsx` showing 6 branch colors with labels and node size scale (cartela de mapa)
- [X] T045 [US5] Create KnowledgeGraph container in `src/graph/KnowledgeGraph.tsx` with loading/empty/error/success states, rendering GraphCanvas + GraphLegend + SourcesPanel
- [X] T046 [US5] Create graph store slice in `src/state/graphStore.ts`: graphData, selectedNodeId, loading/error, fetchGraph(sessionId), setSelectedNode()
- [X] T047 [US5] Create GraphTab in `src/analysis/GraphTab.tsx` connecting KnowledgeGraph, auto-fetching graph+sources vía módulo `api/` (endpoint correcto `/research/{id}/graph`, FR-050) on mount

## Phase 8: US6 — History Bar & Layout

**Story Goal**: El usuario ve el historial de sesiones en una barra lateral, puede crear una nueva investigación, cambiar entre sesiones pasadas, y colapsar paneles según necesite.

**Independent Test Criteria**:
- La barra de historial muestra la lista de sesiones ordenadas por fecha
- Al hacer clic en una sesión, se carga su estado completo
- El boton "+ Nueva investigación" limpia el estado para empezar una nueva
- Los paneles (historial y agentes) se pueden colapsar/expandir
- Los estados de sesión se muestran con colores CSS

- [X] T048 [US6] Create HistoryBar component in `src/history/HistoryBar.tsx` listing SessionSummary items with click handler, "+" new session button, session status via CSS dot colors (sin emojis), collapsible toggle, with loading/empty/error states
- [X] T049 [US6] Create history store slice in `src/state/historyStore.ts`: sessions list, activeSessionId, fetchSessions(), selectSession(id) (clears previous state, loads new session data), newSession()
- [X] T050 [US6] Create ChatView in `src/chat/ChatView.tsx` integrating ChatPanel (center), HistoryBar (left, collapsible), AgentSidebar (right, collapsible), SSE hook managed by session state, orquesta start→clarify→approve vía módulo `api/`
- [X] T051 [US6] Create AnalysisView in `src/analysis/AnalysisView.tsx` rendering AnalysisPanel with HistoryBar (left)
- [X] T052 [US6] Create MainLayout in `src/MainLayout.tsx` (movido fuera de `components/` para no violar regla de dependencia FR-048): header marca + ConnectionStatus, TabNav switching ChatView/AnalysisView, HistoryBar como panel izquierdo colapsable

## Phase Final: Polish — Cross-Cutting & P2 Decoration

**Goal**: Interactividad avanzada del grafo (zoom, pan, drag, hover, click-nodo → fuentes), animaciones de UI, responsive design para pantallas estrechas.

- [X] T053 Add zoom (mouse wheel), pan (background drag), and node drag to GraphCanvas in `src/graph/GraphCanvas.tsx` using D3 zoom behavior and force simulation reheat (alphaTarget) on drag
- [X] T054 Add hover highlight to GraphCanvas: on node hover, dim non-connected nodes and edges via `buildAdjacency` in `src/graph/GraphCanvas.tsx`
- [X] T055 Create SourcesPanel in `src/graph/SourcesPanel.tsx`: opens on node click showing node name, linked sources (title, clickable URL, provider, branch), confidence score
- [ ] T056 Add shortest path visualization: node multi-select + "Ruta mas corta" button, call GET /research/{id}/graph/path, highlight path nodes/edges in `src/graph/GraphCanvas.tsx` — *fuera de scope de este pase de diseño; GraphCanvas ya acepta props `pathNodeIds`/`pathEdgeIds` para conectarlo después*
- [X] T057 Add responsive behavior: AgentSidebar overlay+backdrop <1024px; HistoryBar drawer overlay <768px (CSS en `src/App.css`, verificado en preview a 375px)
- [X] T058 Add CSS transitions for CollapsibleSection (grid-template-rows + opacity) and smooth tab/collapse transitions (`src/index.css` + `src/App.css`)
- [X] T059 [P] Add node click handler to GraphCanvas in `src/graph/GraphCanvas.tsx`: on node click, dispatch onSelectNode → KnowledgeGraph opens SourcesPanel
- [ ] T060 Add FR-051 audit doc — *pendiente: todos los componentes ya implementan loading/error/empty/success vía `StateBlock`, falta el doc `docs/audit-component-states.md`*

## Phase 10: Testing & Coverage

**Goal**: Garantizar que el código cumple SC-009 (cobertura >70%) con tests unitarios y de integración.

**Independent Test Criteria**:
- Vitest corre sin errores
- Cobertura combinada >70% (branches, functions, lines, statements)
- Todos los componentes principales tienen al menos un test de renderizado

- [X] T061 [P] Setup Vitest + React Testing Library + jsdom in `vitest.config.ts` with coverage reporter (lcov, text, html) and threshold set to 70%
- [ ] T062 [P] Write unit tests for pure functions and types in `src/types/__tests__/types.test.ts` and `src/graph/__tests__/graphUtils.test.ts`
- [ ] T063 [P] Write unit tests for store slices in `src/state/__tests__/chatStore.test.ts`, `src/state/__tests__/agentsStore.test.ts`, `src/state/__tests__/graphStore.test.ts`
- [ ] T064 [P] Write component render tests for base components in `src/components/__tests__/Button.test.tsx`, `src/components/__tests__/Spinner.test.tsx`, `src/components/__tests__/Badge.test.tsx`
- [ ] T065 [P] Write SSE client integration test in `src/api/__tests__/sse.test.ts`: mock EventSource, verify reconnect backoff, verify event dispatch
- [ ] T066 Verify coverage threshold in CI: add `npm run test -- --coverage` to CI pipeline and enforce >=70%

---

## Dependencies

### Phase Completion Order

```
Phase 1 (Setup)
     |
Phase 2 (Foundation)
     |
     +----------------+----------------+
     |                |                |
Phase 3 (Chat)   Phase 4 (Agents)  Phase 5 (SSE)
     |                |                |
     +----------------+----------------+
                          |
                    Phase 6 (Analysis)
                     /              \
               Phase 7 (Graph)   Phase 8 (History)
                      \              /
                    Phase 9 (Polish)
                          |
                   Phase 10 (Testing)
```

### Sequential Requirements
- Phase 1 must complete before Phase 2 (no types/api without project scaffold)
- Phase 2 must complete before Phase 3, 4, 5 (all UI modules depend on types, store, and components)
- Phase 6 depends on Phase 3+4+5 (analysis needs chat foundation, agents, and SSE pipeline)
- Phase 7 depends on Phase 6 (GraphTab is a sub-tab of AnalysisPanel)
- Phase 8 depends on Phase 3+4 (ChatView and AnalysisView need chat+agent components)
- Phase 9 must complete before Phase 10 (tests validate the complete implementation)
- Phase 10 is last (tests depend on all features being implemented first)

### Parallel Opportunities
- Within each phase, tasks marked with [P] are independent and can run in parallel
- Phase 1: T001-T007 are all parallel (different config files)
- Phase 2: T009 (types), T010 (client), T012 (SSE), T015 (components) parallel
- Phase 3: T017-T021 parallel (independent components)
- Phase 4: T024-T027 parallel, T030 parallel
- Phase 5: T032 (handlers) and T034 (indicator) parallel
- Phase 6: T037 (metrics), T038 (recommendations) parallel
- Phase 7: T040-T042 parallel (utility functions and leaf components)

## Parallel Execution Examples

### Phase 2 Parallel Block
Run T009, T010, T012, T015 in parallel (types, api client, sse client, base components — all different files).

### Phase 3 Parallel Block
Run T017, T018, T019, T020, T021 in parallel (ChatMessageItem, ClarificationInput, InputBar, PlanBlock, ReportSummary — all independent leaf components).

### Phase 7 Parallel Block
Run T040, T041, T042, T044 in parallel (graphUtils, GraphNode, GraphEdge, GraphLegend — no interdependencies).

## Implementation Strategy

1. **P0 First — Core Logic**: Ejecutar Phases 1-8 completas (T001-T052). Cada fase produce un incremento funcional testeable de forma independiente: al terminar Phase 3, el chat ya muestra mensajes; al terminar Phase 4, los agentes ya se ven en la sidebar.

2. **No saltos a P2**: Aunque algunas tareas P2 parezcan tentadoras (ej. animaciones del grafo), deben ignorarse hasta que todo P0 y P1 esté completo. La regla es: si la app funciona correctamente sin la decoración, la decoración va en Phase 9.

3. **Testing continuo**: Cada componente debe ser testeable de forma aislada (props in, JSX out). No esperar a Phase 9 para probar — probar cada Phase al completarla.

4. **Validación de módulos**: Despues de Phase 2, verificar que `madge` no encuentre dependencias circulares. Despues de cada fase, verificar que las reglas de importación (api/ no importa state/, state/ no importa UI) se mantengan.

5. **Testing en Phase 10**: Los tests se escriben AL FINAL (Phase 10) porque validan el producto completo. Sin embargo, cada componente debe diseñarse para ser testeable desde el inicio (props in, JSX out). No postergar decisiones de testabilidad.

6. **MVP Scope**: Las Phases 1-5 (T001-T035) constituyen el MVP funcional: el usuario puede lanzar una investigación, ver progreso en tiempo real, y recibir el reporte. Phases 6-8 añaden las vistas de análisis. Phase 9 es polish puro. Phase 10 añade garantía de calidad.
