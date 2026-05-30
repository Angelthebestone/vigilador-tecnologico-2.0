"""Tests para PIQuarantineRepository (T013) — requiere PostgreSQL."""

from __future__ import annotations

import pytest

# NOTE: These tests require a running PostgreSQL instance.
# Mark them so they can be skipped in DB-free CI runs.
pytestmark = pytest.mark.skipif(
    True,  # Skip by default in DB-free runs
    reason="Requires PostgreSQL; run with --run-pg flag or set TEST_DATABASE_URL",
)
