"""T014 — Test de la migración 006_mvp_foundation.sql (5 tablas enterprise).

El 2.0 usa SQL crudo + `MigrationRunner` (no Alembic). `MigrationRunner` es
upgrade-only, así que aquí:

  - aplicamos la 006 de forma AISLADA (sin depender de 001-005, que requieren
    pgvector y bloquearían el test en entornos sin la extensión),
  - verificamos idempotencia re-aplicándola 5 veces seguidas sin residuos ni error,
  - verificamos aislamiento: una tabla "del 2.0" simulada permanece intacta,
  - el "downgrade" se cubre con DROP idempotente (rollback manual del MVP).

Si no hay PostgreSQL disponible, el test se salta (skip) en vez de fallar.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

from tests.enterprise.db_url import resolve_database_url
from vigilancia_multiagente.infra.db.migration_runner import _split_sql_statements

ENTERPRISE_TABLES = (
    "tool_health",
    "oauth_credentials",
    "subagents",
    "pending_approvals",
    "company_profile",
)

MIGRATION_PATH = Path("src/vigilancia_multiagente/infra/db/migrations/006_mvp_foundation.sql")


def _statements() -> list[str]:
    return _split_sql_statements(MIGRATION_PATH.read_text(encoding="utf-8"))


async def _drop_enterprise(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        for table in reversed(ENTERPRISE_TABLES):
            await conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))


async def _apply_006(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        for statement in _statements():
            await conn.execute(text(statement))


@pytest_asyncio.fixture
async def engine():
    # Engine dedicado con NullPool: cada test crea el suyo dentro de su propio
    # event loop. La URL se resuelve del .env real (no de get_settings(), que el
    # conftest del 2.0 contamina con credenciales placeholder).
    db_url = resolve_database_url()
    if not db_url:
        pytest.skip("VT_DATABASE_URL no resoluble")
    eng = create_async_engine(db_url, poolclass=NullPool)
    try:
        try:
            async with eng.begin() as conn:
                await conn.execute(text("SELECT 1"))
        except Exception as exc:
            pytest.skip(f"PostgreSQL no disponible: {exc}")
        await _drop_enterprise(eng)
        yield eng
    finally:
        await _drop_enterprise(eng)
        await eng.dispose()


@pytest.mark.asyncio
async def test_006_crea_las_cinco_tablas(engine: AsyncEngine) -> None:
    await _apply_006(engine)
    async with engine.connect() as conn:
        for table in ENTERPRISE_TABLES:
            r = await conn.execute(text(f"SELECT to_regclass('public.{table}') IS NOT NULL"))
            assert r.scalar_one() is True, f"falta tabla {table}"


@pytest.mark.asyncio
async def test_006_tool_health_columnas(engine: AsyncEngine) -> None:
    await _apply_006(engine)
    async with engine.connect() as conn:
        r = await conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'tool_health' ORDER BY ordinal_position"
            )
        )
        cols = [row[0] for row in r.fetchall()]
    assert cols == [
        "name",
        "tenant_id",
        "status",
        "last_check",
        "fail_count",
        "last_error",
        "domain",
        "requires_key",
    ]


@pytest.mark.asyncio
async def test_006_tenant_id_indices(engine: AsyncEngine) -> None:
    await _apply_006(engine)
    async with engine.connect() as conn:
        r = await conn.execute(
            text("SELECT tablename, indexname FROM pg_indexes WHERE tablename = ANY(:tables)"),
            {"tables": list(ENTERPRISE_TABLES)},
        )
        indexes = {(row[0], row[1]) for row in r.fetchall()}
    for table in ENTERPRISE_TABLES:
        assert any(t == table and "tenant_id" in i for (t, i) in indexes), (
            f"falta índice tenant_id en {table}"
        )


@pytest.mark.asyncio
async def test_006_idempotente_cinco_veces(engine: AsyncEngine) -> None:
    for _ in range(5):
        await _apply_006(engine)  # IF NOT EXISTS → no debe lanzar
    async with engine.connect() as conn:
        for table in ENTERPRISE_TABLES:
            r = await conn.execute(text(f"SELECT to_regclass('public.{table}') IS NOT NULL"))
            assert r.scalar_one() is True


@pytest.mark.asyncio
async def test_006_aisla_tablas_del_2_0(engine: AsyncEngine) -> None:
    """Una tabla simulada del 2.0 sobrevive intacta al upgrade y al downgrade."""
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS _t014_legacy CASCADE"))
        await conn.execute(text("CREATE TABLE _t014_legacy (id INT PRIMARY KEY, payload TEXT)"))
        await conn.execute(text("INSERT INTO _t014_legacy (id, payload) VALUES (1, 'intacto')"))
    try:
        await _apply_006(engine)  # upgrade
        await _drop_enterprise(engine)  # downgrade (DROP idempotente)
        async with engine.connect() as conn:
            r = await conn.execute(text("SELECT payload FROM _t014_legacy WHERE id = 1"))
            assert r.scalar_one() == "intacto"
    finally:
        async with engine.begin() as conn:
            await conn.execute(text("DROP TABLE IF EXISTS _t014_legacy CASCADE"))
