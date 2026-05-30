"""T020 — CRUD básico de los 3 repositorios enterprise contra DB real.

Aplica la migración 006 aislada en un fixture (sin depender de 001-005, que
requieren pgvector). Se salta si PostgreSQL no está disponible.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from tests.enterprise.db_url import resolve_database_url
from vigilancia_multiagente.infra.db.migration_runner import _split_sql_statements
from vigilancia_multiagente.infra.persistence.company_profile_repository import (
    CompanyProfile,
    CompanyProfileRepository,
)
from vigilancia_multiagente.infra.persistence.oauth_credentials_repository import (
    OAuthCredentialsRepository,
    OAuthRow,
)
from vigilancia_multiagente.infra.persistence.tool_health_repository import (
    ToolHealthRepository,
    ToolHealthRow,
)

ENTERPRISE_TABLES = (
    "tool_health",
    "oauth_credentials",
    "subagents",
    "pending_approvals",
    "company_profile",
)
MIGRATION_PATH = Path("src/vigilancia_multiagente/infra/db/migrations/006_mvp_foundation.sql")


class _TestDatabase:
    """Adaptador `Database`-like sobre un engine NullPool dedicado al test.

    Reproduce solo la superficie que usan los repositorios (`.session()`), sin
    el engine module-level del 2.0, para evitar el cruce de event loops en
    Windows (ProactorEventLoop + asyncpg + pool persistente).
    """

    def __init__(self, db_url: str) -> None:
        self._engine = create_async_engine(db_url, poolclass=NullPool)
        self._sessionmaker = async_sessionmaker(
            self._engine, expire_on_commit=False, class_=AsyncSession
        )

    @property
    def engine(self):
        return self._engine

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        async with self._sessionmaker() as session:
            yield session

    async def dispose(self) -> None:
        await self._engine.dispose()


@pytest_asyncio.fixture
async def database():
    db_url = resolve_database_url()
    if not db_url:
        pytest.skip("VT_DATABASE_URL no resoluble")
    db = _TestDatabase(db_url)
    try:
        try:
            async with db.engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
        except Exception as exc:
            pytest.skip(f"PostgreSQL no disponible: {exc}")

        async with db.engine.begin() as conn:
            for tbl in reversed(ENTERPRISE_TABLES):
                await conn.execute(text(f"DROP TABLE IF EXISTS {tbl} CASCADE"))
            for st in _split_sql_statements(MIGRATION_PATH.read_text(encoding="utf-8")):
                await conn.execute(text(st))
        yield db
    finally:
        async with db.engine.begin() as conn:
            for tbl in reversed(ENTERPRISE_TABLES):
                await conn.execute(text(f"DROP TABLE IF EXISTS {tbl} CASCADE"))
        await db.dispose()


@pytest.mark.asyncio
async def test_tool_health_crud(database: _TestDatabase) -> None:
    repo = ToolHealthRepository(database)
    tenant = uuid4()
    now = datetime.now(UTC)

    assert await repo.read_status("tavily", tenant) is None

    await repo.upsert(
        ToolHealthRow(
            name="tavily",
            tenant_id=tenant,
            status="UP",
            last_check=now,
            fail_count=0,
            last_error=None,
            domain="search",
            requires_key=True,
        )
    )
    row = await repo.read_status("tavily", tenant)
    assert row is not None
    assert row.status == "UP"
    assert row.domain == "search"
    assert row.requires_key is True

    # update vía upsert
    await repo.upsert(
        ToolHealthRow(
            name="tavily",
            tenant_id=tenant,
            status="DOWN",
            last_check=now,
            fail_count=3,
            last_error="timeout",
            domain="search",
            requires_key=True,
        )
    )
    row = await repo.read_status("tavily", tenant)
    assert row is not None
    assert row.status == "DOWN"
    assert row.fail_count == 3
    assert row.last_error == "timeout"

    listed = await repo.list_all(tenant)
    assert [r.name for r in listed] == ["tavily"]


@pytest.mark.asyncio
async def test_oauth_credentials_crud(database: _TestDatabase) -> None:
    repo = OAuthCredentialsRepository(database)
    tenant = uuid4()
    expires = datetime.now(UTC) + timedelta(days=30)

    assert await repo.get("github", tenant) is None

    await repo.store(
        OAuthRow(
            tenant_id=tenant,
            provider="github",
            token_encrypted="enc-token",
            refresh_token_encrypted="enc-refresh",
            expires_at=expires,
            scopes=["repo", "read:user"],
        )
    )
    row = await repo.get("github", tenant)
    assert row is not None
    assert row.token_encrypted == "enc-token"
    assert row.refresh_token_encrypted == "enc-refresh"
    assert row.scopes == ["repo", "read:user"]

    # update vía store (conflicto tenant+provider)
    await repo.store(
        OAuthRow(
            tenant_id=tenant,
            provider="github",
            token_encrypted="enc-token-2",
            scopes=["repo"],
        )
    )
    row = await repo.get("github", tenant)
    assert row is not None
    assert row.token_encrypted == "enc-token-2"
    assert row.refresh_token_encrypted is None
    assert row.scopes == ["repo"]

    await repo.delete("github", tenant)
    assert await repo.get("github", tenant) is None


@pytest.mark.asyncio
async def test_company_profile_crud(database: _TestDatabase) -> None:
    repo = CompanyProfileRepository(database)
    tenant = uuid4()

    assert await repo.get(tenant) is None

    await repo.upsert(
        CompanyProfile(
            tenant_id=tenant,
            name="Acme",
            sector="energia",
            country="Colombia",
            department="Santander",
            municipality="Bucaramanga",
            timezone="America/Bogota",
        )
    )
    profile = await repo.get(tenant)
    assert profile is not None
    assert profile.name == "Acme"
    assert profile.municipality == "Bucaramanga"

    # update vía upsert
    await repo.upsert(
        CompanyProfile(
            tenant_id=tenant,
            name="Acme S.A.",
            sector="energia",
            country="Colombia",
            department="Santander",
            municipality="Floridablanca",
            timezone="America/Bogota",
        )
    )
    profile = await repo.get(tenant)
    assert profile is not None
    assert profile.name == "Acme S.A."
    assert profile.municipality == "Floridablanca"
