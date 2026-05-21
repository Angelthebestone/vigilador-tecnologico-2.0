# Implementation Plan: Frontend Chatbot UI — Vigilador Tecnológico

## Problem

El backend multi-agente (spec 002) expone APIs REST + SSE para investigaciones de vigilancia tecnológica, pero no existe interfaz gráfica. Los usuarios deben lanzar consultas vía curl/Postman, monitorear progreso leyendo JSON, y no pueden explorar resultados visualmente (grafo, métricas, recomendaciones). Sin frontend, el sistema es inaccesible para usuarios no técnicos y limita la adopción.

## Approach

Construir una SPA (Single Page Application) con React 18 + TypeScript estricto como chatbot conversacional. La aplicación se conecta al backend existente vía REST y SSE, y se organiza en módulos independientes con dependencia unidireccional: `types/` → `api/` → `state/` → módulos de UI. El estado global se maneja con Zustand, los estilos con Tailwind CSS, y el grafo de conocimiento se renderiza con D3.js 7 (SVG + forceSimulation). La implementación sigue prioridades P0 (lógica pura) → P1 (UI esencial) → P2 (decoración).

---

## Technical Context

| Area | Decision | Rationale |
|------|----------|-----------|
| Framework | React 18 + TypeScript strict | Ecosistema maduro para SPAs complejas; tipado estático elimina `any` y permite refactors seguros |
| Build tool | Vite 6+ | HMR instantáneo, tree-shaking nativo, configuración cero para React+TS |
| State management | Zustand | API mínima (< 1KB), sin boilerplate, middleware de persistencia integrado, rendimiento predecible |
| Graph rendering | D3.js 7 (SVG + forceSimulation) | Única librería que ofrece control total sobre layout force-directed, escalado, colores e interactividad |
| Styling | Tailwind CSS 4+ | Utilidades atómicas evitan CSS monolítico; cada módulo tiene estilos auto-contenidos sin leakage |
| HTTP client | Fetch nativo + wrapper | Sin dependencias extra; AbortController para timeouts; tipado genérico en wrapper |
| SSE | EventSource nativo | API del browser estándar; sin dependencias; reconexión manual con backoff |
| Persistence | localStorage | Simple, síncrono, suficiente para sesión activa e historial de chats |
| Testing | Vitest + React Testing Library | Compatible con Vite nativamente; RTL para tests centrados en comportamiento del usuario |
| Module structure | `types/` → `api/` → `state/` → `{chat,agents,analysis,graph,history}/` + `components/` | Dependencia unidireccional; módulos hoja (types, components) sin dependencias de UI |
| Path aliases | `@/` → `src/` | Imports más legibles: `@/types` vs `../../types` |
| Linting | ESLint + import/no-cycle + madge | Previene dependencias circulares en CI |
| Error handling | try/catch por llamada API + estados loading/error/empty/success en cada componente | Sin errores silenciosos; el usuario siempre sabe qué pasa |

## External Constraints

| Constraint | Impact |
|------------|--------|
| Backend ya existe, NO modificable | El frontend debe consumir las APIs tal cual están; no se pueden agregar endpoints |
| No hay API key de MiniMax en backend | La síntesis de reportes usa plantillas Markdown; el frontend no puede esperar generación con LLM real |
| SSE es unidireccional (solo lectura) | El frontend no puede enviar comandos por SSE; las acciones (aprobar, modificar) van por REST aparte |
| Sin autenticación en backend | El frontend NO debe implementar login; las sesiones son identificadas por UUID y accesibles sin auth |
| Sin emojis en la UI | Todas las indicaciones visuales deben usar colores CSS, SVG icons o texto — prohibido el uso de emojis |

---

## Files to Create / Modify

### New Files

| File | Purpose |
|------|---------|
| `src/types/index.ts` | Tipos compartidos: Session, BranchType, ChatMessage, GraphNode, Source, Recommendation, etc. |
| `src/api/client.ts` | Cliente HTTP genérico con tipado, timeouts y manejo de errores |
| `src/api/endpoints.ts` | Funciones tipadas para cada endpoint REST del backend |
| `src/api/sse.ts` | Clase SseClient con reconexión automática y backoff exponencial |
| `src/state/useStore.ts` | Store global Zustand con slices de sesión, chat, agentes, reporte, grafo, SSE |
| `src/state/hooks.ts` | Hooks personalizados: useActiveSession, useChatMessages, useAgents, etc. |
| `src/state/sseHandlers.ts` | Mapa de handlers SSE → acciones del store |
| `src/state/chatStore.ts` | Slice de chat: mensajes, addMessage, persistencia |
| `src/state/agentsStore.ts` | Slice de agentes: estado, iteraciones, progreso |
| `src/state/analysisStore.ts` | Slice de análisis: métricas, recomendaciones, estados de carga |
| `src/state/graphStore.ts` | Slice de grafo: nodos, aristas, selección, fetch |
| `src/state/historyStore.ts` | Slice de historial: sesiones, activa, cambio de sesión |
| `src/components/Button.tsx` | Botón reutilizable con variantes (primary/secondary/ghost) |
| `src/components/Input.tsx` | Input reutilizable con label y estado de error |
| `src/components/Spinner.tsx` | Indicador de carga genérico |
| `src/components/Badge.tsx` | Badge de estado (success/warning/error/info) |
| `src/components/Modal.tsx` | Modal genérico con overlay y contenido |
| `src/components/CollapsibleSection.tsx` | Sección expandible/contraíble con CSS transition |
| `src/components/TabNav.tsx` | Navegación de pestañas genérica |
| `src/components/ConnectionStatus.tsx` | Indicador de conexión SSE (conectado/reconectando/desconectado) |
| `src/components/MainLayout.tsx` | Layout principal: header, tab nav, paneles colapsables |
| `src/chat/ChatMessageItem.tsx` | Mensaje individual del chat (renderizado por tipo) |
| `src/chat/ClarificationInput.tsx` | Inputs para preguntas de clarificación |
| `src/chat/InputBar.tsx` | Barra de entrada de texto fija en parte inferior |
| `src/chat/PlanBlock.tsx` | Bloque de plan con botón Aprobar |
| `src/chat/ReportSummary.tsx` | Resumen ejecutivo renderizado como mensaje |
| `src/chat/ChatPanel.tsx` | Contenedor del chat con scroll automático |
| `src/chat/ChatView.tsx` | Vista completa del chat (panel + sidebar + historial + SSE) |
| `src/agents/PlanningChain.tsx` | Cadena de pensamiento colapsable del planner |
| `src/agents/AgentStatusStrip.tsx` | Tira compacta con estado de 6 agentes |
| `src/agents/AgentIterationCard.tsx` | Iteración colapsable de un agente |
| `src/agents/AgentDetailPanel.tsx` | Detalle del agente seleccionado |
| `src/agents/AgentSidebar.tsx` | Barra lateral de agentes con navegación |
| `src/agents/AgentProgressBar.tsx` | Barra de progreso del agente |
| `src/analysis/AnalysisPanel.tsx` | Panel de análisis con sub-pestañas |
| `src/analysis/MetricsTab.tsx` | Tab de métricas (KPIs, proveedores) |
| `src/analysis/RecommendationsTab.tsx` | Tab de recomendaciones agrupadas |
| `src/analysis/GraphTab.tsx` | Tab del grafo (wrapper de KnowledgeGraph) |
| `src/analysis/AnalysisView.tsx` | Vista completa de análisis |
| `src/graph/graphUtils.ts` | Funciones puras D3 (radio, color, layout, filtrado) |
| `src/graph/GraphNode.tsx` | Componente SVG de nodo |
| `src/graph/GraphEdge.tsx` | Componente SVG de arista |
| `src/graph/GraphCanvas.tsx` | Contenedor SVG con D3 forceSimulation |
| `src/graph/GraphLegend.tsx` | Leyenda de colores y tamaños |
| `src/graph/KnowledgeGraph.tsx` | Contenedor con estados loading/empty/error/success |
| `src/graph/SourcesPanel.tsx` | Panel de fuentes al hacer clic en nodo |
| `src/history/HistoryBar.tsx` | Barra lateral de historial de sesiones |

### Modified Files

Ninguno. Es un proyecto nuevo desde cero.

---

## Constitution Check (Pre-Design)

- **Gate result**: PASS
- **Alignment**:
  - **Pensar Antes de Codificar**: Este plan documenta explícitamente decisiones de arquitectura (stack, módulos, data flow) y trade-offs (por qué Zustand y no Redux, por qué D3 y no vis.js, por qué Vite y no CRA). Todas las asunciones están declaradas en Technical Context.
  - **Simplicidad Obligatoria**: Sin abstracciones innecesarias. Zustand (<1KB) en vez de Redux. Fetch nativo envuelto en 2 funciones en vez de axios/ky. Sin HOCs, sin render props, sin middleware complejo. Cada componente <300 líneas.
  - **Modularidad Primero**: 9 módulos con dependencia unidireccional estricta (FR-048). `types/` y `components/` son hojas; `api/` no importa UI; `state/` no importa componentes. Los componentes de UI reciben datos por props, no importan el store.
  - **Cambios Quirurgicos y Trazables**: Cada módulo tiene responsabilidad única. Cada cambio se limita a un módulo. No se tocan archivos fuera del alcance.
  - **Entrega Verificable**: Cada fase del plan tiene criterios de éxito independientes y verificables. Las tasks tienen file paths exactos y story labels.

---

## Phases

### Phase 1 — Setup (Project Init)

1. Scaffold Vite + React 18 + TypeScript strict
2. Configure Tailwind CSS 4+, ESLint, path aliases (`@/` → `src/`)
3. Create directory structure: `src/{types,api,state,components,chat,history,agents,analysis,graph}`
4. Add dependencies: zustand, d3@7, @types/d3, vitest, @testing-library/react

**Output**: `package.json`, `vite.config.ts`, `tsconfig.json`, `tailwind.config.ts`, `eslint.config.js`, `.env.example`, `src/index.css`, `src/config.ts`

### Phase 2 — Foundation

1. Create shared types: Session, BranchType, ChatMessage, ThinkingStep, BranchAgent, GraphNode/Edge, Source, Recommendation
2. Create HTTP client wrapper y endpoint functions para todas las APIs
3. Create SseClient with auto-reconnect and exponential backoff
4. Create Zustand store with slices (session, chat, agents, report, graph, SSE, history)
5. Create base components: Button, Input, Spinner, Badge, Modal, CollapsibleSection, TabNav
6. Create MainLayout stub with TabNav (Chat | Analisis)

**Output**: `src/types/`, `src/api/`, `src/state/`, `src/components/`

### Phase 3 — Chat Core (US1)

1. Implement ChatMessageItem (renderizado por tipo: user/system/event/plan/report/clarification)
2. Implement ClarificationInput, InputBar, PlanBlock, ReportSummary
3. Implement ChatPanel con scroll automático
4. Implement chatStore slice con persistencia localStorage
5. Wire ChatView en MainLayout

**Output**: `src/chat/`, `src/state/chatStore.ts`

### Phase 4 — Planning & Agent Sidebar (US2)

1. Implement PlanningChain colapsable (CollapsibleSection wrapper)
2. Implement AgentStatusStrip (6 agentes con colores de estado)
3. Implement AgentIterationCard, AgentDetailPanel, AgentProgressBar
4. Implement AgentSidebar con navegación prev/next y toggle
5. Implement agentsStore slice
6. Wire AgentSidebar en ChatView

**Output**: `src/agents/`, `src/state/agentsStore.ts`

### Phase 5 — SSE Integration (US3)

1. Implement sseHandlers.ts (mapa de eventos SSE → acciones store)
2. Implement useSSE hook (lifecycle del SseClient)
3. Implement ConnectionStatus indicator
4. Integrar useSSE en ChatView (activo durante EXECUTING)

**Output**: `src/state/sseHandlers.ts`, `src/chat/useSSE.ts`, `src/components/ConnectionStatus.tsx`

### Phase 6 — Analysis Tabs (US4)

1. Implement AnalysisPanel con sub-tab routing (Grafo, Metricas, Recomendaciones)
2. Implement MetricsTab (KPIs, proveedores, loading/error/empty)
3. Implement RecommendationsTab (agrupadas por prioridad)
4. Implement analysisStore slice

**Output**: `src/analysis/`, `src/state/analysisStore.ts`

### Phase 7 — Knowledge Graph (US5)

1. Implement graphUtils: mapCentralityToRadius, getBranchColor, buildForceLayout
2. Implement GraphNode, GraphEdge (componentes SVG)
3. Implement GraphCanvas con D3 forceSimulation
4. Implement GraphLegend, KnowledgeGraph container, GraphTab
5. Implement graphStore slice

**Output**: `src/graph/`, `src/state/graphStore.ts`, `src/analysis/GraphTab.tsx`

### Phase 8 — History & Layout (US6)

1. Implement HistoryBar con lista de sesiones y boton "+"
2. Implement historyStore con selectSession, newSession
3. Implement ChatView completo (integra ChatPanel + AgentSidebar + HistoryBar + SSE)
4. Implement AnalysisView (integrates AnalysisPanel + HistoryBar)
5. Implement MainLayout final con tab switching

**Output**: `src/history/`, `src/state/historyStore.ts`, `src/chat/ChatView.tsx`, `src/analysis/AnalysisView.tsx`, `src/components/MainLayout.tsx`

### Phase 9 — Polish & Testing

1. Add graph interactions: zoom, pan, node drag, hover highlight, path visualization
2. Add SourcesPanel on node click
3. Add CSS transitions: collapsible sections, tab switches
4. Add responsive: AgentSidebar overlay <1024px, HistoryBar drawer <768px
5. Add unit tests per module (Vitest + RTL, coverage >70%)
6. Add integration tests: SSE client, store persistence

**Output**: Tests en `src/**/__tests__/`, mejoras de interactividad y responsive

---

## Rollout Strategy

1. **MVP (Phases 1-5)**: Usuario puede lanzar investigación, ver progreso SSE en tiempo real en chat+sidebar, y recibir reporte. Esto solo requiere backend funcionando.
2. **Análisis (Phases 6-8)**: Se añaden las vistas de métricas, recomendaciones, grafo e historial. El MVP sigue funcionando sin cambios.
3. **Polish (Phase 9)**: Interactividad avanzada del grafo, animaciones, responsive, y tests de cobertura. No cambia APIs ni flujos.

Cada fase es un incremento funcional completo y desplegable independientemente. No se requiere feature flagging porque el frontend se despliega completo; las fases son solo orden de implementación.

---

## Success Criteria

- **SC-001**: Usuario lanza investigación en ≤3 clics desde la UI (sin curl/Postman)
- **SC-002**: Eventos SSE se reflejan en UI en <500ms desde emisión
- **SC-003**: Grafo con 200 nodos renderiza en <3s
- **SC-004**: Navegación entre agentes en sidebar <100ms
- **SC-005**: Chat persiste entre recargas de página (restaurado en <1s)
- **SC-006**: Transiciones entre tabs son instantáneas (<200ms)
- **SC-007**: Grafo interactivo: zoom, pan, clic en nodo responden en <100ms
- **SC-008**: SSE reconecta automáticamente en <30s tras desconexión
- **SC-009**: Cobertura de tests >70% con Vitest + RTL

## Constitution Check (Post-Design)

- **Status**: PASS
- **Justification**: El plan divide la implementación en 9 fases incrementales donde cada fase produce un resultado verificable. La estructura de módulos con dependencia unidireccional satisface Modularidad Primero. La regla P0→P1→P2 asegura que no se invierte tiempo en decoración antes de tener lógica funcional. Las decisiones de stack están justificadas y no hay sobreingeniería (Zustand y no Redux, fetch nativo y no axios, D3 directo y no vis.js).
