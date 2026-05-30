"""Tests para migración 010_pi_quarantine.sql (T012) — requiere PostgreSQL."""

from __future__ import annotations

import pytest

# NOTE: These tests require a running PostgreSQL instance.
pytestmark = pytest.mark.skipif(
    True,
    reason="Requires PostgreSQL; run with --run-pg flag or set TEST_DATABASE_URL",
)
