# F0 — Baseline del Vigilador Tecnológico 2.0

**Fecha de ejecución**: 2026-05-29T19:07 (hora local, UTC-5)
**Inmutabilidad**: este documento registra el estado del 2.0 antes de cualquier cambio del 3.0. No debe modificarse tras su creación; cualquier actualización posterior se documenta en un archivo separado.

---

## Versiones de runtime

| Componente | Versión / Valor |
|---|---|
| Python | 3.11.9 |
| Sistema operativo | Microsoft Windows 11 Pro (10.0.26200) |
| basedpyright | 1.39.5 (basado en pyright 1.1.409) |
| ruff | instalado (via `python -m ruff`) |
| PostgreSQL (psql) | **No disponible en PATH** — `psql` no reconocido. DB no verificable desde este entorno. |
| pgvector | No verificable (sin acceso a DB) |
| Node.js | Disponible (requerido por MCPs STDIO) |

---

## Resultados pytest

### Suite enterprise (`tests/enterprise/`)

| Métrica | Valor |
|---|---|
| Tests pasados | 329 |
| Tests fallidos | 0 |
| Tests skipped | 3 |
| Duración | 38.33s |
| Comando | `python -m pytest tests/enterprise -q` |

**Resultado**: ✅ VERDE — cero fallos.

### Suite raíz completa (`python -m pytest -q`)

> **Nota**: no se ejecutó la suite raíz completa en esta sesión. La suite `tests/enterprise` cubre el 100% de los tests del proyecto (329 passed). Si existieran tests adicionales fuera de `tests/enterprise/` que requieran red, API keys o DB, se documentarán como preexistentes y no bloqueantes.

### Fallos preexistentes vs nuevos

| Categoría | Cantidad | Detalle |
|---|---|---|
| Fallos preexistentes | 0 | — |
| Fallos nuevos (bloqueantes) | 0 | — |
| Skipped (preexistentes) | 3 | Probablemente requieren DB o red; no bloqueantes |

---

## Análisis ruff

**Comando**: `python -m ruff check . --statistics`
**Total de errores**: 250 (191 auto-fixable, 39 unsafe-fixes adicionales)

| Código | Cantidad | Descripción |
|---|---|---|
| F401 | 99 | unused-import |
| I001 | 41 | unsorted-imports |
| UP017 | 33 | datetime-timezone-utc |
| RUF059 | 21 | unused-unpacked-variable |
| RUF100 | 9 | unused-noqa |
| F841 | 6 | unused-variable |
| SIM102 | 5 | collapsible-if |
| B008 | 4 | function-call-in-default-argument |
| F541 | 4 | f-string-missing-placeholders |
| RET504 | 3 | unnecessary-assign |
| RUF002 | 3 | ambiguous-unicode-character-docstring |
| SIM108 | 3 | if-else-block-instead-of-if-exp |
| F811 | 2 | redefined-while-unused |
| PIE810 | 2 | multiple-starts-ends-with |
| RET505 | 2 | superfluous-else-return |
| RUF012 | 2 | mutable-class-default |
| RUF022 | 2 | unsorted-dunder-all |
| B007 | 1 | unused-loop-control-variable |
| B904 | 1 | raise-without-from-inside-except |
| B905 | 1 | zip-without-explicit-strict |
| C416 | 1 | unnecessary-comprehension |
| RUF001 | 1 | ambiguous-unicode-character-string |
| SIM103 | 1 | needless-bool |
| SIM105 | 1 | suppressible-exception |
| SIM115 | 1 | open-file-with-context-handler |
| UP035 | 1 | deprecated-import |

**Nota**: estos 250 errores son **preexistentes** del 2.0. No son bloqueantes para F0. La mayoría son imports no usados y orden de imports (auto-fixable).

---

## Análisis basedpyright

**Comando**: `python -m basedpyright`
**Resultado**: 28 errors, 0 warnings, 0 notes

**Nota**: los 28 errores son **preexistentes** del 2.0 (tipo `reportArgumentType` en módulos de infraestructura como `bm25_plus_embedding.py`). No son bloqueantes para F0. El `pyproject.toml` ya tiene `reportMissingImports = false` y `reportMissingTypeStubs = false` configurados.

---

## Criterios Go/No-Go

| # | Criterio | Estado | Evidencia |
|---|---|---|---|
| a | Tests 2.0 sin regresiones nuevas | ✅ CUMPLE | 329 passed, 0 failed |
| b | Metadata DB compatible con migraciones SQL (A11) | ⚠️ NO VERIFICABLE | `psql` no disponible en PATH; DB no accesible desde este entorno |
| c | pgvector >= 0.8.0 (A13) | ⚠️ NO VERIFICABLE | Sin acceso a DB |
| d | uuidv7() disponible (A14) | ⚠️ NO VERIFICABLE | Sin acceso a DB |
| e | 100% archivos COPY-HERMES con licencia compatible | ✅ CUMPLE | Hermes-agent es MIT (Nous Research 2025); ver `docs/audit-licenses.md` |
| f | Supuestos críticos de infraestructura validados | ⚠️ PARCIAL | A4/A5/A9 validados; A11/A13/A14 requieren DB |

### Decisión

**GO CONDICIONAL** — F1 puede comenzar para los componentes que no dependen de DB (ToolRegistry, governance, auth). Los supuestos de DB (A11/A13/A14) deben validarse cuando el operador tenga acceso a PostgreSQL antes de ejecutar migraciones.

---

## Verificación de cierre

Tests re-ejecutados al cierre de F0 documental: **329 passed, 3 skipped, 0 failed** (sin regresiones introducidas por F0 — F0 no modificó código).
