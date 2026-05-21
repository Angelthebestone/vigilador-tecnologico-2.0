# Feature Specification: Activación de Workstreams desde Frontend y Visualización de Resultados

## Problem Statement

Spec 007 implementó 5 workstreams de evaluación (WS-A Source Quality, WS-B Data Intelligence, WS-C Deep Analysis, WS-D Strategic Signals, WS-E Output Assurance) con 34 entidades nuevas y 23 protocolos. Sin embargo, todo el sistema es invisible para el usuario: los flags solo se activan editando `.env` a mano, los prompts solo se modifican editando archivos YAML en el servidor, y el frontend no muestra ningún resultado de evaluación — ni siquiera sabe que los workstreams existen. El usuario no puede activar, configurar ni ver los resultados de la inteligencia que ya está implementada.

## Scope Boundaries

### In Scope
- Panel de configuración en frontend para activar/desactivar cada workstream (A, B, C, D, E) individualmente
- Visualización en frontend de todos los resultados generados por cada workstream activo
- Editor de prompts desde el frontend: ver, editar y restaurar los templates de prompts de evaluación
- Nuevos endpoints API para exponer resultados de workstreams al frontend
- Nuevos endpoints API para leer y actualizar configuración de workstreams y prompts
- Visualización del Quality Gate (WS-E): bias audit, forensic trace, stakeholders, falsificación, calibración
- Indicadores visuales de qué workstreams están activos durante una investigación en curso
- **Mock server completo**: simula cadenas de pensamiento por rama, ejecución de tools (MCP calls visibles), resultados de los 5 workstreams, y todos los eventos SSE del pipeline real — sin omitir ninguna función del backend real

### Out of Scope
- Modificar la lógica de los workstreams ya implementados (eso es spec 007)
- Cambiar el mecanismo de opt-in por flag (los flags de `.env` siguen siendo el default inicial)
- Agregar nuevos workstreams (WS-F, etc.)
- Migrar la base de datos o el modelo de datos de spec 007
- Autenticación/permisos por workstream (todos los usuarios administradores ven todo)
- El mock server **no** requiere PostgreSQL, MCP providers reales, ni LLM — funciona con datos estáticos simulados

## Assumptions
- El usuario que accede al panel de configuración es administrador del sistema
- Los cambios de configuración (flags, prompts) se persisten en el backend y sobreviven reinicios
- Los workstreams se activan/desactivan por sesión: el flag aplica a la próxima investigación iniciada, no a investigaciones en curso
- La edición de prompts es para los 8 templates de evaluación (`assumption_detection.txt`, `counterfactual.txt`, `falsification.txt`, `stakeholder_investor.txt`, `stakeholder_regulator.txt`, `stakeholder_competitor.txt`, `stakeholder_academic.txt`, `query_expand.txt`)
- Los templates de prompts de evaluación son texto plano — no requieren editor de YAML ni JSON
- El frontend ya tiene SSE streaming, tipos TypeScript, stores Zustand, y componentes React con Tailwind

## User Scenarios & Testing

### Primary User Story 1: Activar workstreams desde la UI
Un administrador quiere activar la evaluación de calidad de fuentes (WS-A) para su próxima investigación sin tener que editar archivos del servidor.

**Acceptance Scenarios**:
1. **Given** un administrador autenticado en la vista de configuración, **When** activa el toggle de WS-A y guarda, **Then** el sistema persiste el flag y WS-A se ejecutará en la próxima investigación que inicie.
2. **Given** WS-A activado desde la UI, **When** el administrador inicia una nueva investigación, **Then** el pipeline de ejecución incluye SourceQualityStep y los resultados de WS-A aparecen en el reporte final.
3. **Given** WS-A desactivado desde la UI, **When** se inicia una investigación, **Then** el pipeline es idéntico al comportamiento pre-007 (sin workstreams).

### Primary User Story 2: Ver resultados de evaluación en el reporte
Un analista termina una investigación y quiere ver el análisis de calidad de fuentes, las curvas-S de madurez tecnológica, las señales estratégicas y el quality gate en el frontend.

**Acceptance Scenarios**:
1. **Given** una investigación completada con WS-A, B, C, D y E activos, **When** el analista abre el reporte, **Then** ve secciones dedicadas para: calidad de fuentes (reputación de autores, conflictos de interés, retractaciones), inteligencia de datos (autenticidad, consenso/disputa), análisis profundo (curva-S, asunciones, dependencias), señales estratégicas (redes, convergencia, brechas) y assurance (bias audit, stakeholders, calibración).
2. **Given** una investigación con solo WS-A activo, **When** el analista abre el reporte, **Then** solo ve la sección de calidad de fuentes; las demás secciones no aparecen.
3. **Given** el quality gate detectó bias crítico, **When** el analista ve el reporte, **Then** ve una alerta visual destacada explicando el tipo de bias detectado y las fuentes afectadas.

### Primary User Story 3: Editar prompts de evaluación
Un administrador quiere ajustar el prompt de detección de asunciones implícitas porque el actual no captura bien las asunciones en su dominio técnico.

**Acceptance Scenarios**:
1. **Given** el administrador en el editor de prompts, **When** selecciona el template `assumption_detection.txt` y modifica su contenido, y guarda, **Then** el sistema persiste la nueva versión y la usa en la próxima ejecución de WS-C.
2. **Given** el administrador modificó un prompt y quiere revertirlo, **When** presiona "Restaurar default", **Then** el prompt vuelve al contenido original del template.
3. **Given** un prompt modificado tiene sintaxis inválida (placeholders rotos), **When** el administrador guarda, **Then** el sistema muestra una advertencia pero permite guardar (los placeholders se validan en runtime).

### Edge Cases
- Workstream activado en UI pero servicio externo caído (OpenAlex, Google FactCheck): el sistema sigue funcionando, el workstream produce `StepError(warning)` y el frontend muestra "parcialmente disponible" en esa sección.
- Workstream activado a mitad de una investigación en curso: no afecta la investigación actual, aplica a la siguiente.
- Múltiples administradores editando prompts simultáneamente: última escritura gana, sin bloqueo.
- Prompt vacío: el sistema usa el template default en runtime.
- Workstream activado pero `.env` tiene la clave externa faltante (ej. `VT_GOOGLE_FACTCHECK_API_KEY` no configurada): el workstream corre pero el fact-checker degrada a `not_found`.

## Functional Requirements

### FR-F01: Endpoint de configuración de workstreams
`GET /config/workstreams` devuelve el estado actual (booleano) de cada workstream (A, B, C, D, E).
`PATCH /config/workstreams` recibe `{ ws_a: true, ws_b: false, ... }` y persiste los flags para la próxima investigación.

### FR-F02: Panel de configuración en frontend
Una vista accesible desde la UI principal (pestaña o ícono de configuración) muestra 5 toggles independientes (WS-A, WS-B, WS-C, WS-D, WS-E) con etiqueta descriptiva, tooltip explicando qué hace cada workstream, y estado actual. Incluye botón "Guardar cambios".

### FR-F03: Indicador visual de workstreams activos
Durante una investigación en curso, un indicador sutil (íconos o badges) muestra qué workstreams están activos. Al finalizar, un resumen muestra cuáles se ejecutaron y cuáles no.

### FR-F04: Endpoint de resultados de workstreams
`GET /research/{session_id}/evaluation` devuelve un objeto con los resultados de todos los workstreams activos para esa sesión, estructurado por workstream. Si un workstream no estuvo activo, su key retorna `null`.

### FR-F05: Secciones de reporte por workstream
El reporte final en frontend muestra secciones colapsables por cada workstream que estuvo activo. Cada sección renderiza los datos relevantes de forma visual (no solo texto plano).

### FR-F06: Visualización WS-A (Source Quality)
Muestra por finding: author reputation (h-index, afiliación), conflictos de interés detectados (nivel de riesgo), fact-checks externos, estado de retractación, score de reproducibilidad, y decay temporal aplicado a cada fuente.

### FR-F07: Visualización WS-B (Data Intelligence)
Muestra estadísticas de búsqueda híbrida, tasa de deduplicación, autenticidad de contenido (probabilidad IA, burstiness), y mapa de consenso/disputa entre fuentes como gráfico de acuerdo/desacuerdo.

### FR-F08: Visualización WS-C (Deep Analysis)
Muestra por finding: proyección de curva-S con gráfico de madurez, meta-análisis (tamaño de efecto, heterogeneidad I²), asunciones implícitas detectadas (con severidad), escenarios contrafactuales, y dependencias críticas mapeadas.

### FR-F09: Visualización WS-D (Strategic Signals)
Muestra: clusters de convergencia entre dominios, red de colaboración (grafo co-autoría/co-invención), linaje de ideas (trazabilidad de publicaciones seminales), cambios de narrativa (sentiment pre/post con punto de cambio), movilidad de talento, y brechas de patentamiento (blue ocean / red ocean).

### FR-F10: Visualización WS-E (Output Assurance)
Muestra: resultado del bias audit (distribución geográfica, género, institucional con alerta si es crítico), trazabilidad forense (cadena claim→fuente→razonamiento), simulaciones de stakeholders (4 perspectivas con críticas), escenarios de falsificación, y curva de calibración empírica con comparación vs curva identidad.

### FR-F11: Endpoint de prompts de evaluación
`GET /config/prompts` devuelve la lista de templates de evaluación con nombre, contenido actual, y si fue modificado respecto al default.
`GET /config/prompts/{template_name}` devuelve el contenido completo de un template.
`PUT /config/prompts/{template_name}` recibe `{ content: "..." }` y actualiza el template.
`POST /config/prompts/{template_name}/restore` restaura el template a su contenido default.

### FR-F12: Editor de prompts en frontend
Vista de administración que lista los 8 templates de evaluación. Al seleccionar uno, muestra un editor de texto con el contenido actual, botón "Guardar" y botón "Restaurar default". Muestra indicador visual si el template fue modificado.

### FR-F13: Persistencia de configuración
Los flags de workstreams y los prompts modificados se persisten de forma que sobrevivan reinicios del servidor. Los valores modificados prevalecen sobre los defaults.

### FR-F14: API de health check por workstream
`GET /config/workstreams/health` devuelve el estado de disponibilidad de cada servicio externo requerido por los workstreams (OpenAlex reachable, Google FactCheck API key configured, Retraction Watch CSV disponible, etc.).

## Key Entities

- **WorkstreamConfig**: flag booleano por workstream (A..E), persistido
- **PromptTemplate**: nombre, contenido actual, contenido default, indicador de modificación
- **SessionEvaluation**: agregado de resultados de todos los workstreams para una sesión, particionado por workstream activo
- **WorkstreamHealth**: estado de disponibilidad de dependencias externas por workstream

## Success Criteria

- **SC-001**: Un administrador puede activar o desactivar cualquier workstream desde el frontend en menos de 10 segundos (2 clics: toggle + guardar)
- **SC-002**: El 100% de las entidades de spec 007 que tengan datos para una sesión se renderizan en el frontend en secciones dedicadas
- **SC-003**: Un administrador puede editar y guardar un prompt de evaluación en menos de 30 segundos sin tocar archivos del servidor
- **SC-004**: El frontend refleja correctamente qué workstreams estuvieron activos al 100% de las investigaciones completadas (sin falsos positivos ni negativos)
- **SC-005**: El tiempo de carga del reporte no aumenta más de 2 segundos al incluir todas las secciones de workstreams
- **SC-006**: Un usuario nuevo entiende qué hace cada workstream sin consultar documentación externa (tooltips y etiquetas auto-explicativas)

## Delivery Constraints
- **Simplicidad obligatoria**: La UI usa componentes React existentes (Tailwind, Zustand stores, SSE) sin nuevos frameworks
- **Modularidad**: Cada sección de workstream en frontend es un componente independiente que se renderiza condicionalmente
- **No refactor lateral**: No se modifica la lógica de negocio de los workstreams — solo se exponen y visualizan
- **KISS**: Los indicadores visuales son íconos/badges, no gráficos complejos que requieran nuevas dependencias
- **POLA**: Los flags arrancan en `false` (comportamiento actual). El usuario opta in explícitamente.
- **Manejo de errores estricto**: Si un endpoint de workstream falla, el frontend muestra "No disponible" en esa sección sin romper el resto del reporte.
