"""T123 — DB pool configuration from environment variables."""

from __future__ import annotations

import os
from unittest.mock import patch


def test_db_pool_config_reads_env_vars():
    """Verify Database reads VT_DB_POOL_SIZE and VT_DB_POOL_OVERFLOW from env."""
    with patch.dict(os.environ, {"VT_DB_POOL_SIZE": "25", "VT_DB_POOL_OVERFLOW": "50"}):
        from vigilancia_multiagente.infra.db.connection import Database

        db = Database()
        pool = db.engine.pool
        assert pool.size() == 25
        assert pool._max_overflow == 50  # type: ignore[attr-defined]


def test_db_pool_config_defaults():
    """Verify Database uses default pool sizes when env vars not set."""
    env = os.environ.copy()
    env.pop("VT_DB_POOL_SIZE", None)
    env.pop("VT_DB_POOL_OVERFLOW", None)

    with patch.dict(os.environ, env, clear=True):
        from vigilancia_multiagente.infra.db.connection import Database

        db = Database()
        pool = db.engine.pool
        assert pool.size() == 10
        assert pool._max_overflow == 20  # type: ignore[attr-defined]
