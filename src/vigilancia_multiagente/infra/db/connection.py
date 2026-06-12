import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from vigilancia_multiagente.config.settings import get_settings


class Database:
    def __init__(self) -> None:
        settings = get_settings()
        pool_size = int(os.environ.get("VT_DB_POOL_SIZE", "10"))
        max_overflow = int(os.environ.get("VT_DB_POOL_OVERFLOW", "20"))
        self._engine: AsyncEngine = create_async_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_size=pool_size,
            max_overflow=max_overflow,
        )
        self._sessionmaker = async_sessionmaker(
            self._engine,
            expire_on_commit=False,
            class_=AsyncSession,
        )

    @property
    def engine(self) -> AsyncEngine:
        return self._engine

    async def initialize(self) -> list[str]:
        from vigilancia_multiagente.infra.db.migration_runner import MigrationRunner

        runner = MigrationRunner(self._engine)
        return await runner.apply()

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        async with self._sessionmaker() as session:
            yield session


database = Database()
