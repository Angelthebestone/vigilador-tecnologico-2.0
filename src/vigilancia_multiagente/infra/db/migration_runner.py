from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


class MigrationRunner:
    def __init__(self, engine: AsyncEngine, migrations_dir: Path | None = None) -> None:
        self._engine = engine
        self._migrations_dir = migrations_dir or Path(__file__).with_name("migrations")

    async def apply(self) -> list[str]:
        applied: list[str] = []
        async with self._engine.begin() as connection:
            await connection.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        filename TEXT PRIMARY KEY,
                        applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
            )
            existing = await connection.execute(text("SELECT filename FROM schema_migrations ORDER BY filename"))
            applied_names = {row[0] for row in existing.fetchall()}

            for migration_path in sorted(self._migrations_dir.glob("*.sql")):
                if migration_path.name in applied_names:
                    continue
                for statement in _split_sql_statements(migration_path.read_text(encoding="utf-8")):
                    await connection.execute(text(statement))
                await connection.execute(
                    text("INSERT INTO schema_migrations (filename) VALUES (:filename)"),
                    {"filename": migration_path.name},
                )
                applied.append(migration_path.name)

        return applied


def _split_sql_statements(sql_text: str) -> list[str]:
    statements: list[str] = []
    buffer: list[str] = []
    for line in sql_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        buffer.append(line)
    statement_block = "\n".join(buffer)
    for statement in statement_block.split(";"):
        cleaned = statement.strip()
        if cleaned:
            statements.append(cleaned)
    return statements
