# PostgreSQL & entorno readiness — spec 009 MVP Foundation

**Feature**: 009-mvp-foundation
**Creado**: 2026-05-28

Documento de validación de entorno de la Fase 1 (Setup) del spec 009.

---

## Decisión de arquitectura de migraciones (importante)

**tasks.md / plan.md asumían Alembic** (`alembic/versions/009_*.py`, ORM `Base.metadata`,
`alembic upgrade head`). Al auditar el repo se confirmó que **el 2.0 NO usa Alembic ni
SQLAlchemy ORM**:

- Las migraciones son archivos SQL crudos numerados en
  `src/vigilancia_multiagente/infra/db/migrations/NNN_*.sql`
  (`001_init.sql` … `005_evaluation_tables.sql`).
- Las aplica `src/vigilancia_multiagente/infra/db/migration_runner.py` (`MigrationRunner`),
  que registra cada archivo en la tabla `schema_migrations`.
- Los repositorios usan SQL crudo vía `sqlalchemy.text()`, no modelos ORM. No existe
  `Base` ni `metadata.py`.

**Decisión (operador, 2026-05-28)**: seguir el patrón SQL crudo del 2.0. Las 5 tablas
enterprise se crearán como `infra/db/migrations/006_mvp_foundation.sql` (en Fase 2 / T013),
aplicadas por el `MigrationRunner` existente. **No se introduce Alembic.**

Justificación constitucional:
- **#2 Simplicidad Obligatoria**: no añadir un segundo sistema de migraciones en paralelo.
- **#5 Cambios Quirúrgicos y Trazables**: reusar el mecanismo existente en vez de duplicarlo.

Acción tomada en T009: se eliminó el scaffold vacío `alembic/` (solo contenía `env.py`,
`script.py.mako` y `versions/.gitkeep` en 0 bytes, ninguno trackeado por git).

> Reinterpretación de tasks: T009 ("Setup Alembic") → "verificar sistema de migraciones SQL
> del 2.0 operativo". T013 ("alembic/versions/009_*.py") → "infra/db/migrations/006_mvp_foundation.sql".
> T014 (test upgrade/downgrade) se adaptará al `MigrationRunner` (que es upgrade-only;
> el rollback se cubrirá con SQL `DROP` idempotente en el test).

---

## Validaciones de entorno

### PostgreSQL (T001)

- [ ] **PENDIENTE — requiere entorno vivo.** Validar `VT_DATABASE_URL` con PostgreSQL real
  (versión, conectividad). El `.env.example` usa placeholder `CAMBIA_ESTA_CLAVE`; no hay
  credenciales reales disponibles en esta sesión.
- Comando sugerido cuando haya DB:
  `python -c "import asyncio, asyncpg; ..."` contra `VT_DATABASE_URL`.

### Xiaomimimo connectivity (T002)

- [ ] **PENDIENTE — requiere entorno vivo.** Validar `https://platform.xiaomimimo.com/v1/models`
  con `VT_XIAOMIMIMO_API_KEY`. El operador confirmó claves de PostgreSQL y Gemini, pero NO
  mencionó Xiaomimimo; se valida en su propio componente (T021/T022 con mocks; smoke real al
  arrancar la app).

### Embedding provider del 2.0 (T003)

- [x] **Validado 2026-05-28 (entorno vivo) — conectividad OK, con hallazgo de configuración.**
  `GeminiEmbeddingGateway.embed()` con `VT_EMBEDDING_API_KEY` configurada SÍ llega a Gemini y
  devuelve un vector. **Pero** el modelo activo devuelve **3072 dimensiones**, mientras el 2.0
  espera `VT_EMBEDDING_DIMENSIONS=768`; `_normalize_and_validate()` lanza
  `ValueError: Unexpected embedding dimension 3072; expected 768`.
- **Causa**: desajuste entre el modelo de embeddings real (3072 dims, p. ej. `gemini-embedding-001`)
  y el valor por defecto `768`. **No es un bug del código** ni de los cambios del spec 009.
- **Acción recomendada (operador, fuera del alcance del spec 009, no se toca el 2.0)**: alinear
  `VT_EMBEDDING_DIMENSIONS=3072` con el modelo activo, **o** fijar el modelo a uno de 768 dims.
  El discovery semántico de `ToolRegistry` (T025) reutilizará este gateway, así que la dimensión
  debe quedar coherente antes de F1.2.

### Layer imports baseline (T004)

- [x] **Ejecutado 2026-05-28.** `python scripts/check-layer-imports.py` →
  `[OK] No se encontraron violaciones de capas.` Capas analizadas: domain, application,
  infra, api (0 archivos con imports prohibidos). Baseline limpio del 2.0.
- Nota: el script aún no incluye `enterprise/` en su mapa de capas; extender su cobertura
  para SC-011 se hará al incorporar código bajo `enterprise/` (Fase 3+), sin modificar el
  script (plan.md, fila "Layer enforcement").

### Sistema de migraciones del 2.0 (T009, reinterpretado)

- [x] **Verificado 2026-05-28.** 5 migraciones SQL intactas
  (`001_init.sql` … `005_evaluation_tables.sql`), `MigrationRunner` presente y operativo.
  Scaffold `alembic/` vacío eliminado. La migración 006 (5 tablas enterprise) se creará en
  Fase 2.

### Dependencias PyPI nuevas (T008)

- [x] Instaladas y verificadas como importables: `openai` 2.9.1, `cryptography`,
  `apscheduler` 3.11.5, `prometheus-client`, `opentelemetry-api/sdk`, `respx` (dev).
- Auditoría de licencias en `docs/audit-licenses.md`.

---

## Fase 2 (Foundational) — verificación (T011–T020)

**Estado: COMPLETA (2026-05-28).**

- **T011** `settings.py` extendido (campos planos `VT_*` para LLM/Xiaomimimo/HealthMonitor/
  tenant/observabilidad). Settings del 2.0 intactos. Verificado: carga OK.
- **T012** `config/settings.yaml` con defaults LLM declarativos.
- **T013** `infra/db/migrations/006_mvp_foundation.sql` (SQL crudo, no Alembic): 5 tablas
  (`tool_health`, `oauth_credentials`, `subagents`, `pending_approvals`, `company_profile`)
  con `tenant_id UUID NOT NULL` + índices. Verificado contra DB real (aislado de pgvector).
- **T014** `tests/enterprise/migrations/test_009_mvp_foundation.py` — 5 tests (tablas, columnas,
  índices, idempotencia 5×, aislamiento de tabla 2.0 tras upgrade+downgrade).
- **T015/T016** `enterprise/tooling/tool_wrapper.py` (Protocol + `HealthcheckResult`) y
  `tool_card.py` (`ToolCard`/`ToolSummary`/`ToolDocs`).
- **T017/T018/T019** repositorios `tool_health`, `oauth_credentials`, `company_profile`
  (SQL crudo, patrón del 2.0).
- **T020** `tests/enterprise/persistence/test_repositories.py` — 3 tests CRUD contra DB real.

**Resultado de tests Fase 2**: `pytest tests/enterprise/` → **8 passed** (contra PostgreSQL 18.3
real). Skip automático si no hay DB.

**Calidad (solo archivos nuevos del spec 009)**:
- `ruff check` → *All checks passed!*
- `basedpyright` → 0 errores en archivos enterprise/repos/settings nuevos.
- `check-layer-imports.py` → *OK: no layer import violations*.

### Notas de entorno (acción del operador, fuera del alcance del spec 009)

1. **pgvector no instalado** en la PostgreSQL local → bloquea las migraciones 001–005 del 2.0
   (`MigrationRunner` completo). Los tests del spec 009 lo evitan aplicando la 006 aislada.
   Instalar `pgvector` para que el arranque normal de la app (`database.initialize()`) funcione.
2. **Embeddings 3072 vs 768**: el modelo Gemini activo devuelve 3072 dims; el 2.0 espera 768.
   Alinear `VT_EMBEDDING_DIMENSIONS` o el modelo antes de usar el discovery semántico (F1.2).
3. **basedpyright preexistente**: 13 errores en `infra/search/bm25_plus_embedding.py` (código del
   2.0, NO tocado por el spec 009). Aparecen ahora porque `rank_bm25` se instaló en esta sesión.
   No es regresión del spec 009; se deja señalado para el mantenimiento del 2.0.

---

## Final verification (Fase 4 — Polish, 2026-05-29)

### Suite de tests (T054)

- **Enterprise (spec 009)**: `pytest tests/enterprise/` → **41 passed** (contra PostgreSQL
  18.3 real; skip automático sin DB). Cero fallos.
- **Frontend enterprise (T058)**: `vitest run src/enterprise` → **30 passed** (5 archivos
  de test). Cobertura medida solo sobre `src/enterprise/` ≥ 70 % en las 4 métricas
  (enterpriseClient 96 %, onboardingStore 100 %, stores/páginas/flow 81–100 %).
- **Suite global del 2.0**: `pytest tests/` → **273 passed, 21 failed, 4 errors**.

  **Importante — los 21 fallos + 4 errores son PREEXISTENTES del 2.0, no regresiones del
  spec 009.** Verificado con `git stash` de los 4 archivos rastreados modificados
  (`pyproject.toml`, `api/app.py`, `api/router.py`, `config/settings.py`): en el estado
  baseline (origin/main, sin spec 009) los mismos tests fallan idénticamente. Los archivos
  de test que fallan no importan código enterprise. Categorías:

  | Test(s) | Causa (preexistente, ajena al spec 009) |
  |---------|------------------------------------------|
  | `ws_b/test_hybrid_search.py` (3) | `bm25_plus_embedding.py` bug numpy `truth value of an array is ambiguous` (mismo archivo de los 13 errores basedpyright preexistentes). |
  | `ws_c/test_assumption_detector.py` (4), `ws_c/test_counterfactual_synthesizer.py` (4), `ws_e/test_falsification_prober.py` (2) | `DummyPromptLoader` de los tests asume el path antiguo sin `.example_user.txt`; drift de la API de prompts del 2.0. |
  | `test_constitution_compliance.py` (4) | marcadores `DEPRECATED` y accesos `.get("results")` en código del 2.0. |
  | `test_contract_naming.py` (2 + error), `test_e2e_full_flow.py` (error), `test_sse_events.py` (2 errores) | tests de integración que levantan un mock server en el puerto 8000; falla por `[Errno 10048]` (puerto en uso — ambiental) y contrato camelCase del 2.0. |
  | `test_e2e_flow.py` | `KeyError: 'by_branch'`. |
  | `test_minimax_client.py::test_complete_sends_max_tokens` | `KeyError: 'max_tokens'` en el cliente MiniMax del 2.0. |

  **Conclusión**: spec 009 introduce **cero regresiones**. FR-032 ("100 % del 2.0") está
  limitado por deuda preexistente del 2.0 que precede a este spec; se deja señalada para el
  mantenimiento del 2.0 (fuera del alcance de 009, que no toca esos archivos).

### Linters / typecheck / capas (T055–T057, T062)

- **T055** `python scripts/check-layer-imports.py` → `OK: no layer import violations`.
- **T056** `basedpyright` sobre archivos enterprise nuevos → **0 errores, 0 warnings, 0 notes**.
- **T057** `ruff check` sobre archivos del spec 009 → **All checks passed!**;
  `ruff format` aplicado (8 archivos reformateados).
- **T062** SC-009 (`grep -E "^\s*(pass|\.\.\.|TODO)\s*$" enterprise/`) → los únicos 2 matches
  son los cuerpos `...` de los métodos del `Protocol ToolWrapper` (`tool_wrapper.py`), idioma
  legítimo de Python, **no stubs**. Cero stubs reales.

### Validaciones manuales de Success Criteria (T059–T061)

Requieren entorno vivo (API key Xiaomimimo + navegador). Procedimientos documentados en
`docs/sc-001-validation.md`. Pendientes de ejecución por el operador.
