# Feature Specification: Frontend Chatbot UI — Vigilador Tecnológico

## Problem Statement

El backend multi-agente de vigilancia tecnológica es completamente funcional (API REST + SSE streaming, 6 agentes especializados, grafo de conocimiento, síntesis de reportes), pero carece de una interfaz gráfica de usuario. Los investigadores y tomadores de decisiones necesitan un frontend intuitivo tipo chatbot para:

- Lanzar investigaciones y responder preguntas de clarificación
- Monitorear en **tiempo real** la ejecución de los agentes (cadena de pensamiento del planner + tool calls de cada agente)
- Visualizar resultados: resumen ejecutivo, reporte completo, grafo de conocimiento interactivo, métricas y recomendaciones
- Reanudar sesiones históricas y hacer preguntas de seguimiento post-investigación

Sin esta interfaz, el sistema solo es accesible vía API, lo que limita su adopción por parte de usuarios no técnicos y dificulta la exploración visual de los hallazgos.

## Scope Boundaries

### In Scope

- Aplicación web SPA (Single Page Application) con arquitectura modular por funcionalidad
- Interfaz tipo chatbot con dos pestañas principales: **Chat** y **Análisis**
- **Barra lateral de historial** de sesiones de investigación, con capacidad de crear nueva, seleccionar, renombrar y eliminar sesiones
- Visualización en tiempo real del progreso de la investigación vía SSE (Server-Sent Events)
- **Cadena de pensamiento del planner** en el área de chat principal, colapsable/expandible (estilo ChatGPT/Claude)
- **Barra lateral de agentes** (independiente del historial) que muestra la cadena de pensamiento de cada agente individual: tool calls, queries, respuestas, hallazgos intermedios, nivel de confianza
- Navegación entre agentes mediante flechas (anterior/siguiente) en la barra lateral
- **Resumen ejecutivo** renderizado como mensaje del sistema en el chat
- **Input bar** para continuar la conversación post-investigación
- Pestaña de **Análisis** con sub-pestañas: **Grafo**, **Métricas**, **Recomendaciones**
- **Grafo de conocimiento interactivo** tipo VOSviewer: diseño circular/force-directed, nodos escalados por frecuencia/importancia, etiquetas visibles, colores por categoría (rama de origen)
- Panel de fuentes al hacer clic en un nodo del grafo
- Persistencia de estado local (sesión activa, histórico de sesiones)
- Diseño responsivo adaptable a escritorio y tablet

### Out of Scope

- Autenticación y autorización de usuarios (será un feature separado)
- Soporte multi-idioma (fase futura)
- Aplicaciones móviles nativas (solo web responsiva)
- Modificación del backend API (cambios en spec 002)
- Notificaciones push o email
- Modo offline completo (requiere conexión al backend)
- Personalización de temas más allá de claro/oscuro

## Assumptions

1. **Stack tecnológico**: Se asume React 18+ con TypeScript como framework principal, por su ecosistema maduro para SPAs complejas, tipado estático y facilidad de modularización.
2. **Grafo**: Se asume D3.js (versión 7+) para la visualización del grafo, por ser el estándar de la industria para grafos interactivos con control total sobre escalado, color y layout force-directed.
3. **Estilos**: Se asume Tailwind CSS 4+ para el sistema de diseño, por sus utilidades atómicas que facilitan la modularización y consistencia visual.
4. **Estado global**: Se asume Zustand o Context API para manejo de estado, por su simplicidad y rendimiento frente a alternativas más pesadas.
5. **API base**: El backend corre en la misma URL de origen o se configura vía variable de entorno `VITE_API_BASE_URL`.
6. **SSE**: El navegador soporta `EventSource` nativo. En caso de corte, se implementa reconexión automática con backoff exponencial.
7. **Dispositivos**: La resolución objetivo mínima es 1024×768 para escritorio y 375×667 para móvil.
8. **Sesiones**: El backend no tiene eliminación automática de sesiones; el frontend asume que las sesiones persisten indefinidamente en el backend.

## User Scenarios & Testing

### Primary User Story: Investigación completa

> **Como** analista de tecnología,
> **Quiero** lanzar una investigación sobre computación cuántica en finanzas desde un chat,
> **Para** recibir un análisis completo con visualizaciones y poder hacer preguntas de seguimiento.

**Flujo primario:**

1. El usuario abre la aplicación y ve la barra de historial a la izquierda con una lista de sesiones anteriores vacía y un botón "+ Nueva investigación"
2. Hace clic en "+ Nueva investigación", escribe "analizar computación cuántica en finanzas" y presiona Enter
3. El sistema responde con preguntas de clarificación (horizonte temporal, alcance geográfico)
4. El usuario responde las preguntas en el chat
5. Aparece el plan generado con las 6 ramas, con la cadena de pensamiento del planner en un bloque colapsable
6. El usuario revisa el plan y hace clic en "Aprobar" dentro del chat
7. La investigación se ejecuta: la barra lateral de agentes muestra en tiempo real el progreso de cada agente, navegable con flechas
8. En el chat principal aparecen eventos de progreso (agente X completado, etc.)
9. Al completarse, el resumen ejecutivo aparece en el chat
10. El usuario puede hacer preguntas de seguimiento ("¿qué startups menciona?")
11. El usuario cambia a la pestaña Análisis, explora el grafo interactivo, hace clic en un nodo y ve las fuentes relacionadas
12. El usuario cambia a la sub-pestaña Recomendaciones y revisa las acciones priorizadas

### Acceptance Scenarios

1. **Inicio de investigación**: **Given** el usuario en la pantalla principal, **When** escribe una consulta y presiona Enter, **Then** se crea una sesión vía `POST /research/start` y se muestran las preguntas de clarificación en el chat.

2. **Cadena de pensamiento del planner**: **Given** una investigación en estado PLANNING, **When** el plan se genera, **Then** aparece un bloque colapsable en el chat con la etiqueta "[Plan]" y el texto "Plan generado — 6 ramas" que al expandirse muestra el razonamiento completo del planner.

3. **Barra lateral de agentes**: **Given** una investigación en estado EXECUTING, **When** el usuario abre la barra lateral de agentes, **Then** ve un agente a la vez con sus tool calls y puede navegar entre los 6 usando flechas (anterior/siguiente).

4. **Streaming en tiempo real**: **Given** una investigación ejecutándose, **When** el backend emite eventos SSE, **Then** el chat principal y la barra lateral se actualizan sin necesidad de recargar la página.

5. **Grafo interactivo**: **Given** una investigación completada, **When** el usuario navega a Análisis > Grafo, **Then** ve un grafo circular con nodos de diferentes tamaños y colores, etiquetas visibles, y puede hacer clic en un nodo para ver sus fuentes asociadas.

6. **Historial de sesiones**: **Given** múltiples investigaciones realizadas, **When** el usuario hace clic en una sesión anterior en la barra de historial, **Then** se carga el estado completo de esa sesión (chat, reporte, grafo).

7. **Continuar conversación**: **Given** una investigación completada, **When** el usuario escribe un mensaje de seguimiento en el input bar, **Then** el mensaje aparece en el historial del chat.

### Edge Cases

- **Error de red durante SSE**: Se implementa reconexión automática con backoff exponencial (1s, 2s, 4s, max 30s). Se muestra indicador de "reconectando..." al usuario.
- **Sesión fallida**: Si la investigación termina en estado FAILED, se muestra un mensaje de error en el chat con el código y mensaje de error del backend. Los resultados parciales (si existen) siguen siendo accesibles.
- **Grafo vacío**: Si una investigación no genera hallazgos, el grafo muestra un mensaje "No se encontraron hallazgos para esta investigación" en lugar de un canvas vacío.
- **Múltiples pestañas**: Si el usuario abre la misma sesión en dos pestañas, cada pestaña mantiene su propio estado SSE independiente.
- **Sesión no encontrada**: Si el usuario hace clic en una sesión del historial que ya no existe en el backend, se muestra un mensaje "Sesión no disponible" y se elimina del historial local.
- **Reconexión después de inactividad**: Si el usuario deja la pestaña inactiva y vuelve, el SSE se reconecta y sincroniza el estado actual.
- **Input deshabilitado durante ejecución**: El input bar permanece funcional para preguntas, pero las acciones de control (aprobar/modificar plan) se deshabilitan mientras la investigación está en EXECUTING.

## Implementation Priorities

Los requerimientos se organizan en 3 niveles de prioridad que definen el orden de implementación:

| Prioridad | Enfoque | Incluye |
|-----------|---------|---------|
| **P0 — Core Logic** | Escribir primero | Estado global, API client, stores, flujos de datos, tipos, lógica de componentes sin decoración |
| **P1 — Essential UI** | Después de P0 | Layout básico, estructura HTML semántica, posicionamiento de paneles, indicadores de estado funcionales |
| **P2 — Decoration** | Al final | Transiciones animadas, sombras, bordes redondeados, hover effects, responsive refinements, polish visual |

> **Regla**: Ningún requerimiento P2 debe implementarse hasta que todo P0 y P1 esté completo y testeado. Esto asegura que la lógica funcional sea sólida antes de invertir tiempo en estética.

---

## Functional Requirements

### Módulo: Historial de Sesiones

- **FR-001** [P0]: La aplicación debe mantener una lista en memoria de todas las sesiones de investigación, cargada desde el backend o desde localStorage, ordenada por fecha de creación descendente.
- **FR-002** [P0]: Cada entrada en el historial debe ser un objeto con: id, nombre/resumen de la consulta, fecha, y estado. Debe existir un tipo TypeScript SessionSummary que modele estos datos.
- **FR-003** [P0]: Al hacer clic en una sesión del historial, debe dispararse un cambio de sesión activa en el store global, que propague la carga de datos (chat, reporte, grafo, métricas) desde la API.
- **FR-004** [P0]: Debe existir un botón "+ Nueva investigación" cuya acción sea limpiar el estado de la sesión activa y permitir escribir una nueva consulta.
- **FR-005** [P1]: La barra de historial debe poder colapsarse a un icono de menú (hamburguesa) para maximizar el espacio de contenido.
- **FR-006** [P1]: Las sesiones en la barra de historial deben mostrar un indicador visual de estado mediante colores CSS (verde = completada, amarillo = en progreso, rojo = fallida), sin usar emojis.

### Módulo: Chat Principal

- **FR-007** [P0]: El componente ChatPanel debe renderizar una lista ordenada de mensajes desde un array en el store. Debe hacer scroll automático al último mensaje cuando se agregue uno nuevo.
- **FR-008** [P1]: Los mensajes del usuario deben alinearse a la derecha; los mensajes del sistema (asistente) alineados a la izquierda, con estilos visualmente diferenciados mediante clases CSS distintas.
- **FR-009** [P0]: Debe haber un componente InputBar fijo en la parte inferior, con un campo de texto y un botón de envío. Al presionar Enter o hacer clic en enviar, debe despachar la acción al store.
- **FR-010** [P0]: El ChatPanel debe ser capaz de renderizar diferentes tipos de mensaje: texto del usuario, preguntas de clarificación con inputs integrados, bloque de plan, eventos de progreso, y resumen ejecutivo. Cada tipo debe ser un componente React independiente.
- **FR-011** [P0]: Los mensajes del sistema que requieren acción (ej. aprobar plan) deben incluir botones de acción que disparen llamadas API (POST /research/{id}/approve).
- **FR-012** [P0]: El historial de mensajes de la sesión activa debe persistirse en localStorage y restaurarse al recargar la página.

### Módulo: Cadena de Pensamiento del Planner

- **FR-013** [P0]: Debe existir un componente PlanningChain que reciba un array de pasos de razonamiento (tipo ThinkingStep) y los renderice como una lista. Debe tener estado interno de colapsado/expandido.
- **FR-014** [P1]: Cuando está colapsado, debe mostrar una línea resumen: indicador SVG + "Plan generado — N ramas" + estado (listo para aprobar).
- **FR-015** [P0]: Al expandirse, debe mostrar el razonamiento paso a paso del planner: análisis de la consulta, desglose en ramas, justificación de proveedores MCP asignados, y estimación de profundidad.
- **FR-016** [P2]: La transición de colapsado a expandido debe ser animada (transición suave de altura máxima).

### Módulo: Barra Lateral de Agentes

- **FR-017** [P0]: Debe existir un componente AgentSidebar que reciba el estado de los 6 agentes desde el store y se renderice como panel acoplado al layout.
- **FR-018** [P0]: El componente debe mantener un estado interno de "agente seleccionado" (índice 0-5). Debe tener botones "anterior" y "siguiente" que cambien el índice.
- **FR-019** [P1]: En la parte superior de la barra debe haber una tira compacta que muestre los 6 agentes con su estado actual (waiting, running, completed, failed), indicado mediante colores CSS distintos.
- **FR-020** [P0]: Para el agente seleccionado, la barra debe renderizar:
  - Nombre del agente y su estado actual
  - Lista de iteraciones realizadas (cada una colapsable mediante estado local)
  - Por cada iteración: query enviada, tool usada, respuesta/resumen recibido, nivel de confianza, y si generó una query de seguimiento
  - Indicador de progreso mientras el agente está ejecutando
- **FR-021** [P1]: La barra lateral de agentes debe poder ocultarse/mostrarse mediante un botón de toggle.
- **FR-022** [P2]: En pantallas estrechas (< 1024px), la barra lateral debe convertirse en un panel deslizable (overlay) o bottom sheet.

### Módulo: Streaming en Tiempo Real (SSE)

- **FR-023** [P0]: Debe existir un servicio/class SseClient que consuma `GET /research/{id}/stream` usando `EventSource`. Debe mapear cada tipo de evento SSE a un dispatch en el store.
- **FR-024** [P0]: Los siguientes eventos SSE deben tener representación en el store y disparar actualizaciones en los componentes correspondientes:
  - `SessionStarted` → inicializar sesión en store
  - `ClarificationRequested` → agregar mensaje de clarificación al chat
  - `PlanGenerated` → almacenar plan en store, agregar bloque al chat
  - `BranchStarted` → actualizar estado del agente a "running" en store
  - `BranchProgress` → agregar iteración al agente correspondiente en store
  - `BranchCompleted` → marcar agente como "completed" en store, agregar notificación al chat
  - `BranchFailed` → marcar agente como "failed" en store, agregar mensaje de error
  - `AllBranchesCompleted` → agregar mensaje de consolidación al chat
  - `FusionStarted` / `FusionProgress` → actualizar indicador de progreso en store
  - `ReportGenerated` → almacenar reporte en store, mostrar resumen ejecutivo en chat
  - `GraphBuildingStarted` / `GraphAnalyticsComputed` → marcar datos de grafo como disponibles en store
- **FR-025** [P0]: El SseClient debe implementar reconexión automática con backoff exponencial (1s, 2s, 4s, 8s, max 30s). El estado de conexión debe exponerse en el store para que la UI pueda mostrar un indicador "Reconectando...".
- **FR-026** [P0]: El SseClient debe ignorar heartbeats (keep-alive) sin dispatchear eventos al store.

### Módulo: Pestaña de Análisis

- **FR-027** [P0]: Debe existir un componente AnalysisPanel con un sistema de tabs interno. Cada tab (Grafo, Métricas, Recomendaciones) debe ser un componente independiente que se renderiza condicionalmente según el tab activo.
- **FR-028** [P0]: Al cambiar de tab, el estado de los tabs anteriores debe mantenerse en el store (no desmontar, solo ocultar via CSS display).
- **FR-029** [P1]: Cada tab debe cargar sus datos del store. Si los datos no existen, debe disparar la llamada API correspondiente y mostrar un indicador de carga mientras se obtienen.

### Módulo: Grafo de Conocimiento (Sub-pestaña)

- **FR-030** [P0]: Debe existir un componente KnowledgeGraph que reciba nodos y aristas desde el store y los renderice en un elemento SVG o Canvas con layout force-directed.
- **FR-031** [P0]: Cada nodo debe tener un radio proporcional a su score de centralidad. La escala debe calcularse en una función pura: `mapCentralityToRadius(score: number, min: number, max: number): number`.
- **FR-032** [P1]: Los nodos deben ser coloreados según su rama de origen (Avances, Comercial, Riesgo, PI_Normativa, Competitivo, Oportunidades). Debe existir una función `getBranchColor(branch: BranchType): string` que devuelva el color asignado.
- **FR-033** [P1]: Todos los nodos deben mostrar su etiqueta (label) permanentemente visible como texto SVG. El tamaño de fuente debe escalar proporcionalmente al radio del nodo. En caso de solapamiento extremo, las etiquetas menos importantes pueden ocultarse.
- **FR-034** [P2]: El usuario debe poder:
  - Hacer zoom (rueda del ratón o gesto pinch) → transformar el grupo SVG
  - Arrastrar el canvas para panear → modificar translate del grupo SVG
  - Arrastrar nodos individuales para reajustar el layout → actualizar posición en el store
  - Hacer clic en un nodo para seleccionarlo → disparar evento de selección en store
  - Hover sobre un nodo para resaltar sus conexiones directas → actualizar estado visual en SVG
- **FR-035** [P2]: Al hacer clic en un nodo, debe abrirse un panel lateral o modal que muestre:
  - Nombre del nodo (concepto/hallazgo)
  - Lista de fuentes asociadas: título, URL (enlace clicable), proveedor, rama de origen
  - Score de confianza
- **FR-036** [P0]: El grafo debe ser un único grafo unificado que relacione todos los conceptos entre ramas. Las aristas representan relaciones semánticas entre hallazgos. No debe haber grafos separados por agente.
- **FR-037** [P1]: Una leyenda visible debe explicar el significado de los colores por rama y el rango de tamaños de nodos.
- **FR-038** [P0]: El grafo debe obtener sus datos del endpoint `GET /research/{id}/graph`. Debe existir una función `fetchGraph(sessionId: string): Promise<GraphData>` en el módulo api/.
- **FR-039** [P2]: El usuario debe poder seleccionar dos nodos y solicitar la ruta más corta entre ellos, visualizándola resaltada en el grafo.

### Módulo: Métricas (Sub-pestaña)

- **FR-040** [P0]: Debe existir un componente MetricsPanel que reciba desde el store y muestre:
  - KPIs por rama (coverage, precision, latency, cost)
  - Métricas agregadas de proveedores MCP (latencia promedio, tasa de error, tasa de retry)
  - Score de confianza general de la investigación
  - Conteo total de fuentes consultadas y hallazgos generados
- **FR-041** [P1]: Las métricas deben presentarse en una combinación de tarjetas resumen, tablas y gráficos de barras simples.

### Módulo: Recomendaciones (Sub-pestaña)

- **FR-042** [P0]: Debe existir un componente RecommendationsPanel que reciba desde el store la lista de recomendaciones del reporte final, agrupadas por nivel de prioridad (Alta, Media, Baja).
- **FR-043** [P0]: Cada recomendación debe incluir en su tipo: texto de la acción, prioridad, y citas de las fuentes/evidencias que la sustentan.
- **FR-044** [P1]: Las recomendaciones deben presentarse en tarjetas visualmente agrupadas por nivel de prioridad.

### Módulo: Estado Global y Persistencia

- **FR-045** [P0]: Debe existir un store global (Zustand o Context) que contenga: lista de sesiones, sesión activa, estado de la sesión activa, historial de mensajes del chat, datos del grafo (si ya se cargaron), estado de los 6 agentes, reporte final.
- **FR-046** [P0]: El store debe tener un middleware o suscripción que persista estado seleccionado en localStorage: sesión activa, historial de mensajes, lista de sesiones. Al cargar la app, debe restaurarse desde localStorage.
- **FR-047** [P0]: Al cambiar de sesión activa, el store debe limpiar el estado previo y disparar la carga de datos de la nueva sesión desde la API.

### Módulo: Arquitectura y Calidad

- **FR-048** [P0]: El código fuente debe organizarse en módulos con responsabilidad única. Cada módulo debe tener un `index.ts` que exporte su API pública y mantener detalles internos privados:

  ```
  src/
  ├── types/          # Tipos compartidos (sin dependencias)
  ├── api/            # Cliente HTTP + SSE (depende solo de types/)
  ├── state/          # Store global, slices, hooks (depende de types/, api/)
  ├── components/     # Componentes atómicos reutilizables (depende solo de types/)
  ├── chat/           # Chat principal (depende de state/, components/, types/)
  ├── history/        # Barra de historial (depende de state/, components/, types/)
  ├── agents/         # Barra lateral de agentes (depende de state/, components/, types/)
  ├── analysis/       # Pestaña de análisis + layout de sub-tabs (depende de state/, components/, graph/, types/)
  └── graph/          # Grafo de conocimiento SVG/Canvas (depende de state/, components/, api/, types/)
  ```

  **Reglas de dependencia**:
  - `types/` y `components/` son módulos hoja — ningún otro módulo puede depender de `chat/`, `history/`, etc.
  - `api/` no puede importar de `state/` ni de ningún módulo de UI
  - `state/` no puede importar de `components/` ni de ningún módulo de UI
  - Prohibidas las dependencias circulares (herramienta `madge` o similar debe pasar en CI)
  - Cada módulo debe poder ser testeado de forma aislada: los módulos de UI reciben datos por props, no importan el store directamente
- **FR-049** [P0]: Cada módulo funcional (chat, history, agents, analysis, graph) debe ser independientemente testeable. Los componentes deben recibir datos y callbacks por props; el store se inyecta en el nivel superior del árbol, no en componentes internos.
- **FR-050** [P0]: Todas las llamadas API deben centralizarse en el módulo `api/` con un cliente genérico que maneje errores, timeouts, cancelación de requests y parseo de respuestas. Ningún otro módulo puede hacer fetch/http directo.
- **FR-051** [P0]: Todos los componentes deben tener manejo explícito de estados: **loading**, **error**, **empty**, **success**.

## Key Entities

- **Session (Sesión de Investigación)**: Representa una investigación individual con su query, estado actual, plan, resultados y reporte. Identificada por UUID. Transiciona por estados: DRAFT → CLARIFYING → PLANNING → APPROVED → EXECUTING → COMPLETED/FAILED.
- **ChatMessage (Mensaje de Chat)**: Una entrada en el historial conversacional. Puede ser de tipo: `user` (mensaje del usuario), `system` (respuesta del asistente), `event` (evento de progreso), `plan` (bloque de plan), `report` (resumen ejecutivo), `clarification` (pregunta de clarificación con inputs).
- **ThinkingChain (Cadena de Pensamiento)**: Secuencia de pasos de razonamiento generados por el planner o un agente. Incluye: paso de razonamiento, tool call (si aplica), resultado intermedio, y nivel de confianza.
- **BranchAgent (Agente de Rama)**: Uno de los 6 investigadores especializados (Avances, Comercial, Riesgo, PI_Normativa, Competitivo, Oportunidades). Cada uno tiene: estado actual, iteraciones ejecutadas, tool calls realizadas y hallazgos encontrados.
- **GraphNode (Nodo del Grafo)**: Un concepto o hallazgo representado como nodo en el grafo de conocimiento. Atributos: id, label, tamaño (score de centralidad), color (rama de origen), fuentes asociadas, conexiones a otros nodos.
- **GraphEdge (Arista del Grafo)**: Relación semántica entre dos nodos. Atributos: nodo origen, nodo destino, tipo de relación, score de similitud.
- **Source (Fuente)**: Un recurso externo consultado durante la investigación (artículo, paper, página web, patente). Atributos: URL, título, proveedor, rama de origen, fecha de acceso.
- **Recommendation (Recomendación)**: Acción sugerida basada en los hallazgos. Atributos: texto, prioridad (alta/media/baja), evidencias que la sustentan.
- **ProviderMetric (Métrica de Proveedor)**: Estadísticas de rendimiento de un proveedor MCP: latencia promedio, tasa de error, tasa de reintentos, distribución de latencia.

## Success Criteria

- **SC-001**: Un usuario no técnico puede lanzar una investigación completa (clarificar → aprobar → ver resultados) en menos de 3 clics desde la interfaz, sin tocar la API.
- **SC-002**: La interfaz se actualiza en tiempo real durante la ejecución: el 100% de los eventos SSE tienen representación visual visible en menos de 500ms desde su emisión.
- **SC-003**: El grafo de conocimiento carga y renderiza hasta 200 nodos con sus aristas en menos de 3 segundos en un navegador moderno (Chrome/Firefox/Edge).
- **SC-004**: La navegación entre los 6 agentes en la barra lateral es inmediata (< 100ms de latencia visual al cambiar de agente).
- **SC-005**: El historial de chats persiste entre recargas de página: al recargar, la sesión activa y sus mensajes se restauran completamente en menos de 1 segundo.
- **SC-006**: Las transiciones entre las dos pestañas principales (Chat y Análisis) y entre sub-pestañas de Análisis son instantáneas (< 200ms).
- **SC-007**: El grafo es completamente interactivo: zoom, pan, clic en nodo, visualización de fuentes — todas las operaciones responden en menos de 100ms.
- **SC-008**: En caso de desconexión de red, el SSE se reconecta automáticamente en menos de 30 segundos (backoff exponencial) y el usuario ve un indicador claro del estado de reconexión.
- **SC-009**: El código fuente maintainable: cada módulo funcional tiene cobertura de tests > 70% y todas las funciones tienen tipos TypeScript explícitos (no `any`).

## Delivery Constraints

- **P0 First — No decoration antes de lógica**: Ningún requerimiento marcado como P2 (Decoration) debe implementarse hasta que todos los P0 (Core Logic) y P1 (Essential UI) estén completos, funcionales y probados. Las animaciones, transiciones, sombras, border-radius y efectos hover son lo último que se implementa.
- **Modularización**: Cada funcionalidad debe ser un módulo independiente con su propia carpeta, tipos, componentes y lógica de estado. Prohibido crear archivos "utils" monolíticos o componentes de más de 300 líneas.
- **Código eficiente**: Las actualizaciones de estado durante SSE deben usar batches para evitar re-renders innecesarios. El grafo debe usar virtualización o canvas para mantener 60fps con hasta 500 nodos.
- **Calidad**: TypeScript estricto sin `any`. Todos los componentes deben tener interfaces de props explícitas. Los manejadores de eventos SSE deben estar tipados con los tipos de evento del backend.
- **Manejo de errores explícito**: Toda llamada API debe tener try/catch con estado error visible al usuario. No debe haber errores silenciosos.
- **Rendimiento**: Las operaciones de renderizado del grafo deben ejecutarse en el hilo principal sin bloqueos. Considerar Web Workers para cálculos de layout si es necesario.
- **Accesibilidad**: Todos los controles interactivos deben ser accesibles por teclado. Los eventos SSE deben tener anuncios ARIA para lectores de pantalla.
- **Simplicidad**: Preferir composición de componentes pequeños sobre herencia o HOCs complejos. Cada componente debe hacer una sola cosa y hacerla bien.
