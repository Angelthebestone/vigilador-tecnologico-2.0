# Implementation Plan: Fase F0 — Auditoria Baseline y Estrategia de Migracion

**Feature ID**: 019-fase-F0-auditoria-baseline
**Created**: 2026-05-29
**Spec**: [spec.md](spec.md)

## Problem

El spec 009 (MVP Foundation) definio F0+F1 como bloque conjunto y cubrio los requisitos funcionales basicos de F0 (validar DB, generar audit-licenses.md, crear carpetas vacias, verificar MigrationRunner). Sin embargo, 009 trato F0 como setup subordinado a F1 sin especificar:

- El procedimiento detallado de validacion de cada supuesto A1-A14.
- La clasificacion formal de la matriz preservar/extender/nuevo como artefacto verificable.
- El plan de rollback por fase como documento operativo.
- Los criterios de go/no-go que determinan si F1 puede comenzar.

Este plan materializa el detalle operativo de F0 que 019 extiende sobre 009: auditoria de licencias completa, validacion de supuestos con evidencia, documentacion de la matriz de migracion y plan de rollback. F0 no produce codigo de producto; solo documentos, estructura vacia y configuracion de herramientas.

## Approach

Ejecutar F0 como fase puramente documental y de validacion. Producir 4 artefactos verificables: (1) baseline del 2.0 con resultados de tests/linting/versiones, (2) registro de validacion de supuestos A1-A14 con estado VALIDADO/DESMENTIDO, (3) auditoria de licencias cubriendo archivos COPY-HERMES + paquetes PyPI + MCPs externos, (4) matriz preservar/extender/nuevo formalizada, y (5) plan de rollback por fase F0-F5. Cada artefacto tiene criterios de completitud medibles. Al cierre, se evaluan criterios go/no-go para autorizar F1.

---

## Technical Context

| Area | Decision |
|------|----------|
| Entorno target | Windows 11, Python 3.11+, PostgreSQL 18, pgvector 0.8+ |
| Metadata DB | PostgreSQL existente del 2.0 con extensiones vector y uuid |
| Herramientas de validacion | pytest, ruff, basedpyright, psql, pip (en venv aislado) |
| Archivos COPY-HERMES | ~30 archivos en `documentation/hermes agent/hermes-agent/tools/` |
| Paquetes PyPI nuevos F1 | ~10 paquetes (openai, cryptography, apscheduler, prometheus-client, opentelemetry-api, opentelemetry-sdk, etc.) |
| MCPs externos Tier 2 | 15 MCPs preservados del 2.0 en `infra/mcp/mcp-providers.json` |
| Trabajo sobre branch | `main` directamente (regla CLAUDE.md) |

## External Constraints

| Constraint | Impact |
|------------|--------|
| Constitucion #5 — Cambios quirurgicos | F0 no toca codigo del 2.0. Cero modificaciones a archivos existentes del repo. |
| Constitucion #1 — Pensar antes de codificar | F0 es la materializacion de este principio: validar supuestos antes de implementar. |
| Constitucion #6 — Entrega verificable | Cada supuesto tiene criterio de exito verificable con evidencia. |
| Principio rector doc 07 | Cero breaking changes al 2.0. API `/api/v2/research/*` y 6 agentes intactos. |
| Spec 009 ya cubrio FR-003/FR-004 | Creacion de carpetas vacias y verificacion de MigrationRunner ya estan en scope de 009. Este plan NO los repite. |
| Duracion estimada | 2-3 semanas segun cronograma MVP (00b). |

---

## Files to Create / Modify

### New Files

| File | Purpose |
|------|---------|
| `docs/f0-baseline.md` | Registro inmutable del estado del 2.0: versiones runtime, resultados pytest, conteo ruff/basedpyright, fecha. |
| `docs/audit-licenses.md` | Tabla de archivos COPY-HERMES + paquetes PyPI + MCPs externos con licencia, compatibilidad y accion. |
| `docs/migration-matrix.md` | Clasificacion formal de componentes del 2.0 en PRESERVAR/EXTENDER/CREAR NUEVO con evidencia. |
| `docs/rollback-plan.md` | Procedimientos de reversion por fase F0-F5 con riesgo, procedimiento y estado post-rollback. |
| `docs/f0-supuestos-validacion.md` | Registro de validacion de supuestos A1-A14 con estado, evidencia y accion correctiva. |

### Modified Files

| File | Changes |
|------|---------|
| Ninguno | F0 no modifica archivos existentes del repositorio. |

---

## Relacion con spec 009 — Matriz preservar/extender/nuevo del plan

| Aspecto | Cubierto por plan 009 Phase 1 | Extendido por este plan (019) |
|---|---|---|
| Validar entorno (DB, keys, imports) | Si — pasos 1-2 de Phase 1 | Procedimiento formal por supuesto A1-A14 con evidencia |
| Crear `docs/audit-licenses.md` esqueleto | Si — paso 2 de Phase 1 | Contenido completo: ~30 COPY-HERMES + ~10 PyPI + 15 MCPs |
| Crear carpetas `enterprise/` vacias | Si — paso 3 de Phase 1 | No (ya completo en 009) |
| Crear carpetas `config/` placeholders | Si — paso 4 de Phase 1 | No (ya completo en 009) |
| Verificar MigrationRunner | Si — paso 5 de Phase 1 | No (ya completo en 009) |
| Baseline formal del 2.0 | Implicito (tests deben pasar) | Documento `docs/f0-baseline.md` con registro completo |
| Matriz preservar/extender/nuevo | Referenciada en doc 07 | Formalizada como `docs/migration-matrix.md` verificable |
| Plan de rollback | Mencionado en doc 07 tabla | Formalizado como `docs/rollback-plan.md` con procedimientos |
| Criterios go/no-go | Implicitos en criterios F0 | Explicitos y medibles en baseline |

---

## Constitution Check (Pre-Design)

- **Gate result**: PASS
- **Constitucion evaluada**: v1.2.0 (`.specify/memory/constitution.md`).
- **Alignment**:
  - **Pensar Antes de Codificar**: F0 entera es la materializacion de este principio. Cada supuesto se valida con prueba concreta antes de que F1 escriba codigo. Los 14 supuestos se declaran explicitamente con criterio de exito.
  - **Simplicidad Obligatoria**: cero abstracciones, cero codigo de producto. Solo documentos con tablas verificables. Sin capas innecesarias.
  - **Modularidad Primero**: cada artefacto de F0 es un documento independiente con responsabilidad unica (baseline, licencias, matriz, rollback, supuestos).
  - **Cambios Quirurgicos y Trazables**: cero archivos del 2.0 modificados. F0 solo produce documentos nuevos en `docs/`. Radio de cambio: cero lineas de codigo existente tocadas.
  - **Entrega Verificable**: cada fase del plan tiene output medible. Cada supuesto tiene estado binario (VALIDADO/DESMENTIDO). Criterios go/no-go son checklist explicita.
- **Diseno de Software**: SoC (cada documento cubre un concern separado), KISS (documentos planos sin estructura innecesaria), YAGNI (solo se documenta lo que F1+ necesita para arrancar).

---

## Phases

### Phase 1 — Registro de baseline del 2.0 (1-2 dias)

Objetivo: capturar el estado actual del 2.0 como punto de referencia inmutable.

1. Ejecutar `pytest` sobre el codigo del 2.0 y registrar: tests pasando, tests fallando, tests skipped, duracion total.
2. Ejecutar `ruff check .` y registrar conteo de errores y warnings por categoria.
3. Ejecutar `basedpyright` y registrar conteo de errores/warnings.
4. Registrar versiones de runtime: `python --version`, `psql --version`, `SELECT version()` en metadata DB, `SELECT extversion FROM pg_extension WHERE extname='vector'`.
5. Registrar sistema operativo, fecha de ejecucion, espacio en disco disponible.
6. Consolidar todo en `docs/f0-baseline.md` con formato tabla.

**Output**: `docs/f0-baseline.md` completo con estado inmutable del 2.0. Si tests fallan, se registra el estado como-esta distinguiendo fallos preexistentes (no bloqueantes) de fallos nuevos (bloqueantes).

**Traza**: FR-001, FR-002, FR-003 del spec 019. SC-004.

### Phase 2 — Validacion de supuestos A1-A14 (5-7 dias)

Objetivo: evaluar cada supuesto del plan con prueba concreta y registrar resultado.

1. **A1 (MiniMax M-2.5 via misma API)**: verificar documentacion de API MiniMax; si hay endpoint de info, ejecutar curl. Registrar respuesta o error.
2. **A2 (CrewAI 0.x soporta clientes OpenAI-compatible custom)**: instalar crewai en venv aislado, verificar que acepta `base_url` custom en configuracion. Registrar version + resultado.
3. **A3/A12 (TurboVec en Windows 11)**: ejecutar `pip install turbovec` en venv aislado en Windows 11. Registrar exito/fallo con version y traceback si falla.
4. **A4 (MCPs a internalizar tienen licencias compatibles)**: inspeccionar headers de los MCPs candidatos a internalizacion. Registrar licencia por MCP.
5. **A5 (Tools de Hermes MIT-compatibles y portables)**: inspeccionar headers de los ~30 archivos en `documentation/hermes agent/hermes-agent/tools/`. Registrar licencia detectada por archivo.
6. **A6 (BAAI/bge-m3 en CPU < 200ms)**: instalar sentence-transformers + modelo en venv, ejecutar benchmark con batch de 10 textos. Registrar latencia p50/p95.
7. **A7 (Presidio soporta espanol + ingles)**: instalar presidio-analyzer + es_core_news_md, ejecutar deteccion sobre texto de prueba en espanol. Registrar resultado.
8. **A8 (OAuth providers permiten scopes sin delete)**: revisar documentacion de Google Workspace OAuth y Microsoft Graph. Registrar scopes disponibles sin permisos destructivos.
9. **A9 (Cambios quirurgicos, cero renombres)**: verificacion documental — confirmar que la constitucion v1.2.0 lo exige. Registrar referencia.
10. **A10 (Capacidad de ejecucion 12-16 sem)**: evaluar progreso actual vs cronograma. Registrar estimacion actualizada.
11. **A11 (MigrationRunner soporta DDL con columnas vector + UUIDv7)**: ejecutar `CREATE TABLE test_a11 (id uuid DEFAULT uuidv7(), vec vector(1536))` en metadata DB via psql. Registrar exito/fallo.
12. **A13 (pgvector 0.8+ instalado)**: ejecutar `SELECT extversion FROM pg_extension WHERE extname='vector'`. Registrar version exacta.
13. **A14 (uuidv7() disponible nativamente en PG 18)**: ejecutar `SELECT uuidv7()`. Registrar resultado o error.
14. Para cada supuesto DESMENTIDO: documentar impacto en fases posteriores, plan B disponible (si existe), y decision requerida.
15. Consolidar en `docs/f0-supuestos-validacion.md` con tabla: ID, supuesto, metodo de validacion, resultado (VALIDADO/DESMENTIDO), evidencia, accion correctiva.

**Output**: `docs/f0-supuestos-validacion.md` con 14 filas completas. Cero supuestos sin evaluar.

**Traza**: FR-004, FR-005, FR-006, FR-007, FR-008, FR-009 del spec 019. SC-001.

### Phase 3 — Auditoria de licencias (3-4 dias)

Objetivo: documentar licencia y compatibilidad de todo archivo/paquete que entrara al 3.0.

1. **Archivos COPY-HERMES (~30)**: para cada archivo en `documentation/hermes agent/hermes-agent/tools/`, inspeccionar header de licencia (primeras 20 lineas). Registrar: archivo origen (path relativo), archivo destino previsto en `enterprise/`, licencia detectada, compatible MIT/Apache-2.0 (si/no), accion (copiar/excluir/alternativa), atribucion requerida.
2. **Paquetes PyPI nuevos (~10)**: para cada paquete previsto en F1 (openai, cryptography, apscheduler, prometheus-client, opentelemetry-api, opentelemetry-sdk, sentence-transformers, presidio-analyzer, python-docx, weasyprint), consultar licencia en PyPI metadata o GitHub. Registrar: nombre, version minima, licencia, compatible (si/no), accion.
3. **MCPs externos Tier 2 (15)**: para cada MCP preservado del 2.0 en `infra/mcp/mcp-providers.json`, verificar licencia del paquete/servidor MCP. Registrar: nombre, licencia, compatible (si/no).
4. Si un archivo o paquete resulta incompatible (GPL, AGPL, SSPL u otra copyleft): registrar alternativa propuesta e impacto en cronograma.
5. Consolidar todo en `docs/audit-licenses.md` con 3 secciones (COPY-HERMES, PyPI, MCPs) y tablas completas.

**Output**: `docs/audit-licenses.md` con cobertura 100% de los 3 grupos. Cero filas pendientes.

**Traza**: FR-010, FR-011, FR-012, FR-013, FR-014 del spec 019. SC-002.

### Phase 4 — Matriz preservar/extender/nuevo (2-3 dias)

Objetivo: formalizar la clasificacion de componentes del 2.0 como artefacto verificable.

1. **Seccion PRESERVAR**: listar cada componente de la seccion A del doc 07-migracion con: componente, ubicacion exacta en el repo, razon de preservacion, confirmacion de que existe en el baseline (verificar con `dir` o lectura del archivo).
2. **Seccion EXTENDER**: listar cada componente de la seccion B del doc 07-migracion con: componente, ubicacion, tipo de extension prevista (subclase, adapter, parametro opcional), fase en que se materializa (F1/F2/F3/F4/F5).
3. **Seccion CREAR NUEVO**: listar cada componente de la seccion C del doc 07-migracion con: componente, ubicacion destino en `enterprise/`, fase en que se crea, dependencias de componentes preservados/extendidos.
4. Verificar que cada componente listado como PRESERVAR existe fisicamente en el repo actual.
5. Verificar que cada componente listado como EXTENDER tiene su punto de extension identificado (port, clase base, o interfaz).
6. Consolidar en `docs/migration-matrix.md`.

**Output**: `docs/migration-matrix.md` con 3 secciones completas. Cobertura de todos los componentes de secciones A/B/C del doc 07.

**Traza**: FR-015, FR-016, FR-017, FR-018 del spec 019. SC-003.

### Phase 5 — Plan de rollback por fase (1-2 dias)

Objetivo: documentar procedimiento de reversion para cada fase F0-F5.

1. Para cada fase (F0, F1, F2, F3a, F3b, F4a, F4b, F4c, F5a, F5b, F5c, F5d): documentar riesgo principal, procedimiento de reversion paso a paso, y estado esperado post-rollback.
2. Garantizar que en cualquier fase, la reversion deja el 2.0 funcionando identico al baseline registrado en Phase 1.
3. Para F0 especificamente: rollback es trivial — descartar documentos generados y estructura de carpetas vacias. Sin impacto en codigo ni DB.
4. Para F1: DROP de tablas enterprise + eliminar `enterprise/`. Tests del 2.0 siguen pasando.
5. Para F2-F5: documentar procedimiento especifico segun artefactos de cada fase (config flags, migration downgrade, eliminacion de archivos).
6. Consolidar en `docs/rollback-plan.md`.

**Output**: `docs/rollback-plan.md` con tabla y procedimientos para las 6+ fases.

**Traza**: FR-019, FR-020, FR-021 del spec 019. SC-005.

### Phase 6 — Criterios go/no-go y cierre de F0 (1 dia)

Objetivo: evaluar si F1 puede comenzar.

1. Definir criterios go/no-go en seccion final de `docs/f0-baseline.md` (o documento separado):
   - (a) Tests del 2.0 sin regresiones nuevas respecto al baseline.
   - (b) Metadata DB compatible con migraciones SQL del 2.0 (A11 VALIDADO).
   - (c) pgvector >= 0.8.0 instalado (A13 VALIDADO).
   - (d) `uuidv7()` disponible nativamente (A14 VALIDADO).
   - (e) 100% de archivos COPY-HERMES con licencia compatible o alternativa documentada.
   - (f) Supuestos criticos de infraestructura (A11, A13, A14) todos VALIDADOS.
2. Evaluar cada criterio contra los resultados de Phases 1-5.
3. Si todos los criterios criticos pasan: registrar "GO — F1 autorizado" con fecha.
4. Si algun criterio critico falla: registrar "NO-GO" con: criterio fallido, accion correctiva requerida, responsable, y fecha limite para re-evaluacion.
5. Verificar que tests del 2.0 siguen pasando al 100% al cierre de F0 (cero regresiones introducidas por la fase).

**Output**: Seccion go/no-go en `docs/f0-baseline.md` con decision explicita. F0 cerrado.

**Traza**: FR-022, FR-023, FR-024 del spec 019. SC-004, SC-006, SC-007.

---

## Rollout Strategy

**Estrategia**: F0 es puramente documental. No hay codigo de producto que desplegar.

- **Backward compatibility**: garantizada por definicion — F0 no toca ningun archivo del 2.0.
- **Feature flags**: no aplica. No hay features nuevas.
- **Coexistencia con 2.0**: total. Los documentos generados en `docs/` no afectan el runtime.
- **Rollback de F0**: trivial. Si F0 se descarta, se eliminan los 5 archivos en `docs/` generados por este plan. El repositorio queda identico al estado pre-F0.
- **Orden de ejecucion**: las Phases 1-5 son mayormente secuenciales (Phase 2 depende de Phase 1 para el baseline; Phase 6 depende de todas las anteriores). Phases 3 y 4 pueden ejecutarse en paralelo con Phase 2.

---

## Success Criteria

- **SC-001**: El 100% de los supuestos A1-A14 tienen estado VALIDADO o DESMENTIDO con evidencia documentada en `docs/f0-supuestos-validacion.md`.
- **SC-002**: `docs/audit-licenses.md` cubre el 100% de archivos COPY-HERMES candidatos (~30), el 100% de paquetes PyPI nuevos (~10) y el 100% de MCPs externos Tier 2 (15), sin filas pendientes.
- **SC-003**: `docs/migration-matrix.md` cubre todos los componentes listados en secciones A/B/C del doc 07-migracion, sin omisiones.
- **SC-004**: Los tests del 2.0 registrados en el baseline siguen pasando al 100% al cierre de F0 (cero regresiones introducidas).
- **SC-005**: `docs/rollback-plan.md` cubre las fases F0-F5 (incluyendo sub-fases MVP y roadmap) con procedimiento concreto por fase.
- **SC-006**: Los criterios go/no-go estan documentados y evaluados; F1 tiene autorizacion explicita o bloqueo documentado con accion correctiva.
- **SC-007**: F0 se completa sin producir codigo de producto — solo documentos nuevos en `docs/`.

## Constitution Check (Post-Design)

- **Status**: PASS
- **Constitucion evaluada**: v1.2.0 (`.specify/memory/constitution.md`).
- **Justification**:
  - **Pensar Antes de Codificar**: el plan entero es la ejecucion de este principio. 14 supuestos validados con prueba antes de que F1 escriba una linea de codigo.
  - **Simplicidad Obligatoria**: 5 documentos planos con tablas. Cero abstracciones, cero codigo, cero configuracion compleja. La solucion mas simple posible para validar supuestos.
  - **Modularidad Primero**: cada documento tiene responsabilidad unica (baseline, supuestos, licencias, matriz, rollback). Pueden leerse y verificarse de forma independiente.
  - **Cambios Quirurgicos y Trazables**: cero archivos del 2.0 modificados. Radio de cambio: 5 archivos nuevos en `docs/`, todos documentales. Cada documento traza a FRs y SCs del spec.
  - **Entrega Verificable**: 7 success criteria medibles. Cada supuesto tiene estado binario. Cada tabla tiene criterio de completitud (100% cobertura). El cierre de F0 requiere evaluacion explicita de go/no-go.
  - **Diseno de Software**: SoC (cada documento un concern), KISS (formato tabla plano sin estructura innecesaria), YAGNI (solo se documenta lo estrictamente necesario para autorizar F1), DRY (la matriz referencia doc 07 sin duplicar su contenido completo).
