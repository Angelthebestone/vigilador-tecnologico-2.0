# Tasks: Auditoría de Integración del Sistema

**Input**: `PLAN_DE_AUDITORIA.md`, `frontend/src/api/client.ts`, `frontend/src/api/endpoints.ts`, `frontend/src/state/`, `mock_server.py`, `src/vigilancia_multiagente/api/`
**Feature**: Corregir las desconexiones críticas entre backend (Python/FastAPI) y frontend (React/TypeScript), alinear contratos de datos (snake_case vs camelCase), normalizar el flujo SSE, completar el mock server, y agregar tests de contrato — para que el sistema funcione correctamente contra el backend real y no solo contra el mock.

---

## Phase 1: Setup & Baseline

Preparar el entorno de trabajo para la auditoría, capturar el estado actual del contrato API, y establecer las herramientas de verificación.

- [X] T001 [P] Crear script de verificación de contrato API en `scripts/check-api-contract.py` que compare los tipos TypeScript del frontend (`frontend/src/types/index.ts`) con los endpoints reales del backend (respuestas reales)
- [X] T002 [P] Documentar línea base de endpoints del backend en `docs/api-endpoints-reference.md`: todos los métodos, rutas, request/response shapes, y estado actual de implementación en mock server
- [X] T003 [P] Agregar `tests/test_contract_mock_vs_backend.py` que arranque el mock server y verifique que cada endpoint mock devuelva la misma estructura (mismas keys) que el backend real
- [X] T004 [P] Agregar `VT_AUDIT_MODE` flag en `src/vigilancia_multiagente/config/settings.py` para habilitar logging detallado de transformación de datos entre capas

## Phase 2: Foundational — Transform Layer (snake_case ↔ camelCase)

Construir la capa de transformación automática en el cliente frontend para resolver el problema crítico C1. Esta fase debe completarse ANTES de cualquier fase de corrección de contratos, porque sin ella el frontend no puede comunicarse con el backend real.

- [X] T005 Implementar función `toCamelCase(obj)` y `toSnakeCase(obj)` en `frontend/src/api/transform.ts` que convierta recursivamente todas las keys de objetos anidados
- [X] T006 [P] Implementar interceptor de respuesta en `frontend/src/api/client.ts`: en el método `request()`, después de `response.json()`, convertir recursivamente todas las keys de snake_case a camelCase
- [X] T007 [P] Implementar interceptor de request en `frontend/src/api/client.ts`: en el método `request()`, antes de `JSON.stringify(body)`, convertir recursivamente todas las keys de camelCase a snake_case
- [X] T008 Escribir tests unitarios para `transform.ts` en `frontend/src/api/__tests__/transform.test.ts`: verificar conversión de objetos anidados, arrays, null/undefined, y casos borde
- [X] T009 [P] Actualizar `API_BASE` en `frontend/src/api/client.ts` para que use el proxy de Vite en desarrollo (`/api/v2`) y la URL directa en producción, asegurando que el transform layer se aplique en ambos modos

## Phase 3: Correcciones Críticas de Contrato API [US1]

**Story**: Como ingeniero de integración, quiero que los endpoints críticos del API tengan contratos de datos correctos entre backend y frontend — para que el flujo completo de investigación (start → clarify → approve → execute → report) funcione sin errores.

**Independent Test Criteria**: El flujo E2E completo ejecutado contra el backend real (no mock) completa sin errores 404/422/500, y cada respuesta REST se parsea correctamente en los tipos TypeScript correspondientes.

- [X] T010 [P] [US1] Arreglar `approvePlan()` en `frontend/src/api/endpoints.ts`: agregar `{ approved: true }` como body del POST, cambiando `apiPost(\`/research/${sessionId}/approve\`)` a `apiPost(\`/research/${sessionId}/approve\`, { approved: true })`
- [X] T011 [P] [US1] Arreglar manejador SSE `ReportGenerated` en `frontend/src/state/sseHandlers.ts`: cambiar lógica para obtener el reporte completo vía `getReport()` REST después de recibir el evento SSE, en vez de asumir que el evento contiene el reporte completo
- [X] T012 [US1] Arreglar `AnalysisView` en `frontend/src/analysis/AnalysisView.tsx`: modificar `getMetrics()` para que también obtenga branch KPIs desde el endpoint correcto, o agregar llamada paralela a endpoint de KPIs si existe
- [X] T013 [P] [US1] Arreglar `ask_follow_up` response parse en `frontend/src/chat/ChatView.tsx`: adaptar el manejador de respuesta para que acepte tanto `{ requires_permission: true, prompt: "..." }` (snake_case del backend real) como `{ requiresPermission: true }` (tras transform layer)
- [X] T014 [US1] Verificar y corregir response shape de `getReport()` en `frontend/src/api/endpoints.ts` y `frontend/src/chat/ReportSummary.tsx`: asegurar que los campos `recommendations[].based_on` (backend `based_on`) y `report.generated_at` (backend `generated_at`) se mapeen correctamente

## Phase 4: Flujo de Datos Frontend y State Management [US2]

**Story**: Como desarrollador frontend, quiero que el estado de la aplicación sea consistente a través de recargas de página y cambios de sesión — para que la experiencia de usuario no se pierda ante eventos inesperados.

**Independent Test Criteria**: Al recargar la página durante una sesión activa, el sessionId y sessionStatus se restauran correctamente, y el usuario puede continuar desde el último estado conocido.

- [X] T015 [P] [US2] Agregar persistencia de `sessionStatus` en `frontend/src/state/useStore.ts`: incluir `sessionStatus` en la lista `partialize` del middleware `persist`, para que sobreviva a recargas de página
- [X] T016 [P] [US2] Agregar persistencia de `reportVariants` en `frontend/src/state/useStore.ts`: incluir `reportVariants` en la lista `partialize`
- [X] T017 [US2] Migrar `AnalysisView.tsx` para usar `analysisStore` en vez de estado local: refactorizar `AnalysisContent` para leer metrics/recommendations desde `useAnalysisStore()` y llamar `fetchMetrics()` / `fetchRecommendations()` en el useEffect
- [X] T018 [P] [US2] Agregar manejador SSE para `PlanApproved` en `frontend/src/state/sseHandlers.ts`: cuando se reciba el evento, actualizar el estado de sesión a `APPROVED`
- [X] T019 [P] [US2] Agregar manejador SSE para `EvaluationComputed` en `frontend/src/state/sseHandlers.ts`: recibir los KPIs por rama y actualizar el store de análisis
- [X] T020 [P] [US2] Agregar lógica de restauración de estado en `frontend/src/MainLayout.tsx`: al montar la app, si hay `sessionId` persistido, cargar el estado de la sesión activa (plan, report) vía REST
- [X] T021 [US2] Agregar manejo de `sessionStatus === 'COMPLETED'` en `frontend/src/chat/ChatView.tsx`: si al recargar la página el sessionStatus es COMPLETED, habilitar conversation mode automáticamente
- [X] T035 [P] [US2] Agregar persistencia de sesiones completadas en `frontend/src/state/historyStore.ts`: después de que un research se complete exitosamente, guardar un nuevo `SessionSummary` en el store de historial para que aparezca en la HistoryBar
- [X] T036 [P] [US2] Manejar el campo `analytics` en la respuesta de `getGraph()`: actualizar el tipo `GraphData` en `frontend/src/types/index.ts` para incluir `analytics` opcional, y exponer métricas del grafo en la UI cuando estén disponibles

## Phase 5: Mock Server Completo y Alineado [US3]

**Story**: Como tester de integración, quiero que el mock server implemente TODOS los endpoints del backend real y devuelva datos en el mismo formato — para poder desarrollar y probar el frontend de forma aislada con total fidelidad.

**Independent Test Criteria**: Cada endpoint del backend real tiene un endpoint correspondiente en el mock server que devuelve la misma estructura de datos (mismas keys, mismos tipos anidados).

- [X] T037 [P] [US3] Implementar endpoint `GET /api/v2/research/{id}/graph/nodes` en `mock_server.py`: devolver lista de nodos del grafo (misma estructura que el endpoint real)
- [X] T038 [P] [US3] Implementar endpoint `GET /api/v2/research/{id}/graph/edges` en `mock_server.py`: devolver lista de aristas del grafo
- [X] T039 [P] [US3] Implementar endpoint `GET /api/v2/research/{id}/graph/{node_id}/sources` en `mock_server.py`: devolver source_node_ids para un nodo específico
- [X] T040 [P] [US3] Implementar endpoint `POST /api/v2/research/{id}/modify` en `mock_server.py`: simular modificación de plan
- [X] T041 [P] [US3] Implementar endpoint `GET /api/v2/research/{id}/graph/ecosystem` en `mock_server.py`: simular descubrimiento de ecosistema tecnológico
- [X] T042 [P] [US3] Implementar endpoint `GET /api/v2/research/{id}/graph/search-cross-session` en `mock_server.py`: simular búsqueda cross-session
- [X] T043 [P] [US3] Implementar endpoint `POST /api/v2/research/{id}/decision` en `mock_server.py`: simular análisis de decisión
- [X] T050 [P] [US3] Implementar endpoint `POST /api/v2/research/{id}/obsolescence` en `mock_server.py`: simular análisis de obsolescencia
- [X] T051 [P] [US3] Implementar endpoint `POST /api/v2/research/{id}/hype-analysis` en `mock_server.py`: simular análisis de hype
- [X] T052 [US3] Normalizar respuesta del endpoint `/providers` en `mock_server.py`: separar `branchKpis` y `confidenceCalibration` en sus propios endpoints simulados, o documentar que el mock los agrega donde el backend no
- [X] T053 [US3] Agregar evento SSE `FusionProgress` al backend real en `src/vigilancia_multiagente/api/routes/research_approve.py`: emitir progreso de fusión durante `report_synthesizer.synthesize()` para que coincida con el mock y el frontend
- [X] T054 [P] [US3] Agregar evento SSE `BranchFailed` al mock server en `mock_server.py`: simular fallo de rama para probar el manejador del frontend
- [X] T055 [P] [US3] Agregar evento SSE `EvaluationComputed` al mock server en `mock_server.py`: emitir KPIs por rama al completar, imitando el backend real

## Phase 6: Type Checking — basedpyright [US4]

**Story**: Como mantenedor del backend, quiero que todo el código Python pase un type checker estático riguroso (basedpyright) — para detectar errores de tipo, llamadas incorrectas, y violaciones de contratos en tiempo de desarrollo, no en runtime.

**Independent Test Criteria**: basedpyright se ejecuta sin errores (exit code 0) sobre todo el paquete `src/vigilancia_multiagente/`, verificado en CI.

- [X] T056 [P] [US4] Instalar basedpyright vía `pip install basedpyright` y agregar a `[project.optional-dependencies] dev` en `pyproject.toml` — **HECHO**
- [X] T057 [US4] Crear archivo de configuración `pyproject.toml [tool.basedpyright]`: establecer `typeCheckingMode = "standard"`, `pythonVersion = "3.11"`, `include = ["src/vigilancia_multiagente"]`, `exclude = ["tests", "scripts", "mock_server.py", "specs", "docs"]`, `reportMissingTypeStubs = false`, `reportMissingImports = false`, y executionEnvironment con `extraPaths = ["src"]` — **HECHO**
- [X] T058 [US4] Ejecutar basedpyright por primera vez sobre todo `src/vigilancia_multiagente/`, capturar el conteo de errores actual como línea base, y documentar en `docs/type-checking-baseline.md`
- [X] T059 [US4] Corregir errores de tipo en la capa `domain/`: asegurar que todas las entidades (GlobalKnowledgeSnapshot, SourceTrustRecord, SessionContinuationState, TrendProjection, ReportVariant, Signal, ReplanAction, SandboxSession, DocumentReference, BrowserContext) tengan tipos explícitos correctos en `src/vigilancia_multiagente/domain/`
- [X] T060 [US4] Corregir errores de tipo en la capa `api/routes/`: tipar correctamente los parámetros de ruta, modelos Pydantic, y valores de retorno en `src/vigilancia_multiagente/api/routes/`
- [X] T061 [P] [US4] Corregir errores de tipo en la capa `application/`: asegurar firmas de métodos correctas, tipos de retorno de servicios asíncronos, y uso correcto de genéricos en `src/vigilancia_multiagente/application/`
- [X] T062 [P] [US4] Corregir errores de tipo en la capa `infra/`: resolver incompatibilidades con SQLAlchemy/asyncpg (configurar `reportArgumentType = false` en los módulos de persistencia si es necesario, siguiendo el patrón de mypy), tipar correctamente los MCP providers en `src/vigilancia_multiagente/infra/`
- [X] T063 [P] [US4] Corregir errores de tipo en `config/settings.py` y `api/dependencies.py`: asegurar que todas las dependencias inyectadas tengan tipos correctos y que la configuración Pydantic Settings esté correctamente tipada
- [X] T064 [US4] Agregar script `scripts/run-typecheck.sh` (y su equivalente `scripts/run-typecheck.ps1`) que ejecute basedpyright con formato legible y exit code correcto para CI
- [X] T065 [P] [US4] Agregar basedpyright al pipeline de lint: modificar `scripts/lint.sh` (o crear si no existe) para ejecutar basedpyright después de `ruff check`
- [X] T066 [P] [US4] Agregar basedpyright a los checks de CI en `.github/workflows/`: ejecutar en paralelo con ruff y pytest
- [X] T067 [P] [US4] Configurar basedpyright como LSP en opencode: agregar entrada `lsp.basedpyright` en `~/.config/opencode/opencode.jsonc` (o copia local en `opencode.jsonc`) con command, extensions `["py"]`, y env `PYTHONPATH` apuntando a `src/` — **HECHO**
- [X] T068 [US4] Agregar nota en `CLAUDE.md` sobre el uso de basedpyright: comando para ejecutar, configuración, y políticas de type:ignore

## Phase 7: Testing & Validación de Contrato

Tests que verifican que backend y frontend hablan el mismo idioma, que el mock refleja la realidad, y que los componentes se integran correctamente.

- [X] T069 [P] Escribir test de regresión de naming en `tests/test_contract_naming.py`: verificar que todos los endpoints del backend devuelvan keys en snake_case (para que el transform layer del frontend funcione correctamente)
- [X] T070 [P] Escribir test de integración E2E frontend→backend en `tests/test_e2e_full_flow.py`: simular el flujo completo (start → clarify → approve → SSE → report → graph → metrics) y verificar cada respuesta contra los tipos TypeScript
- [X] T071 [P] Agregar test de SSE events en `tests/test_sse_events.py`: verificar que todos los eventos SSE documentados se emitan en el orden correcto y con la estructura de datos esperada
- [X] T072 [P] Agregar test unitario en `frontend/src/api/__tests__/client.test.ts` para el transform layer: simular respuestas del backend real (snake_case) y verificar que el frontend recibe objetos camelCase
- [X] T073 [P] Agregar test de mock server vs backend en `tests/test_mock_vs_real_contract.py`: para cada ruta, comparar keys y tipos entre mock y backend real, reportando diferencias

## Phase 8: Polish & Cross-Cutting Concerns

Optimizaciones finales, limpieza de código no usado, y mejoras de rendimiento en el frontend.

- [X] T074 [P] Optimizar `GraphCanvas.tsx` en `frontend/src/graph/GraphCanvas.tsx`: memoizar la simulación D3 para evitar reinicios en resize, usando `useRef` para la simulación y solo reiniciando cuando `data` cambie realmente
- [X] T075 [P] Eliminar `analysisStore.ts` duplicación en `frontend/src/state/analysisStore.ts`: si se migró AnalysisView al store, eliminar el estado local redundante
- [X] T076 [P] Limpiar archivo `sse.ts` duplicado en `frontend/src/api/sse.ts`: el hook `useSSE` en `chat/useSSE.ts` tiene su propia implementación de SseClient — unificar ambas o eliminar la no usada
- [X] T077 Actualizar `CLAUDE.md` con documentación del transform layer (snake_case ↔ camelCase), basedpyright, y los hallazgos de la auditoría
- [X] T078 Agregar healthcheck de contrato en `scripts/healthcheck.py`: script CLI que verifica que todos los endpoints del backend respondan con la estructura esperada y reporta discrepancias

---

## Dependencies

### Phase Dependencies
- **Phase 1** (Setup) no tiene dependencias — puede correr en paralelo con Phase 2
- **Phase 2** (Foundational — transform layer) DEBE completarse antes que Phase 3, porque Phase 3 corrige endpoints que dependen del transform layer
- **Phase 3** [US1] (Critical API fixes) puede correr en paralelo con Phase 4 [US2] después de Phase 2
- **Phase 5** [US3] (Mock server) es independiente y puede correr en paralelo con Phases 3-4
- **Phase 6** [US4] (basedpyright) es independiente y puede correr en paralelo con Phases 3-5 (pero DEBE completarse antes que Phase 7, porque los tests de Phase 7 cubren basedpyright)
- **Phase 7** (Testing) DEBE completarse después de Phases 3-6
- **Phase 8** (Polish) debe completarse después de todas las fases anteriores

### Task-Level Dependencies
- T005 (transform functions) debe preceder a T006 y T007 (interceptors) — T006 y T007 pueden correr en paralelo
- T008 (tests de transform) debe esperar T005
- T010 (approvePlan fix) es independiente del transform layer — puede correr en Phase 2 o en paralelo
- T011 (SSE ReportGenerated fix) depende del transform layer (T005-T007) porque usa campos camelCase
- T015-T016 (persistence) son independientes entre sí
- T017 (analysisStore migration) depende de T015 (sessionStatus persistence)
- T037-T051 (mock endpoints, 13 tasks) son todos independientes entre sí — máximo paralelismo
- T056 (instalar basedpyright) DEBE completarse antes que T057 (config) y T058 (baseline)
- T057 (config) DEBE completarse antes que T059-T063 (correcciones por capa)
- T069-T073 (tests de contrato) deben esperar que las correcciones correspondientes estén implementadas (Phases 2-6)
- T074-T078 (polish) deben esperar que todas las fases anteriores estén completas

### Critical Path
```
T005 (transform) → T006+T007 (interceptors) 
                → T010 (approvePlan) 
                → T011 (SSE report) 
                → T012 (metrics) 
                → T013 (follow-up)

T056 (basedpyright install) → T057 (config) → T058 (baseline)
                                                 → T059-T063 (layer fixes) → T064 (scripts) → T065-T066 (CI/lint)
```

---

## Parallel Execution Examples

### Phase 1 + Phase 2 Parallel Block
```
Run T001, T002, T003, T004, T005 in parallel:
  T001: Contract check script
  T002: API endpoints reference
  T003: Mock vs backend test
  T004: VT_AUDIT_MODE flag
  T005: Transform functions (transform.ts)

Then T006+T007 in parallel (both modify client.ts):
  T006: Response interceptor
  T007: Request interceptor
```

### Phase 3 Parallel Block (US1 - Critical API)
```
[Group A - Agent 1]: T010 (endpoints.ts quick fix)
[Group B - Agent 2]: T011 (sseHandlers.ts) → T014 (ReportSummary fix)
[Group C - Agent 3]: T012 (AnalysisView.tsx) 
[Group D - Agent 4]: T013 (ChatView.tsx)
  Groups A, B, C, D run in parallel (all different files)
```

### Phase 4 Parallel Block (US2 - State Management)
```
[Group A - Agent 1]: T015 (useStore persistence) → T016 (reportVariants)
[Group B - Agent 2]: T017 (analysisStore migration) 
[Group C - Agent 3]: T018 (SSE PlanApproved) → T019 (SSE EvaluationComputed)
[Group D - Agent 4]: T020 (restore logic MainLayout) → T021 (conversation mode)
[Group E - Agent 5]: T035 (historyStore persistence) + T036 (graph analytics type)
  Groups A, B, C, D, E run in parallel
```

### Phase 5 Parallel Block (US3 - Mock Server)
```
[Agent 1]: T037 (nodes) + T038 (edges) + T039 (node sources) 
[Agent 2]: T040 (modify) + T041 (ecosystem) + T042 (cross-session search)
[Agent 3]: T043 (decision) + T050 (obsolescence) + T051 (hype)
[Agent 4]: T052 (providers normalize) + T053 (FusionProgress SSE) + T054 (BranchFailed SSE) + T055 (EvalComputed SSE)
  All tasks in Phase 5 are P-tagged and can run in parallel
```

### Phase 6 Parallel Block (US4 - basedpyright)
```
[Agent 1]: T056 (install, done) → T057 (config, done) → T058 (baseline capture)
Then T059 (domain fixes) + T060 (api/routes fixes) + T061 (application fixes) + T062 (infra fixes) + T063 (settings/deps fixes)
  All layer fixes run in parallel (different directories)
Then T064 (scripts) + T065 (lint pipeline) + T066 (CI) + T067 (LSP config, done) + T068 (CLAUDE.md)
  All in parallel
```

### Phase 7 Parallel Block (Testing)
```
T069 (naming test), T070 (E2E flow test), T071 (SSE test), T072 (transform test), T073 (mock vs real test)
  All independent — run simultaneously
```

### Phase 8 Parallel Block (Polish)
```
T074 (D3 optimization), T075 (cleanup analysisStore), T076 (unify SSE)
  All independent — run simultaneously
Then T077 (CLAUDE.md) + T078 (healthcheck)
```

---

## Implementation Strategy

1. **Tier 0 — Setup (Phase 1)**: Crear scripts de verificación y documentación de línea base. Paralelo con Tier 1.

2. **Tier 1 — Fundación (Phase 2)**: Implementar el transform layer snake_case↔camelCase. **Esta es la pieza más crítica** — sin esto, nada funciona contra el backend real. Debe probarse exhaustivamente con T008.

3. **Tier 2 — Contratos Críticos (Phase 3) [US1]**: Corregir los 4 issues críticos (C1-C4 del audit). Cada uno es independiente y puede asignarse a un agente diferente. El transform layer de Tier 1 ya debe estar activo.

4. **Tier 3 — Estado y Flujo (Phase 4) [US2]**: Mejorar la persistencia del estado frontend y agregar los manejadores SSE faltantes. Puede correr en paralelo con Tier 2.

5. **Tier 4 — Mock Completo (Phase 5) [US3]**: Implementar los 11 endpoints faltantes en el mock server. Totalmente independiente. Puede correr en paralelo con Tiers 2-3.

6. **Tier 5 — Type Checking (Phase 6) [US4]**: basedpyright instalado (T044-T045 ya hechos), capturar baseline, corregir errores por capa, integrar en CI. Independiente — puede correr en paralelo con Tiers 2-4, pero DEBE completarse antes de Tier 6.

7. **Tier 6 — Validación (Phase 7)**: Tests de contrato y regresión. Debe esperar a que Tiers 2-5 estén completos.

8. **Tier 7 — Calidad (Phase 8)**: Optimizaciones y limpieza final. Depende de todo lo anterior.

### Resumen de esfuerzo

| Tier | Fases | Tasks | Agentes recomendados | Depende de |
|------|-------|-------|---------------------|------------|
| Tier 0 | Phase 1 | T001-T004 | 4 en paralelo | — |
| Tier 1 | Phase 2 | T005-T009 | 3 en secuencia+paralelo | — |
| Tier 2 | Phase 3 [US1] | T010-T014 | 4 en paralelo | Tier 1 |
| Tier 3 | Phase 4 [US2] | T015-T018, T035-T036 | 5 en paralelo | Tier 1 |
| Tier 4 | Phase 5 [US3] | T037-T055 | 4 en paralelo | — |
| Tier 5 | Phase 6 [US4] | T056-T068 | 3 capas+CI en paralelo | — (indep. de Tiers 2-4) |
| Tier 6 | Phase 7 | T069-T073 | 5 en paralelo | Tiers 2-5 |
| Tier 7 | Phase 8 | T074-T078 | 3+1 en paralelo+secuencia | Tiers 2-6 |
