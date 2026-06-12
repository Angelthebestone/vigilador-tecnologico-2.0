"""Tests for DreamingScheduler — T007."""

from __future__ import annotations

import time

from vigilancia_multiagente.enterprise.dreaming.scheduler import (
    DreamingScheduler,
    DreamingSchedulerConfig,
)


def test_cron_triggers_at_configured_hour() -> None:
    config = DreamingSchedulerConfig(cron_hour=3)
    scheduler = DreamingScheduler(config)
    assert scheduler.should_trigger_cron(3)
    assert not scheduler.should_trigger_cron(4)


def test_idle_trigger_detects_inactivity() -> None:
    config = DreamingSchedulerConfig(idle_timeout_min=10)
    scheduler = DreamingScheduler(config)
    # Simulate last activity was 11 minutes ago
    scheduler._last_activity_ts = time.time() - 11 * 60
    assert scheduler.is_idle_triggered()


def test_interaction_activates_pause_flag() -> None:
    scheduler = DreamingScheduler()
    assert not scheduler.interaction_active
    scheduler.record_activity()
    assert scheduler.interaction_active
    scheduler.clear_interaction()
    assert not scheduler.interaction_active


def test_custom_config_respected() -> None:
    config = DreamingSchedulerConfig(enabled=False, cron_hour=5, idle_timeout_min=20)
    scheduler = DreamingScheduler(config)
    assert not scheduler.enabled
    assert not scheduler.should_trigger_cron(5)  # disabled
    assert not scheduler.is_idle_triggered()  # disabled
