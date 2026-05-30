# Tasks: Fase F0 — Auditoria Baseline y Estrategia de Migracion

**Input**: `specs/019-fase-F0-auditoria-baseline/spec.md`, `specs/019-fase-F0-auditoria-baseline/plan.md`
**Feature**: Auditoria completa del entorno 2.0, validacion de supuestos A1-A14, auditoria de licencias, matriz de migracion y plan de rollback. Fase puramente documental — cero codigo de producto.

**Relacion con spec 009**: El spec 009 (MVP Foundation) cubrio F0+F1 como bloque conjunto. Su Phase 1 ya creo estructura de carpetas, verifico MigrationRunner, `docs/audit-licenses.md` (esqueleto) y valido entorno basico. Este spec (019) **extiende** F0 con el detalle operativo que 009 no cubrio: baseline formal, validacion exhaustiva de supuestos, auditoria de licencias completa, matriz preservar/extender/nuevo formalizada, plan de rollback por fase y criterios go/no-go explicitos.

**Testing strategy**: F0 no produce codigo de producto. La verificacion es documental: cada artefacto tiene criterios de completitud medibles (cobertura 100% de filas, estados binarios por supuesto, procedimientos por fase). El unico test ejecutable es confirmar que los tests del 2.0 siguen pasando al cierre (cero regresiones).

---

## Phase 1: Registro de baseline del 2.0

Objetivo: capturar el estado actual del 2.0 como punto de referencia inmutable antes de cualquier cambio del 3.0.

**Independent Test Criteria**: `docs/f0-baseline.md` existe con todas las secciones completas (resultados pytest, conteo ruff, conteo basedpyright, versiones runtime, fecha); los valores registrados coinciden con la ejecucion real.

- [ ] T001 Ejecutar `pytest` sobre el codigo del 2.0 y registrar resultados (tests pasando, fallando, skipped, duracion) en `docs/f0-baseline.md` seccion "Resultados pytest"
- [ ] T002 [P] Ejecutar `ruff check .` y registrar conteo de errores/warnings por categoria en `docs/f0-baseline.md` seccion "Analisis ruff"
- [ ] T003 [P] Ejecutar `basedpyright` y registrar conteo de errores/warnings en `docs/f0-baseline.md` seccion "Analisis basedpyright"
- [ ] T004 [P] Registrar versiones de runtime en `docs/f0-baseline.md` seccion "Versiones": `python --version`, `psql --version`, `SELECT version()`, `SELECT extversion FROM pg_extension WHERE extname='vector'`, sistema operativo, espacio en disco
- [ ] T005 Consolidar `docs/f0-baseline.md` con formato tabla, fecha de ejecucion y nota de inmutabilidad. Distinguir fallos preexistentes (no bloqueantes) de fallos nuevos (bloqueantes)

**Traza**: FR-001, FR-002, FR-003. SC-004.

---

## Phase 2: Validacion de supuestos A1-A14

Objetivo: evaluar cada supuesto del plan con prueba concreta y registrar resultado como VALIDADO o DESMENTIDO con evidencia.

**Independent Test Criteria**: `docs/f0-supuestos-validacion.md` contiene 14 filas completas; cada fila tiene estado (VALIDADO/DESMENTIDO), metodo de validacion, evidencia y accion correctiva si aplica; cero supuestos sin evaluar.

- [ ] T006 Crear `docs/f0-supuestos-validacion.md` con estructura de tabla: columnas ID, Supuesto, Metodo, Resultado, Evidencia, Accion Correctiva
- [ ] T007 [P] Validar A1 (MiniMax M-2.5 via misma API): verificar documentacion/endpoint de info MiniMax; registrar respuesta o error en `docs/f0-supuestos-validacion.md`
- [ ] T008 [P] Validar A2 (CrewAI 0.x soporta clientes OpenAI-compatible custom): instalar crewai en venv aislado, verificar que acepta `base_url` custom; registrar version + resultado en `docs/f0-supuestos-validacion.md`
- [ ] T009 [P] Validar A3/A12 (TurboVec en Windows 11): ejecutar `pip install turbovec` en venv aislado; registrar exito/fallo con version y traceback en `docs/f0-supuestos-validacion.md`
- [ ] T010 [P] Validar A4 (MCPs a internalizar tienen licencias compatibles): inspeccionar headers de MCPs candidatos a internalizacion; registrar licencia por MCP en `docs/f0-supuestos-validacion.md`
- [ ] T011 [P] Validar A5 (Tools de Hermes MIT-compatibles): inspeccionar headers de ~30 archivos en `documentation/hermes agent/hermes-agent/tools/`; registrar licencia detectada por archivo en `docs/f0-supuestos-validacion.md`
- [ ] T012 [P] Validar A6 (BAAI/bge-m3 en CPU < 200ms): instalar sentence-transformers + modelo en venv, ejecutar benchmark batch 10 textos; registrar latencia p50/p95 en `docs/f0-supuestos-validacion.md`
- [ ] T013 [P] Validar A7 (Presidio soporta espanol + ingles): instalar presidio-analyzer + es_core_news_md, ejecutar deteccion sobre texto de prueba en espanol; registrar resultado en `docs/f0-supuestos-validacion.md`
- [ ] T014 [P] Validar A8 (OAuth providers permiten scopes sin delete): revisar documentacion Google Workspace OAuth y Microsoft Graph; registrar scopes disponibles en `docs/f0-supuestos-validacion.md`
- [ ] T015 [P] Validar A9 (Cambios quirurgicos, cero renombres): verificacion documental contra constitucion v1.2.0; registrar referencia en `docs/f0-supuestos-validacion.md`
- [ ] T016 [P] Validar A10 (Capacidad de ejecucion 12-16 sem): evaluar progreso actual vs cronograma; registrar estimacion actualizada en `docs/f0-supuestos-validacion.md`
- [ ] T017 [P] Validar A11 (MigrationRunner aplica DDL con columnas vector(N) + UUIDv7): ejecutar `CREATE TABLE test_a11 (id uuid DEFAULT uuidv7(), vec vector(1536))` en metadata DB; registrar exito/fallo en `docs/f0-supuestos-validacion.md`
- [ ] T018 [P] Validar A13 (pgvector 0.8+ instalado): ejecutar `SELECT extversion FROM pg_extension WHERE extname='vector'`; registrar version exacta en `docs/f0-supuestos-validacion.md`
- [ ] T019 [P] Validar A14 (uuidv7() disponible nativamente en PG 18): ejecutar `SELECT uuidv7()`; registrar resultado o error en `docs/f0-supuestos-validacion.md`
- [ ] T020 Para cada supuesto DESMENTIDO: documentar impacto en fases posteriores, plan B disponible y decision requerida en `docs/f0-supuestos-validacion.md` seccion "Acciones Correctivas"

**Traza**: FR-004, FR-005, FR-006, FR-007, FR-008, FR-009. SC-001.

---

## Phase 3: Auditoria de licencias

Objetivo: documentar licencia y compatibilidad de todo archivo/paquete que entrara al 3.0. Extiende el esqueleto creado por spec 009 T007.

**Independent Test Criteria**: `docs/audit-licenses.md` tiene 3 secciones completas (COPY-HERMES, PyPI, MCPs); cobertura 100% de los ~30 archivos Hermes, ~10 paquetes PyPI y 15 MCPs; cero filas con estado "pendiente".

- [ ] T021 Completar seccion "Hermes copies" en `docs/audit-licenses.md` (extiende esqueleto creado por spec 009 T007): para cada archivo en `documentation/hermes agent/hermes-agent/tools/` registrar path origen, path destino previsto en `enterprise/`, licencia detectada, compatible MIT/Apache-2.0 (si/no), accion (copiar/excluir/alternativa), atribucion requerida
- [ ] T022 [P] Completar seccion "New PyPI dependencies" en `docs/audit-licenses.md` (extiende esqueleto creado por spec 009 T007): para cada paquete previsto en F1 (openai, cryptography, apscheduler, prometheus-client, opentelemetry-api, opentelemetry-sdk, sentence-transformers, presidio-analyzer, python-docx, weasyprint) registrar nombre, version minima, licencia, compatible (si/no), accion
- [ ] T023 [P] Agregar seccion "MCPs externos Tier 2" en `docs/audit-licenses.md` (extiende esqueleto creado por spec 009 T007): para cada MCP preservado del 2.0 en `infra/mcp/mcp-providers.json` registrar nombre, licencia, compatible (si/no)
- [ ] T024 Para cada archivo o paquete incompatible (GPL, AGPL, SSPL u otra copyleft): registrar alternativa propuesta e impacto en cronograma en `docs/audit-licenses.md` (extiende esqueleto creado por spec 009 T007) seccion "Incompatibilidades y Alternativas"

**Traza**: FR-010, FR-011, FR-012, FR-013, FR-014. SC-002.

---

## Phase 4: Matriz preservar/extender/nuevo

Objetivo: formalizar la clasificacion de componentes del 2.0 como artefacto verificable referenciando doc 07-migracion.

**Independent Test Criteria**: `docs/migration-matrix.md` tiene 3 secciones (PRESERVAR, EXTENDER, CREAR NUEVO); cada componente de secciones A/B/C del doc 07 esta cubierto; componentes PRESERVAR verificados como existentes en el repo; componentes EXTENDER con punto de extension identificado.

- [ ] T025 Crear `docs/migration-matrix.md` con estructura de 3 secciones y columnas por categoria
- [ ] T026 Completar seccion PRESERVAR en `docs/migration-matrix.md`: listar cada componente de seccion A del doc 07 con ubicacion exacta en el repo, razon de preservacion y confirmacion de existencia fisica
- [ ] T027 [P] Completar seccion EXTENDER en `docs/migration-matrix.md`: listar cada componente de seccion B del doc 07 con ubicacion, tipo de extension prevista (subclase/adapter/parametro opcional) y fase de materializacion (F1-F5)
- [ ] T028 [P] Completar seccion CREAR NUEVO en `docs/migration-matrix.md`: listar cada componente de seccion C del doc 07 con ubicacion destino en `enterprise/`, fase de creacion y dependencias de componentes preservados/extendidos
- [ ] T029 Verificar integridad de `docs/migration-matrix.md`: confirmar que cada componente PRESERVAR existe fisicamente; cada componente EXTENDER tiene punto de extension identificado (port, clase base o interfaz). Registrar resultado de verificacion al final del documento

**Traza**: FR-015, FR-016, FR-017, FR-018. SC-003.

---

## Phase 5: Plan de rollback por fase

Objetivo: documentar procedimiento de reversion para cada fase F0-F5 garantizando que el 2.0 queda intacto post-rollback.

**Independent Test Criteria**: `docs/rollback-plan.md` cubre F0, F1, F2, F3a, F3b, F4a, F4b, F4c, F5a, F5b, F5c, F5d con riesgo principal, procedimiento paso a paso y estado post-rollback; cada procedimiento garantiza que el 2.0 funciona identico al baseline.

- [ ] T030 Crear `docs/rollback-plan.md` con tabla resumen (fase, riesgo, complejidad de reversion) y secciones detalladas por fase
- [ ] T031 Documentar rollback de F0 en `docs/rollback-plan.md`: descartar documentos generados y estructura de carpetas vacias; sin impacto en codigo ni DB
- [ ] T032 [P] Documentar rollback de F1 en `docs/rollback-plan.md`: DROP de tablas enterprise + eliminar `enterprise/`; tests del 2.0 siguen pasando
- [ ] T033 [P] Documentar rollback de F2-F5 (sub-fases) en `docs/rollback-plan.md`: procedimiento especifico por sub-fase segun artefactos (config flags, migration downgrade, eliminacion de archivos enterprise)
- [ ] T034 Verificar coherencia de `docs/rollback-plan.md`: cada procedimiento referencia el baseline de Phase 1 como estado objetivo post-rollback

**Traza**: FR-019, FR-020, FR-021. SC-005.

---

## Phase 6: Criterios go/no-go y cierre de F0

Objetivo: evaluar si F1 puede comenzar basandose en los resultados de Phases 1-5.

**Independent Test Criteria**: seccion go/no-go en `docs/f0-baseline.md` con decision explicita (GO o NO-GO); cada criterio evaluado contra evidencia de fases anteriores; tests del 2.0 confirmados sin regresiones al cierre.

- [ ] T035 Agregar seccion "Criterios Go/No-Go" en `docs/f0-baseline.md` con checklist: (a) tests 2.0 sin regresiones nuevas, (b) metadata DB compatible con migraciones SQL del 2.0 (A11), (c) pgvector >= 0.8.0 (A13), (d) uuidv7() disponible (A14), (e) 100% archivos COPY-HERMES con licencia compatible o alternativa, (f) supuestos criticos de infraestructura validados
- [ ] T036 Evaluar cada criterio go/no-go contra resultados de Phases 1-5 y registrar estado (CUMPLE/NO CUMPLE) con referencia a evidencia en `docs/f0-baseline.md`
- [ ] T037 Ejecutar `pytest` final para confirmar cero regresiones introducidas por F0 y registrar resultado en `docs/f0-baseline.md` seccion "Verificacion de cierre"
- [ ] T038 Registrar decision final en `docs/f0-baseline.md`: "GO — F1 autorizado" con fecha, o "NO-GO" con criterio fallido, accion correctiva, responsable y fecha limite de re-evaluacion

**Traza**: FR-022, FR-023, FR-024. SC-004, SC-006, SC-007.

---

## Dependencies

- **Phase 1** must complete before **Phase 2** (el baseline es referencia para validar supuestos).
- **Phase 1** must complete before **Phase 5** (el rollback referencia el baseline como estado objetivo).
- **Phase 2** must complete before **Phase 6** (go/no-go evalua resultados de supuestos).
- **Phase 3** must complete before **Phase 6** (go/no-go evalua cobertura de licencias).
- **Phase 4** must complete before **Phase 6** (go/no-go requiere matriz completa).
- **Phase 5** must complete before **Phase 6** (go/no-go requiere rollback documentado).
- **Phases 2, 3 y 4** son independientes entre si y pueden ejecutarse en paralelo tras Phase 1.
- Dentro de Phase 2: T006 debe completarse antes que T007-T019; T020 requiere que T007-T019 esten completos.
- Dentro de Phase 3: T021, T022, T023 son independientes; T024 requiere que T021-T023 esten completos.
- Dentro de Phase 4: T025 debe completarse antes que T026-T028; T029 requiere T026-T028 completos.
- Dentro de Phase 5: T030 debe completarse antes que T031-T033; T034 requiere T031-T033 completos.
- Dentro de Phase 6: T035 antes que T036; T036 y T037 antes que T038.

## Parallel Execution Examples

### Phase 1 Parallel Block

- Run T002, T003, T004 en paralelo (herramientas distintas, archivos distintos).
- T001 y T005 son secuenciales (T001 primero, T005 consolida al final).

### Phases 2, 3, 4 Parallel Block (tras Phase 1)

- Run Phase 2 (T006-T020), Phase 3 (T021-T024) y Phase 4 (T025-T029) en paralelo por desarrolladores distintos.

### Phase 2 Internal Parallel Block

- Tras T006, run T007-T019 en paralelo (cada supuesto es independiente, mismo archivo pero secciones distintas).

### Phase 3 Internal Parallel Block

- Run T021, T022, T023 en paralelo (secciones distintas del mismo documento).

### Phase 4 Internal Parallel Block

- Tras T025, run T026, T027, T028 en paralelo (secciones distintas del mismo documento).

### Phase 5 Internal Parallel Block

- Tras T030, run T031, T032, T033 en paralelo (secciones distintas del mismo documento).

---

## Implementation Strategy

1. **Cerrar Phase 1 primero**: ejecutar herramientas de analisis y registrar baseline inmutable. Esto establece el punto de referencia para todo lo demas.
2. **Ejecutar Phases 2, 3 y 4 en paralelo**: son independientes entre si. Distribuir entre operadores si hay disponibilidad. Phase 2 es la mas larga (5-7 dias); Phases 3 y 4 son mas cortas (2-4 dias cada una).
3. **Phase 5 puede comenzar tras Phase 1**: solo necesita el baseline como referencia. Puede ejecutarse en paralelo con Phases 2-4.
4. **Phase 6 cierra F0**: requiere que todas las fases anteriores esten completas. Es la evaluacion final que autoriza o bloquea F1.
5. **Cero codigo de producto**: todas las tareas producen documentos en `docs/`. Si alguna validacion requiere ejecutar comandos (pip install, psql, pytest), se hace en entorno aislado sin modificar el repositorio.
6. **Distincion con spec 009**: este spec NO repite la creacion de carpetas vacias, verificacion de MigrationRunner ni esqueleto de `docs/audit-licenses.md` (ya cubiertos por 009 T005-T009). Extiende con contenido completo y artefactos nuevos.

---

## Format Validation

Todas las tareas T001-T038 siguen el formato requerido:
- Checkbox `- [ ]` al inicio.
- Task ID secuencial (T001-T038).
- Marcador `[P]` solo en tareas paralelizables (diferentes archivos o secciones independientes del mismo archivo).
- Descripcion con accion + path concreto del archivo destino.
- Traza a FR y SC del spec por fase.

**Total task count**: 38 tareas.
**Task count per phase**:
- Phase 1 (Baseline): 5
- Phase 2 (Supuestos): 15
- Phase 3 (Licencias): 4
- Phase 4 (Matriz): 5
- Phase 5 (Rollback): 5
- Phase 6 (Go/No-Go): 4

**Scope**: este spec es puramente documental (SC-007). No hay MVP vs roadmap — todas las tareas son prerequisito para autorizar F1.
