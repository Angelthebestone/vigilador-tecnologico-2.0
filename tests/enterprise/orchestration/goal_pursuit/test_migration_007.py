"""Test migration 007_goal_pursuit.sql: idempotency and table isolation."""

from __future__ import annotations

from pathlib import Path

import pytest

MIGRATION_PATH = (
    Path(__file__).resolve().parents[4]
    / "src"
    / "vigilancia_multiagente"
    / "infra"
    / "db"
    / "migrations"
    / "007_goal_pursuit.sql"
)


def _get_sync_db_url() -> str | None:
    """Resolve database URL and convert to sync psycopg2 format."""
    try:
        from tests.enterprise.db_url import resolve_database_url

        url = resolve_database_url()
        if not url:
            return None
        # Convert asyncpg URL to psycopg2 format
        url = url.replace("postgresql+asyncpg://", "postgresql://")
        return url
    except Exception:  # noqa: BLE001
        return None


def _try_connect(url: str) -> bool:
    """Try connecting to the database."""
    try:
        import psycopg2

        conn = psycopg2.connect(url)
        conn.close()
        return True
    except Exception:  # noqa: BLE001
        return False


@pytest.fixture
def db_url() -> str:
    url = _get_sync_db_url()
    if not url:
        pytest.skip("PostgreSQL URL not configured")
    if not _try_connect(url):
        pytest.skip("PostgreSQL not reachable")
    return url


@pytest.fixture
def migration_sql() -> str:
    return MIGRATION_PATH.read_text(encoding="utf-8")


def test_migration_007_is_idempotent(db_url: str, migration_sql: str) -> None:
    """Apply migration twice without error."""
    import psycopg2

    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cur = conn.cursor()
    try:
        for statement in migration_sql.split(";"):
            stmt = statement.strip()
            if stmt:
                cur.execute(stmt)
        for statement in migration_sql.split(";"):
            stmt = statement.strip()
            if stmt:
                cur.execute(stmt)
    finally:
        cur.close()
        conn.close()


def test_existing_tables_intact(db_url: str, migration_sql: str) -> None:
    """Verify existing tables are not affected by migration 007."""
    import psycopg2

    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cur = conn.cursor()
    try:
        for statement in migration_sql.split(";"):
            stmt = statement.strip()
            if stmt:
                cur.execute(stmt)
        for table in ("tool_health", "oauth_credentials", "pending_approvals", "company_profile"):
            cur.execute(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = %s)",
                (table,),
            )
            exists = cur.fetchone()[0]  # type: ignore[index]
            assert exists, f"Table {table} should still exist after migration 007"
    finally:
        cur.close()
        conn.close()
