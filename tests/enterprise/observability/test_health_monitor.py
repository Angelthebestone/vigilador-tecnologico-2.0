"""Tests for HealthMonitor (F1.3)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from freezegun import freeze_time

from vigilancia_multiagente.enterprise.observability.health_monitor import HealthMonitor
from vigilancia_multiagente.enterprise.tooling.tool_wrapper import HealthcheckResult


def _make_tool(name: str = "tool_a", healthy: bool = True) -> MagicMock:
    tool = MagicMock()
    tool.name = name
    tool.domain = "test"
    tool.is_external_mcp = False
    tool.requires_auth = False
    if healthy:
        tool.healthcheck = AsyncMock(
            return_value=HealthcheckResult(status="UP", latency_ms=10.0, error=None)
        )
    else:
        tool.healthcheck = AsyncMock(
            return_value=HealthcheckResult(status="DOWN", latency_ms=None, error="timeout")
        )
    return tool


def _make_registry(tools: list[MagicMock]) -> MagicMock:
    registry = MagicMock()
    registry._tools = {t.name: t for t in tools}
    return registry


def _make_settings(**overrides: object) -> MagicMock:
    defaults = {
        "health_monitor_interval_sec": 30,
        "health_monitor_cb_threshold": 3,
        "health_monitor_cb_window_sec": 60,
        "health_monitor_cooldown_sec": 300,
        "default_tenant_id": "00000000-0000-0000-0000-000000000001",
    }
    defaults.update(overrides)
    s = MagicMock()
    for k, v in defaults.items():
        setattr(s, k, v)
    return s


@pytest.mark.asyncio
@freeze_time("2026-01-01 00:00:00", tz_offset=0)
async def test_tick_invokes_healthcheck_on_each_tool(tmp_path):
    """Ciclo cada 30s invoca healthcheck en cada tool registrada."""
    tools = [_make_tool("tool_a"), _make_tool("tool_b")]
    registry = _make_registry(tools)
    repo = AsyncMock()
    settings = _make_settings()

    monitor = HealthMonitor(
        tool_registry=registry,
        tool_health_repo=repo,
        settings=settings,
        audit_dir=tmp_path,
    )
    await monitor._tick()

    for t in tools:
        t.healthcheck.assert_awaited_once()
    assert repo.upsert.await_count == 2


@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_threshold(tmp_path):
    """Circuit breaker abre tras 3 fallos en 60s."""
    tool = _make_tool("failing_tool", healthy=False)
    registry = _make_registry([tool])
    repo = AsyncMock()
    settings = _make_settings(health_monitor_cb_threshold=3, health_monitor_cb_window_sec=60)

    monitor = HealthMonitor(
        tool_registry=registry,
        tool_health_repo=repo,
        settings=settings,
        audit_dir=tmp_path,
    )

    with freeze_time("2026-01-01 00:00:00", tz_offset=0) as frozen:
        await monitor._tick()
        frozen.tick(10)
        await monitor._tick()
        frozen.tick(10)
        await monitor._tick()

    # After 3 failures, last upsert should have status DOWN
    last_call = repo.upsert.call_args_list[-1]
    row = last_call[0][0]
    assert row.status == "DOWN"
    assert row.fail_count >= 3


@pytest.mark.asyncio
async def test_cooldown_prevents_recheck(tmp_path):
    """Status DOWN se mantiene ≥ 5 min (cooldown)."""
    tool = _make_tool("cool_tool", healthy=False)
    registry = _make_registry([tool])
    repo = AsyncMock()
    settings = _make_settings(
        health_monitor_cb_threshold=1,
        health_monitor_cooldown_sec=300,
    )

    monitor = HealthMonitor(
        tool_registry=registry,
        tool_health_repo=repo,
        settings=settings,
        audit_dir=tmp_path,
    )

    with freeze_time("2026-01-01 00:00:00", tz_offset=0) as frozen:
        # First tick triggers circuit breaker (threshold=1)
        await monitor._tick()
        call_count_after_down = tool.healthcheck.await_count

        # Tick 60s later — still within cooldown (300s)
        frozen.tick(60)
        await monitor._tick()

        # healthcheck should NOT have been called again
        assert tool.healthcheck.await_count == call_count_after_down


@pytest.mark.asyncio
@freeze_time("2026-01-01 00:00:00", tz_offset=0)
async def test_writes_jsonl_log(tmp_path):
    """Escribe línea JSONL al log."""
    tool = _make_tool("logged_tool")
    registry = _make_registry([tool])
    repo = AsyncMock()
    settings = _make_settings()

    monitor = HealthMonitor(
        tool_registry=registry,
        tool_health_repo=repo,
        settings=settings,
        audit_dir=tmp_path,
    )
    await monitor._tick()

    log_file = tmp_path / "healthcheck.log"
    assert log_file.exists()
    line = json.loads(log_file.read_text().strip())
    assert line["tool"] == "logged_tool"
    assert line["status"] == "UP"
    assert "ts" in line
    assert "latency_ms" in line
    assert "error" in line
