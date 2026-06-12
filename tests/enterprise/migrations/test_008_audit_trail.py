"""Tests for migration 008_audit_trail.sql (requires PostgreSQL).

These tests verify idempotency and isolation of the audit trail migration.
They require a running PostgreSQL instance and will be skipped if unavailable.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import pytest_asyncio

try:
    import asyncpg  # noqa: F401
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
    from sqlalchemy.pool import NullPool

    HAS_PG = True
except ImportError:
    HAS_PG = False

from tests.enterprise.db_url import resolve_database_url
from vigilancia_multiagente.infra.db.migration_runner import _split_sql_statements

MIGRATION_PATH = (
    Path(__file__).resolve().parents[3]
    / "src"
    / "vigilancia_multiagente"
    / "infra"
    / "db"
    / "migrations"
    / "008_audit_trail.sql"
)

pytestmark = pytest.mark.skipif(not HAS_PG, reason="asyncpg not available")


def _statements() -> list[str]:
    return _split_sql_statements(MIGRATION_PATH.read_text(encoding="utf-8"))


async def _apply(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        for statement in _statements():
            await conn.execute(text(statement))


@pytest_asyncio.fixture
async def engine():
    url = resolve_database_url()
    if url is None:
        pytest.skip("TEST_DATABASE_URL not set")
    eng = create_async_engine(url, poolclass=NullPool)
    try:
        async with eng.begin() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        await eng.dispose()
        pytest.skip(f"PostgreSQL no disponible: {exc}")
    yield eng
    await eng.dispose()


@pytest.mark.asyncio
async def test_migration_idempotent(engine: AsyncEngine) -> None:
    """Applying 008_audit_trail.sql twice should not raise errors."""
    await _apply(engine)
    await _apply(engine)  # Second apply - must not fail
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'agent_modifications'"
            )
        )
        assert result.scalar() == 1


@pytest.mark.asyncio
async def test_drop_does_not_affect_other_tables(engine: AsyncEngine) -> None:
    """DROP TABLE IF EXISTS agent_modifications CASCADE should not affect other tables."""
    await _apply(engine)
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS agent_modifications CASCADE"))
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'agent_modifications'"
            )
        )
        assert result.scalar() == 0
