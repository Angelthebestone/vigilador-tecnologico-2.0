# Feature Specification: Fase F0 — Auditoria Baseline y Estrategia de Migracion 2.0 a 3.0

**Feature ID**: 019-fase-F0-auditoria-baseline
**Created**: 2026-05-29
**Status**: Draft (specification phase)
**Related plan documents**:
- [plan vigilador 3.0/07-migracion-2.0-a-3.0.md](../../plan%20vigilador%203.0/07-migracion-2.0-a-3.0.md) (fuente principal: matriz preservar/extender/nuevo + fases F0-F5 + rollback)
- [plan vigilador 3.0/00b-mvp-scope-y-cronograma.md](../../plan%20vigilador%203.0/00b-mvp-scope-y-cronograma.md) (scope MVP vs roadmap)
- [plan vigilador 3.0/00-canon-operativo-corregido.md](../../plan%20vigilador%203.0/00-canon-operativo-corregido.md) (canon C0)

---

## Problem Statement

La evolucion del Vigilador Tecnologico 2.0 al 3.0 requiere una fase preparatoria (F0) que valide los supuestos tecnicos del plan antes de escribir codigo de producto. Sin esta validacion, las fases posteriores (F1-F5) podrian construirse sobre premisas falsas — por ejemplo, que TurboVec funciona en Windows 11, que las licencias de archivos Hermes son compatibles, o que la metadata DB soporta las migraciones previstas.

El spec 009 (MVP Foundation) ya cubrio la **definicion** de F0 y F1 como scope conjunto, incluyendo los requisitos funcionales FR-001 a FR-004 para F0 (validar DB, generar audit-licenses.md, crear carpetas vacias, verificar MigrationRunner). Sin embargo, 009 trato F0 como un bloque de setup subordinado a F1 y no especifico:

1. El procedimiento detallado de validacion de cada supuesto A1-A14.
2. La clasificacion formal de la matriz preservar/extender/nuevo como artefacto verificable.
3. El plan de rollback por fase como documento operativo.
4. Los criterios de go/no-go que determinan si F1 puede comenzar.

Este spec (019) complementa a 009 profundizando exclusivamente en F0: la auditoria de licencias, la validacion de supuestos, la documentacion de la matriz de migracion y el plan de rollback. No redefine lo que 009 ya cubrio; lo extiende con el detalle operativo necesario para ejecutar F0 de forma autonoma.

---

## Scope Boundaries

### In Scope

- **Validacion de supuestos A1-A14**: procedimiento de verificacion para cada supuesto con criterio de exito/fallo y accion correctiva documentada.
- **Auditoria de licencias**: proceso formal para los ~30 archivos COPY-HERMES, ~10 paquetes PyPI nuevos de F1 y los 15 MCPs externos Tier 2 preservados.
- **Matriz preservar/extender/nuevo como artefacto**: documento verificable que clasifica cada componente del 2.0 segun su tratamiento en la migracion.
- **Plan de rollback por fase**: documento operativo con procedimiento de reversion para F0-F5.
- **Criterios go/no-go de F0**: condiciones que deben cumplirse para autorizar el inicio de F1.
- **Baseline del 2.0**: ejecucion y registro del estado actual de tests, linting y estructura como punto de referencia inmutable.

### Out of Scope

- **Implementacion de codigo de producto**: F0 no produce codigo funcional; eso es F1+ (spec 009).
- **Creacion de carpetas enterprise/ y config/**: ya especificado en spec 009 FR-003.
- **Verificacion de MigrationRunner**: ya especificado en spec 009 T009.
- **Setup de Prometheus/OpenTelemetry stubs**: ya especificado en spec 009 FR-030/FR-031.
- **Cualquier componente de F1-F5**: adapter LLM, ToolRegistry, HealthMonitor, frontend, modos, playbooks, ingestion, dreaming.
- **Decisiones de arquitectura nuevas**: F0 valida supuestos existentes, no introduce decisiones nuevas.

---

## Relacion con spec 009

El spec 009 definio F0+F1 como un bloque unico. Este spec (019) **no duplica ni contradice** a 009. La relacion es:

| Aspecto | Cubierto por 009 | Extendido por 019 |
|---|---|---|
| FR-001 (validar DB) | Si — requisito funcional | Procedimiento detallado de validacion |
| FR-002 (audit-licenses.md) | Si — requisito funcional | Proceso formal con criterios de inclusion/exclusion |
| FR-003 (carpetas vacias) | Si — requisito funcional | No (ya completo en 009) |
| FR-004 (MigrationRunner init) | Si — requisito funcional | No (ya completo en 009) |
| Supuestos A1-A14 | Mencionados en Assumptions | Procedimiento de validacion por supuesto |
| Matriz preservar/extender/nuevo | Referenciada | Formalizada como artefacto verificable |
| Plan de rollback | Mencionado en doc fuente | Formalizado con procedimientos |
| Criterios go/no-go | Implicitos | Explicitos y medibles |
| Baseline del 2.0 | Implicito (tests deben pasar) | Registro formal del estado inicial |

---

## Assumptions

- **A-01**: El repositorio del 2.0 esta en estado funcional: `pytest` pasa, `ruff` y `basedpyright` no reportan errores nuevos. Si no es asi, la primera tarea de F0 es estabilizar antes de registrar baseline.
- **A-02**: El operador tiene acceso a la metadata DB PostgreSQL del 2.0 con permisos para ejecutar queries de diagnostico (`SELECT version()`, `SELECT extversion FROM pg_extension`, `SELECT uuidv7()`).
- **A-03**: Los archivos fuente de Hermes estan disponibles en `documentation/hermes agent/hermes-agent/tools/` para inspeccion de licencias (no se copian en F0, solo se auditan).
- **A-04**: El operador tiene conectividad de red hacia `platform.xiaomimimo.com` para validar A-supuesto sobre el nuevo LLM (validacion de conectividad, no implementacion del adapter).
- **A-05**: El entorno target es Windows 11 con Python 3.11+ y PostgreSQL 18 con pgvector 0.8+.

---

## User Scenarios & Testing

### Primary User Story

Como **ingeniero responsable de la migracion 2.0 a 3.0**, quiero **ejecutar una auditoria completa del entorno y las dependencias antes de escribir codigo**, para tener certeza de que los supuestos del plan son validos y que la migracion puede proceder sin riesgos ocultos.

### Acceptance Scenarios

1. **Given** el repositorio del 2.0 en su estado actual, **When** ejecuto la bateria de tests + linting del 2.0, **Then** obtengo un registro inmutable (archivo o commit tag) del estado baseline con: numero de tests pasando, warnings de linting, version de Python, version de PostgreSQL, version de pgvector, espacio en disco.

2. **Given** la metadata DB del 2.0 corriendo, **When** ejecuto las queries de validacion de supuestos A11/A13/A14, **Then** obtengo confirmacion de que el MigrationRunner puede aplicar DDL con columnas vector, que pgvector >= 0.8.0 esta instalado y que `uuidv7()` funciona nativamente.

3. **Given** los ~30 archivos candidatos COPY-HERMES identificados en el inventario de extraccion, **When** inspecciono el header de licencia de cada uno, **Then** genero una tabla en `docs/audit-licenses.md` con: archivo origen, licencia detectada, compatibilidad MIT/Apache-2.0, accion (copiar/excluir/buscar alternativa).

4. **Given** los ~10 paquetes PyPI nuevos previstos para F1, **When** consulto sus licencias en PyPI/GitHub, **Then** documento cada uno en `docs/audit-licenses.md` con: paquete, version, licencia, compatibilidad, accion.

5. **Given** todos los supuestos A1-A14 evaluados, **When** reviso el documento de validacion, **Then** cada supuesto tiene estado VALIDADO o DESMENTIDO con evidencia y accion correctiva si aplica.

6. **Given** la matriz preservar/extender/nuevo documentada, **When** la comparo con el estado real del repositorio, **Then** cada componente listado como "preservar" existe y no tiene modificaciones pendientes; cada componente "extender" tiene su punto de extension identificado.

7. **Given** todos los criterios go/no-go de F0 evaluados, **When** al menos los criterios criticos (DB funcional, licencias compatibles, tests baseline pasando) se cumplen, **Then** F1 puede comenzar sin bloqueos conocidos.

### Edge Cases

- **EC-01**: Un supuesto se desmiente (ej: TurboVec no compila en Windows 11) — el documento de validacion registra el fallo, la accion correctiva (plan B documentado en decision #85) y el impacto en fases posteriores.
- **EC-02**: Un archivo COPY-HERMES tiene licencia incompatible (ni MIT ni Apache-2.0) — se excluye del inventario, se documenta la alternativa y se actualiza el plan de F3.
- **EC-03**: La metadata DB no tiene pgvector 0.8+ — se documenta el procedimiento de upgrade (`ALTER EXTENSION vector UPDATE TO '0.8.0'`) como prerequisito de F1.
- **EC-04**: `uuidv7()` no esta disponible (PG < 18) — se documenta como bloqueante para F1 y se requiere upgrade de PostgreSQL antes de continuar.
- **EC-05**: Tests del 2.0 fallan en el baseline — se registra el estado como-esta, se distingue entre fallos preexistentes (no bloqueantes) y fallos nuevos (bloqueantes).

---

## Functional Requirements

### Registro de baseline del 2.0

- **FR-001**: El proceso de F0 MUST ejecutar `pytest` sobre el codigo del 2.0 y registrar el resultado (tests pasando, tests fallando, tests skipped) en un documento de baseline (`docs/f0-baseline.md`).
- **FR-002**: El proceso de F0 MUST ejecutar `ruff` y `basedpyright` sobre el codigo del 2.0 y registrar el conteo de errores/warnings como referencia inmutable.
- **FR-003**: El documento de baseline MUST incluir: version de Python, version de PostgreSQL, version de pgvector, sistema operativo, fecha de ejecucion.

### Validacion de supuestos A1-A14

- **FR-004**: El proceso de F0 MUST validar cada supuesto A1-A14 del plan con una prueba concreta y registrar el resultado como VALIDADO o DESMENTIDO con evidencia.
- **FR-005**: Para supuestos de infraestructura DB (A11, A13, A14), la validacion MUST ejecutar queries reales contra la metadata DB: `SELECT version()`, `SELECT extversion FROM pg_extension WHERE extname='vector'`, `SELECT uuidv7()`.
- **FR-006**: Para supuestos de compatibilidad de paquetes (A1, A2, A3, A6), la validacion MUST intentar la instalacion o import en un entorno aislado (venv) y registrar exito/fallo con version.
- **FR-007**: Para supuestos de licencias (A4, A5), la validacion MUST inspeccionar headers de archivos fuente y metadata de paquetes PyPI, registrando licencia detectada por archivo/paquete.
- **FR-008**: Para supuestos de conectividad y APIs (A7, A8), la validacion MUST ejecutar una llamada de prueba minima (health check o endpoint de info) y registrar respuesta/error.
- **FR-009**: Para cada supuesto DESMENTIDO, el documento MUST incluir: impacto en fases posteriores, plan B disponible (si existe en el plan), y decision requerida antes de continuar.

### Auditoria de licencias

- **FR-010**: El proceso de F0 MUST generar `docs/audit-licenses.md` con una tabla que cubra el 100% de los archivos candidatos COPY-HERMES (~30 archivos segun inventario de extraccion, decision #54).
- **FR-011**: Cada fila de la tabla de licencias MUST incluir: archivo origen (path relativo en Hermes), archivo destino previsto en enterprise/, licencia detectada (MIT/Apache-2.0/otra), compatible (si/no), accion (copiar/excluir/alternativa), atribucion requerida.
- **FR-012**: El proceso de F0 MUST auditar los paquetes PyPI nuevos previstos para F1 (~10 paquetes) con: nombre, version, licencia, compatible (si/no), accion.
- **FR-013**: El proceso de F0 MUST auditar los 15 MCPs externos Tier 2 preservados del 2.0 con: nombre, licencia, compatible (si/no). Estos ya estan en uso pero la auditoria formaliza su estado.
- **FR-014**: Si un archivo o paquete resulta incompatible, el documento MUST registrar la alternativa propuesta y el impacto en el cronograma.

### Matriz preservar/extender/nuevo

- **FR-015**: El proceso de F0 MUST producir un documento verificable (`docs/migration-matrix.md`) que clasifique cada componente significativo del 2.0 en una de tres categorias: PRESERVAR (no tocar), EXTENDER (OCP sin modificar existente), CREAR NUEVO (en enterprise/).
- **FR-016**: La categoria PRESERVAR MUST listar: componente, ubicacion, razon de preservacion, y confirmacion de que existe y funciona en el baseline.
- **FR-017**: La categoria EXTENDER MUST listar: componente, ubicacion, tipo de extension prevista (subclase, adapter, parametro opcional), y fase en que se materializa.
- **FR-018**: La categoria CREAR NUEVO MUST listar: componente, ubicacion destino en enterprise/, fase en que se crea, y dependencias de componentes preservados/extendidos.

### Plan de rollback

- **FR-019**: El proceso de F0 MUST documentar un plan de rollback por fase (F0-F5) en `docs/rollback-plan.md` o equivalente, con: riesgo principal, procedimiento de reversion, y estado esperado post-rollback.
- **FR-020**: El plan de rollback MUST garantizar que en cualquier fase, la reversion deja el 2.0 funcionando identico al baseline registrado en FR-001/FR-002/FR-003.
- **FR-021**: Para F0 especificamente, el rollback MUST ser trivial: descartar estructura de carpetas vacias y documentos generados, sin impacto en codigo ni DB.

### Criterios go/no-go

- **FR-022**: El proceso de F0 MUST definir criterios explicitos de go/no-go para autorizar el inicio de F1, documentados en el baseline o en documento separado.
- **FR-023**: Los criterios go MUST incluir como minimo: (a) tests del 2.0 sin regresiones nuevas, (b) metadata DB compatible con migraciones SQL del 2.0, (c) 100% de archivos COPY-HERMES con licencia compatible o alternativa documentada, (d) supuestos criticos (A11, A13, A14) validados.
- **FR-024**: Si un criterio go critico falla, el documento MUST registrar la decision: replantear, buscar alternativa, o escalar.

---

## Key Entities

- **Documento de baseline (`docs/f0-baseline.md`)**: registro inmutable del estado del 2.0 antes de cualquier cambio del 3.0. Atributos: fecha, versiones de runtime, resultados de tests, conteo de linting.
- **Documento de auditoria de licencias (`docs/audit-licenses.md`)**: tabla de archivos y paquetes con su licencia y decision. Ya referenciado en spec 009 FR-002.
- **Documento de matriz de migracion (`docs/migration-matrix.md`)**: clasificacion formal de componentes en preservar/extender/nuevo.
- **Documento de rollback (`docs/rollback-plan.md`)**: procedimientos de reversion por fase.
- **Registro de validacion de supuestos**: puede ser seccion del baseline o documento separado; contiene estado VALIDADO/DESMENTIDO por supuesto con evidencia.

---

## Success Criteria

- **SC-001**: El 100% de los supuestos A1-A14 tienen estado VALIDADO o DESMENTIDO con evidencia documentada al cierre de F0.
- **SC-002**: El documento `docs/audit-licenses.md` cubre el 100% de archivos COPY-HERMES candidatos y el 100% de paquetes PyPI nuevos previstos para F1, sin filas pendientes.
- **SC-003**: La matriz preservar/extender/nuevo cubre todos los componentes listados en la seccion A/B/C del doc 07-migracion, sin omisiones.
- **SC-004**: Los tests del 2.0 registrados en el baseline siguen pasando al 100% al cierre de F0 (cero regresiones introducidas por F0).
- **SC-005**: El plan de rollback cubre las 6 fases (F0-F5) con procedimiento concreto por fase.
- **SC-006**: Los criterios go/no-go estan documentados y evaluados; F1 tiene autorizacion explicita o bloqueo documentado.
- **SC-007**: F0 se completa sin producir codigo de producto — solo documentos, estructura de carpetas vacias y configuracion de herramientas.

---

## Delivery Constraints

- **Constitucion v1.2.0 — Pensar antes de codificar (#1)**: F0 es la materializacion de este principio. Supuestos explicitos, validados con prueba antes de implementar.
- **Constitucion v1.2.0 — Cambios quirurgicos (#5)**: F0 no toca codigo del 2.0. Cero modificaciones a archivos existentes.
- **Constitucion v1.2.0 — Entrega verificable (#6)**: cada supuesto tiene criterio de exito verificable; el cierre de F0 requiere evidencia por supuesto.
- **Principio rector del doc 07**: cero breaking changes al 2.0. La API `/api/v2/research/*` y los 6 agentes de rama no se tocan.
- **CLAUDE.md**: trabajar directamente sobre `main`; cero feature branches automaticas.
- **Duracion estimada**: 2-3 semanas segun cronograma MVP (00b).
- **Rollback F0**: trivial. Si F0 falla, cero codigo nuevo que revertir; solo se descarta estructura vacia y documentos.

---

## Traceability Matrix

| FR | Acceptance scenario | Success criterion | Fuente en doc 07 |
|----|---------------------|-------------------|-------------------|
| FR-001 | AS-1 | SC-004 | F0 criterios verificables: "tests/ del 2.0 siguen pasando 100%" |
| FR-002 | AS-1 | SC-004 | F0 criterios verificables: "CI corre ruff + basedpyright" |
| FR-003 | AS-1 | SC-004 | Implicito en baseline |
| FR-004 | AS-5 | SC-001 | F0 tarea: "validar supuestos A1-A14" |
| FR-005 | AS-2 | SC-001 | F0 tareas 1, verificar metadata DB |
| FR-006 | AS-2 | SC-001 | F0 tareas 2-4 |
| FR-007 | AS-3, AS-4 | SC-002 | F0 tarea 6: auditoria licencias |
| FR-008 | AS-2 | SC-001 | F0 tareas 3-5 |
| FR-009 | EC-01 | SC-001 | Plan de rollback por fase |
| FR-010 | AS-3 | SC-002 | F0 tarea 6 + spec 009 FR-002 |
| FR-011 | AS-3 | SC-002 | F0 tarea 6 |
| FR-012 | AS-4 | SC-002 | F0 tarea 6 |
| FR-013 | AS-4 | SC-002 | F0 tarea 6 |
| FR-014 | EC-02 | SC-002 | Implicito en auditoria |
| FR-015 | AS-6 | SC-003 | Matriz archivo-a-archivo (secciones A/B/C) |
| FR-016 | AS-6 | SC-003 | Seccion A: Preservar intacto |
| FR-017 | AS-6 | SC-003 | Seccion B: Extender (OCP) |
| FR-018 | AS-6 | SC-003 | Seccion C: Crear nuevo en enterprise/ |
| FR-019 | — | SC-005 | Plan de rollback por fase (tabla) |
| FR-020 | — | SC-005 | Principio rector: cero breaking changes |
| FR-021 | — | SC-005, SC-007 | "Rollback F0: trivial" |
| FR-022 | AS-7 | SC-006 | Criterios verificables F0 |
| FR-023 | AS-7 | SC-006 | Criterios verificables F0 (5 items) |
| FR-024 | EC-01, EC-04 | SC-006 | Implicito en go/no-go |

**Cobertura**: 24/24 FR mapeados. Todos los FR tienen al menos un SC asociado.

---

## Dependencies

### Depende de

- **Specs 002-008** (2.0 completo): F0 opera sobre el estado actual del 2.0 como baseline.
- **Spec 009** (MVP Foundation): F0 es la primera fase del scope de 009. Este spec (019) extiende el detalle operativo sin contradecir 009.

### Specs que dependen de este

- **Spec 009 fase F1**: no puede comenzar hasta que los criterios go/no-go de F0 se cumplan.
- **Specs 010-013** (F2-F4a): dependen transitivamente de que F0 haya validado los supuestos que les afectan.

---

## Referencia: Supuestos A1-A14

Para trazabilidad, se listan los supuestos tal como aparecen en el plan maestro:

| ID | Supuesto | Fase de verificacion |
|----|----------|---------------------|
| A1 | MiniMax M-2.5 disponible via misma API que M-2.7 | F0 (verificar antes de F3) |
| A2 | CrewAI 0.x soporta clientes OpenAI-compatible custom | F0 (verificar antes de F3) |
| A3 | TurboVec `pip install turbovec` funciona en Windows 11 | F0 (verificar inicio F2) |
| A4 | MCPs a internalizar tienen licencias compatibles (MIT/Apache-2.0) | F0 |
| A5 | Tools de Hermes son MIT-compatibles y portables a Windows 11 | F0 |
| A6 | `BAAI/bge-m3` corre en CPU con latencia < 200ms por batch | F0 |
| A7 | Presidio soporta espanol + ingles con `es_core_news_md` | F0 |
| A8 | OAuth providers permiten scopes restrictivos sin delete | F0 (verificar antes de F2) |
| A9 | Constitucion exige cambios quirurgicos; cero renombres de paquete | Permanente |
| A10 | Capacidad de ejecucion: MVP 12-16 sem con 1-2 ingenieros (reformulado por C1) | Cierre de F0 |
| A11 | El sistema de migraciones SQL crudo (MigrationRunner) soporta DDL con columnas vector(N) y DEFAULT uuidv7() | F0 |
| A12 | TurboVec funciona en Windows 11 (refuerzo de A3) | F0/F2 |
| A13 | pgvector 0.8+ instalado en PG 18 | F0 |
| A14 | `uuidv7()` disponible nativamente en PG 18 | F0 |
