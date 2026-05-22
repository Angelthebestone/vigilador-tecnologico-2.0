# Implementation Plan: Activación de Workstreams desde Frontend y Visualización de Resultados

## Problem

Spec 007 implementó 5 workstreams de evaluación con 34 entidades y 23 protocolos. El sistema funciona, pero es completamente invisible para el usuario: los flags solo se activan editando `.env` a mano, los prompts se modifican editando archivos YAML en el servidor, y el frontend no muestra ningún resultado de evaluación. El mock server actual (2072 líneas) tampoco simula ningún workstream. El usuario no puede activar, configurar ni ver los resultados de la inteligencia que ya está implementada.

## Approach

**Estrategia de 4 frentes**: (1) Exponer 7 nuevos endpoints REST en el backend para configuración y resultados de workstreams, (2) Agregar tipos, stores y componentes React en el frontend para visualizar los 5 workstreams, (3) Añadir una 4ª pestaña "Configuración" en el layout principal con toggles y editor de prompts, (4) Reconstruir el mock server para que emita datos simulados de los 5 workstreams y todos los eventos SSE del pipeline real. Cero refactors laterales — solo se expone lo que ya existe. Cero nuevas dependencias de frontend (Tailwind, Zustand, SSE existentes). Los flags de `.env` siguen siendo el default; la UI persiste overrides en archivo JSON local.

---

## Technical Context

| Area | Decision |
|------|----------|
| **Backend API** | FastAPI, 7 nuevos endpoints bajo `/config/` y extensión de `/research/{id}/evaluation` |
| **Config persistence** | JSON file en `config/workstream_overrides.json` + `config/prompt_overrides/`. Los flags de `.env` son el default; los overrides de UI prevalecen |
| **Prompt overrides** | Sistema de doble capa: el `FilesystemPromptLoader` actual (lru_cache) se extiende con un fallback a directorio `config/prompt_overrides/` que tiene prioridad |
| **Frontend types** | Se extiende `frontend/src/types/index.ts` con ~20 nuevos tipos de spec 007 |
| **Frontend stores** | Nuevo `configStore.ts` (Zustand, persistido) para flags + prompt editor state |
| **Frontend UI** | 4ª pestaña "Configuración" en `MainLayout`, subcomponentes `WorkstreamToggles`, `PromptEditor`, `WorkstreamHealth` |
| **Mock server** | Se reescribe completamente manteniendo endpoints existentes, agregando datos simulados de los 5 workstreams |
| **No nuevas dependencias** | Cero npm/pip packages nuevos. Tailwind, Zustand, FastAPI, SSE existentes |

## External Constraints

| Constraint | Impact |
|------------|--------|
| `grep`/`findstr` no disponible en el sistema | Verificaciones de imports y referencias se hacen con `Select-String` de PowerShell o lectura directa de archivos |
| Mock server actual es un solo archivo Python monolítico (~2072 líneas) | La reescritura debe ser modular para evitar un archivo aún más grande |
| Los prompts de evaluación son actualmente placeholders (texto descriptivo, no templates reales) | La UI de prompt editor debe reflejar que son placeholders y permitir reemplazarlos |
| `@lru_cache` en el loader de prompts actual impide recarga en caliente | El sistema de overrides se aplica antes del cache (a nivel de filesystem) |
| Frontend sin router (usa tabs con estado local) | La 4ª pestaña sigue el mismo patrón de `MainTab` union type |

---

## Files to Create / Modify

### New Files

| File | Purpose |
|------|---------|
| `src/vigilancia_multiagente/api/routes/config_workstreams.py` | Endpoints `GET/PATCH /config/workstreams` y `GET /config/workstreams/health` |
| `src/vigilancia_multiagente/api/routes/config_prompts.py` | Endpoints `GET /config/prompts`, `GET/PUT /config/prompts/{name}`, `POST /config/prompts/{name}/restore` |
| `src/vigilancia_multiagente/config/workstream_overrides.py` | Carga/guarda overrides desde JSON, resuelve prioridad UI > .env |
| `src/vigilancia_multiagente/config/prompt_overrides.py` | Carga/guarda overrides de prompts desde directorio `config/prompt_overrides/` |
| `src/vigilancia_multiagente/api/routes/research_evaluation.py` | Nuevo endpoint `GET /research/{id}/evaluation` extendido con datos de workstreams |
| `config/prompt_overrides/.gitkeep` | Placeholder para directorio de overrides de prompts |
| `config/workstream_overrides.json` | Archivo de persistencia de flags modificados desde UI |
| `frontend/src/types/evaluation.ts` | ~20 tipos TypeScript para entidades de spec 007 |
| `frontend/src/state/configStore.ts` | Zustand store para configuración de workstreams y prompts |
| `frontend/src/analysis/WorkstreamToggles.tsx` | Componente de 5 toggles con tooltips |
| `frontend/src/analysis/PromptEditor.tsx` | Editor de texto para prompts con restaurar default |
| `frontend/src/analysis/ConfigView.tsx` | Vista contenedora de la pestaña Configuración |
| `frontend/src/analysis/WorkstreamSection.tsx` | Componente base para cada sección de workstream en el reporte |
| `frontend/src/analysis/WorkstreamIndicator.tsx` | Badge/icono que muestra workstreams activos durante investigación |
| `frontend/src/analysis/WSASection.tsx` | Visualización WS-A: author reputation, conflictos, fact-checks, retractaciones |
| `frontend/src/analysis/WSBSection.tsx` | Visualización WS-B: búsqueda, autenticidad, consenso/disputa |
| `frontend/src/analysis/WSCSection.tsx` | Visualización WS-C: curva-S, meta-análisis, asunciones, contrafactuales |
| `frontend/src/analysis/WSDSection.tsx` | Visualización WS-D: convergencia, redes, linaje, narrativa, talento, brechas |
| `frontend/src/analysis/WSESection.tsx` | Visualización WS-E: bias audit, forensic trace, stakeholders, calibración |
| `frontend/src/api/evaluation.ts` | Funciones fetch para endpoints de evaluación y configuración |
| `mock_server/data/workstreams.py` | Datos simulados para los 5 workstreams |
| `mock_server/data/branches.py` | Datos de ramas con tool calls y thinking chains |
| `mock_server/data/report.py` | Reporte simulado completo con secciones de workstreams |
| `mock_server/routes/config.py` | Endpoints de configuración simulados |
| `mock_server/routes/research.py` | Endpoints de investigación (refactor del monolito actual) |
| `mock_server/sse_emitter.py` | Lógica de emisión SSE con workstreams |

### Modified Files

| File | Changes |
|------|---------|
| `src/vigilancia_multiagente/api/dependencies.py` | Registrar nuevos servicios de overrides de configuración y prompts |
| `src/vigilancia_multiagente/api/router.py` | Agregar nuevas rutas `/config/` |
| `src/vigilancia_multiagente/api/routes/research_outputs.py` | Delegar evaluación a `research_evaluation.py` |
| `src/vigilancia_multiagente/config/settings.py` | Agregar campo `workstream_overrides_path` para ruta del JSON |
| `src/vigilancia_multiagente/infra/prompts/loader.py` | Extender con fallback a `config/prompt_overrides/` |
| `frontend/src/types/index.ts` | Agregar imports desde `evaluation.ts`, extender `FinalReport` con campo `evaluation` |
| `frontend/src/state/hooks.ts` | Exportar selectores del `configStore` |
| `frontend/src/state/sseHandlers.ts` | Agregar handlers para eventos de workstreams en SSE |
| `frontend/src/MainLayout.tsx` | Agregar 4ª pestaña "Configuración", tipo `'configuracion'` |
| `frontend/src/chat/ReportSummary.tsx` | Renderizar `WorkstreamIndicator` y secciones de workstreams condicionalmente |
| `frontend/src/api/endpoints.ts` | Agregar funciones para nuevos endpoints de config y evaluación |
| `frontend/src/analysis/AnalysisPanel.tsx` | Opcional: agregar sub-pestañas de workstreams o delegar al reporte |
| `mock_server.py` | Refactorizar en módulos bajo `mock_server/`, mantener compatibilidad de endpoints. Eliminar del archivo original todo el código extraído a `mock_server/data/`, `mock_server/routes/` y `mock_server/sse_emitter.py`, dejando solo imports y `uvicorn.run(app)`. |
| `.env.example` | Documentar nuevos paths de configuración |

---

## Constitution Check (Pre-Design)

- **Gate result**: PASS
- **Alignment**:
  - **Pensar Antes de Codificar**: El plan expone explícitamente todas las decisiones de archivos, persistencia y flujo de datos. No hay ambigüedades sobre dónde vive cada pieza.
  - **Simplicidad Obligatoria**: Cero nuevas dependencias. La persistencia usa archivos JSON locales (no base de datos). Los componentes de frontend reutilizan Tailwind/Zustand/SSE existentes. El mock server se refactoriza sin añadir complejidad.
  - **Modularidad Primero**: Cada workstream tiene su propio componente visual (`WSASection`, `WSBSection`, etc.). El config store está separado de los stores de sesión. Los endpoints de config están en archivos separados.
  - **Cambios Quirúrgicos y Trazables**: Cero refactors laterales. Solo se toca lo necesario para exponer y visualizar. Las líneas modificadas en archivos existentes son mínimas (agregar imports, registrar rutas, extender tipos).
  - **Entrega Verificable**: Cada componente tiene su correspondiente mock server con datos simulados. Los endpoints de config tienen tests de integración planificados.
- **Diseño de Software**:
  - **SRP**: Cada componente de workstream renderiza una sola entidad. Cada endpoint de config maneja una sola responsabilidad.
  - **OCP**: El sistema de overrides extiende el comportamiento de flags/prompts sin modificar el mecanismo `.env` existente.
  - **DIP**: Los nuevos endpoints dependen de abstracciones (`PromptLoader`, settings) no de implementaciones concretas.
  - **KISS**: JSON files para persistencia. Sin base de datos, sin migraciones, sin ORM.
  - **POLA**: Los flags arrancan en `false`. El comportamiento por defecto es idéntico a pre-008.
  - **SoC**: Configuración (flags, prompts) separada de resultados (evaluación por workstream) separada de visualización (componentes React).

---

## Phases

### Phase 0 — Research & Foundation

1. Consolidar hallazgos de investigación (mock server actual, stores existentes, tipos, endpoints)
2. Documentar decisiones técnicas en `research.md`

**Output**: `research.md`

---

### Phase 1 — Backend: Config & Evaluation API

#### 1.1 Persistencia de configuración
- Crear `config/workstream_overrides.py`: lee/escribe `config/workstream_overrides.json`, resuelve prioridad (override UI > .env default)
- Crear `config/prompt_overrides.py`: lee/escribe archivos en `config/prompt_overrides/`, expone `get_override(name) -> str | None`, `set_override(name, content)`, `restore_default(name)`, `list_overrides() -> list[dict]`
- Extender `settings.py` con `workstream_overrides_path: str` (default `config/workstream_overrides.json`)

#### 1.2 Endpoints de configuración
- `GET /config/workstreams` — devuelve `{ ws_a: bool, ws_b: bool, ws_c: bool, ws_d: bool, ws_e: bool }` resolviendo overrides
- `PATCH /config/workstreams` — recibe partial booleans, guarda en `workstream_overrides.json`
- `GET /config/workstreams/health` — chequea reachabilidad de OpenAlex, presencia de API keys, CSV disponible

#### 1.3 Endpoints de prompts
- `GET /config/prompts` — lista los 8 templates con `{ name, modified, size }`
- `GET /config/prompts/{name}` — contenido completo del template (override si existe, sino default)
- `PUT /config/prompts/{name}` — guarda override en `config/prompt_overrides/{name}.txt`
- `POST /config/prompts/{name}/restore` — elimina el archivo de override

#### 1.4 Extender loader de prompts
- Modificar `FilesystemPromptLoader.load()`: primero busca en `config/prompt_overrides/{path}.txt`, si no existe usa el default de `prompts/`
- Mantener `@lru_cache` (la clave de cache incluye el path de override)

#### 1.5 Endpoint de evaluación extendido
- Reescribir `GET /research/{id}/evaluation` para devolver datos estructurados por workstream usando las entidades de spec 007
- Si un workstream no estuvo activo, su key retorna `null`

**Output**: 4 nuevos archivos Python, 3 archivos modificados, 7 nuevos endpoints funcionando

---

### Phase 2 — Frontend: Types, Stores & Config Panel

#### 2.1 Tipos de spec 007
- Crear `frontend/src/types/evaluation.ts` con todos los tipos de entidades:
  - WS-A: `AuthorReputation`, `ConflictOfInterest`, `ClaimExternalValidation`, `RetractionRecord`, `ReproducibilityScore`
  - WS-B: `DedupedSource`, `ContentAuthenticitySignal`, `ConsensusDisputeEntry`
  - WS-C: `SCurveProjection`, `ImplicitAssumption`, `CounterfactualScenario`, `CriticalDependency`, `MetaAnalysisResult`
  - WS-D: `ConvergenceCluster`, `CollaborationNetwork`, `IdeaLineage`, `NarrativeShift`, `TalentMobility`, `PatentingGap`
  - WS-E: `BiasAudit`, `ForensicTrace`, `StakeholderSimulation`, `FalsificationScenario`, `CalibrationCurve`
  - Agregados: `SessionEvaluation`, `WorkstreamConfig`, `PromptTemplate`, `WorkstreamHealth`

#### 2.2 Config Store
- Crear `configStore.ts` (Zustand + persist):
  - Estado: `workstreams: WorkstreamConfig`, `prompts: PromptTemplate[]`, `selectedPrompt: string | null`, `promptContent: string`, `health: WorkstreamHealth | null`
  - Acciones: `fetchWorkstreams()`, `toggleWorkstream(ws, value)`, `saveWorkstreams()`, `fetchPrompts()`, `selectPrompt(name)`, `updatePromptContent(content)`, `savePrompt()`, `restorePrompt(name)`, `fetchHealth()`

#### 2.3 API functions
- Crear `frontend/src/api/evaluation.ts` con funciones fetch para todos los nuevos endpoints
- Extender `endpoints.ts` con exports para `getSessionEvaluation`, `getWorkstreamConfig`, `patchWorkstreamConfig`, `getPromptList`, `getPrompt`, `putPrompt`, `restorePrompt`, `getWorkstreamHealth`

#### 2.4 Config View (4ª pestaña)
- Crear `ConfigView.tsx` como contenedor con dos secciones: "Workstreams" y "Prompts"
- Crear `WorkstreamToggles.tsx`: 5 cards con toggle, nombre, descripción, tooltip, y badge de health
- Crear `PromptEditor.tsx`: lista lateral de 8 templates + área de texto + botones Guardar/Restaurar + indicador "Modificado"
- Modificar `MainLayout.tsx`: agregar `'configuracion'` a `MainTab`, extender `TABS` y `FOLIO`, agregar render condicional

**Output**: 8 nuevos archivos TypeScript/TSX, 3 archivos modificados

---

### Phase 3 — Frontend: Workstream Visualization

#### 3.1 Workstream Indicator
- Crear `WorkstreamIndicator.tsx`: badges inline que muestran qué workstreams están activos
- Integrar en `ChatView.tsx` (junto al estado de sesión) y `ReportSummary.tsx` (al inicio del reporte)

#### 3.2 Workstream Sections
- Crear `WorkstreamSection.tsx`: wrapper colapsable con título, icono, badge de estado
- Crear `WSASection.tsx`: tabla de author reputation, badges de conflicto, lista de fact-checks, badges de retractación
- Crear `WSBSection.tsx`: stats de búsqueda, gráfico de autenticidad, tabla de consenso/disputa
- Crear `WSCSection.tsx`: mini-gráfico de curva-S, badges de asunciones, lista de contrafactuales, lista de dependencias
- Crear `WSDSection.tsx`: lista de clusters, mini-grafo de colaboración, timeline de linaje, indicador de narrativa, badges de brechas
- Crear `WSESection.tsx`: alerta de bias, tabla de distribuciones, tarjetas de stakeholders, curva de calibración

#### 3.3 Integración en ReportSummary
- Modificar `ReportSummary.tsx`: después del executive summary, renderizar `WorkstreamIndicator` y mapear `evaluation.workstreams` a sus secciones correspondientes
- Cada sección solo se renderiza si su workstream estuvo activo (`evaluation.ws_a !== null`, etc.)

#### 3.4 SSE Handler
- Modificar `sseHandlers.ts`: extender handler de `EvaluationComputed` para almacenar datos de workstreams en el store de sesión

**Output**: 9 nuevos componentes TSX, 2 archivos modificados

---

### Phase 4 — Mock Server: Workstreams + Refactor

#### 4.1 Datos simulados
- Crear `mock_server/data/workstreams.py`: datos estáticos realistas para cada workstream
- Crear `mock_server/data/branches.py`: extraer `BRANCH_ITERATIONS` y `REPLAN_SIGNALS` del monolito
- Crear `mock_server/data/report.py`: extender `FINAL_REPORT` con campo `evaluation` que incluye datos de workstreams

#### 4.2 Refactor modular
- Crear `mock_server/sse_emitter.py`: lógica de emisión SSE con workstreams (secuencia completa, sin omitir eventos)
- Crear `mock_server/routes/research.py`: endpoints de investigación (extraídos del monolito)
- Crear `mock_server/routes/config.py`: nuevos endpoints de configuración simulados
- Modificar `mock_server.py`: convertirlo en entry point delgado que importa desde `mock_server/`

#### 4.3 Workstreams en el mock
- `GET /config/workstreams` simulado: devuelve flags desde estado en memoria
- `PATCH /config/workstreams` simulado: actualiza flags en memoria
- `GET /config/prompts` simulado: devuelve lista de 8 templates desde archivos estáticos
- `GET /config/prompts/{name}` simulado: devuelve contenido del template
- `PUT /config/prompts/{name}` simulado: guarda en dict en memoria
- `POST /config/prompts/{name}/restore` simulado: restaura a default
- `ReportGenerated` incluye `evaluation` con datos de workstreams activos
- Si un workstream está desactivado en el mock, su sección no aparece en el reporte

**Output**: 5 nuevos archivos Python, 1 archivo modificado (mock_server.py → entry point)

---

### Phase 5 — Polish & Integration

1. Ejecutar `check-layer-imports.py` para verificar que `application/` no importa de `infra/`
2. Ejecutar typecheck en frontend (`npx tsc --noEmit`)
3. Probar mock server: `python mock_server.py` + frontend `npm run dev`
4. Verificar que con flags=false el pipeline es byte-idéntico a pre-008
5. Actualizar `.env.example` con nuevos paths

**Output**: Verificaciones pasando, sistema funcionando con mock server

---

## Rollout Strategy

- **Flags en `.env`**: Siguen siendo el mecanismo default. El sistema arranca con todos los workstreams en `false` (comportamiento pre-008)
- **Overrides JSON**: Si `config/workstream_overrides.json` existe, sus valores prevalecen sobre `.env`. Se crea vacío por defecto
- **Mock server**: Totalmente independiente. Se ejecuta con `python mock_server.py`. No requiere backend real
- **Frontend**: La 4ª pestaña "Configuración" solo aparece si el endpoint `/config/workstreams` responde (el mock server lo implementa; en prod depende del backend)
- **Rollback**: Borrar `config/workstream_overrides.json` y `config/prompt_overrides/` revierte a comportamiento `.env`

---

## Success Criteria

- **SC-001**: Administrador activa/desactiva workstream en <10s (2 clics) ✓ (WorkstreamToggles con autosave)
- **SC-002**: 100% entidades spec 007 renderizadas en frontend ✓ (6 componentes de sección + tipos TypeScript completos)
- **SC-003**: Editar y guardar prompt en <30s sin tocar servidor ✓ (PromptEditor con PUT endpoint)
- **SC-004**: Frontend refleja workstreams activos sin falsos positivos/negativos ✓ (SessionEvaluation con null para inactivos)
- **SC-005**: Carga del reporte no aumenta >2s ✓ (datos ya incluidos en el reporte, sin fetch extra)
- **SC-006**: Usuario nuevo entiende workstreams sin docs ✓ (tooltips en WorkstreamToggles)
- **SC-007**: Mock server emite 100% de eventos SSE ✓ (sse_emitter.py con secuencia completa)
- **SC-008**: Dev frontend itera con mock server en <2min ✓ (`npm run mock-server` + `npm run dev`)

## Constitution Check (Post-Design)

- **Status**: PASS
- **Justification**: 
  - El plan no introduce nuevas dependencias ni frameworks
  - La persistencia usa archivos JSON locales — el mecanismo más simple posible
  - Cada workstream tiene su propio componente visual (SRP, SoC)
  - Los overrides extienden sin modificar el mecanismo `.env` existente (OCP)
  - Cero refactors laterales — solo se exponen y visualizan entidades ya implementadas
  - El mock server se refactoriza manteniendo 100% compatibilidad de endpoints
  - Los flags arrancan en `false` (POLA, comportamiento pre-008 idéntico)
