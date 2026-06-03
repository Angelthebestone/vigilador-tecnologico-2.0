"""F5a.A / T123 — Dreaming scheduler MVP allow-list tests.

Verifies that the scheduler MVP exposes exactly two phase names and
filters anything else out, and that cron / idle behaviour is preserved.
"""

from __future__ import annotations

import time

from vigilancia_multiagente.enterprise.dreaming.scheduler import (
    DreamingScheduler,
    DreamingSchedulerConfig,
    is_mvp_phase,
    mvp_phase_names,
)

# ---------------------------------------------------------------------------
# T123 #1 — APScheduler-style cron 3 AM is the default config
# ---------------------------------------------------------------------------


def test_cron_default_hour_is_3am() -> None:
    """Per FR-039 the default dreaming cycle runs at 3 AM."""
    scheduler = DreamingScheduler()
    assert scheduler.config.cron_hour == 3
    assert scheduler.should_trigger_cron(3) is True
    assert scheduler.should_trigger_cron(4) is False


# ---------------------------------------------------------------------------
# T123 #2 — idle trigger fires outside the cron window
# ---------------------------------------------------------------------------


def test_idle_trigger_fires_outside_cron_window() -> None:
    """idle_timeout_min default 10 — 11 minutes of inactivity must trigger."""
    scheduler = DreamingScheduler(DreamingSchedulerConfig(idle_timeout_min=10))
    scheduler._last_activity_ts = time.time() - 11 * 60
    # We are NOT at 3 AM in the test, but idle still fires:
    assert scheduler.is_idle_triggered() is True


# ---------------------------------------------------------------------------
# T123 #3 — MVP only registers 2 phases
# ---------------------------------------------------------------------------


def test_mvp_allow_list_is_exactly_two_phases() -> None:
    """FR-040 — only memory_consolidation + ingestion_sync may register."""
    names = mvp_phase_names()
    assert names == ("memory_consolidation", "ingestion_sync")
    assert len(names) == 2

    assert is_mvp_phase("memory_consolidation") is True
    assert is_mvp_phase("ingestion_sync") is True


# ---------------------------------------------------------------------------
# T123 #4 — no roadmap phase is registered
# ---------------------------------------------------------------------------


def test_roadmap_phase_names_filtered_out() -> None:
    """The 8 extra phases + 7 loops must NOT pass the allow-list filter."""
    candidates = [
        # 8 phases on the F5b roadmap:
        "admin_repo_maintenance",
        "config_refresher",
        "dreaming_report",
        "index_maintenance",
        "regulatory_watch",
        "scheduled_artifacts",
        "self_improvement",
        "skill_curator",
        # 7 loops:
        "admin_repo_loop",
        "company_self_update",
        "prompt_self_improvement",
        "regulatory_watcher",
        "skill_learning",
        "tool_composition",
        "writing_style",
        # The 2 MVP phases — these are the only survivors:
        "memory_consolidation",
        "ingestion_sync",
    ]

    filtered = DreamingScheduler.filter_to_mvp(candidates)
    assert filtered == ["memory_consolidation", "ingestion_sync"]
    for name in candidates:
        if name not in {"memory_consolidation", "ingestion_sync"}:
            assert is_mvp_phase(name) is False, f"{name} leaked into MVP allow-list"
