"""F4a.D / T109 — verify ``technology-watch`` wraps the 2.0 ``BranchCoordinator``.

Constitución #5 — assert via ``git diff --stat`` that the 2.0 file is
unchanged after this work; here we test the runtime invariants:

* Calling the wrapper invokes ``BranchCoordinator.execute(session, plan)``.
* Outputs come back structured (list of branch dicts) for ``PlaybookRunner``.
* The ``technology-watch`` playbook YAML loads cleanly via ``PlaybookRunner``.
"""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
PLUGIN = REPO / "plugins" / "technology-watch" / "coordinator_wrapper.py"


def _import_coordinator_wrapper():
    """Dynamic import — the plugin lives outside the ``src/`` package tree."""
    spec = importlib.util.spec_from_file_location("technology_watch_wrapper", PLUGIN)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["technology_watch_wrapper"] = mod
    spec.loader.exec_module(mod)
    return mod


@dataclass
class _FakeBranchResult:
    branch_type: str
    status: str = "completed"
    summary: str = "ok"
    findings: list = None
    llm_calls: int = 3

    def __post_init__(self):
        if self.findings is None:
            self.findings = []


class _FakeBranchCoordinator:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    async def execute(self, session, plan):
        self.calls.append((session, plan))
        return [
            _FakeBranchResult(branch_type=b)
            for b in (
                "avances_tecnologicos",
                "inteligencia_comercial",
                "normativa",
                "riesgos",
                "mercado",
                "social",
            )
        ]


@pytest.mark.asyncio
async def test_wrapper_invokes_branch_coordinator_with_session_and_plan():
    mod = _import_coordinator_wrapper()
    coordinator = _FakeBranchCoordinator()
    executor = mod.TechnologyWatchExecutor(coordinator=coordinator)
    result = await executor.execute("coordinator", {"query": "RAG vendors 2026"})
    assert coordinator.calls, "BranchCoordinator was not invoked"
    session, plan = coordinator.calls[0]
    assert getattr(session, "query", "") == "RAG vendors 2026"
    assert getattr(plan, "query", "") == "RAG vendors 2026"
    assert result["branches"] == 6
    assert isinstance(result["value"], list)
    assert {b["branch_type"] for b in result["value"]} == {
        "avances_tecnologicos",
        "inteligencia_comercial",
        "normativa",
        "riesgos",
        "mercado",
        "social",
    }


@pytest.mark.asyncio
async def test_wrapper_rejects_unknown_agent_id():
    mod = _import_coordinator_wrapper()
    executor = mod.TechnologyWatchExecutor(coordinator=_FakeBranchCoordinator())
    with pytest.raises(ValueError, match="unknown agent_id"):
        await executor.execute("not-the-coordinator", {})


@pytest.mark.asyncio
async def test_technology_watch_playbook_yaml_loads_cleanly():
    """The runner must accept the normalized YAML without errors."""
    from vigilancia_multiagente.enterprise.orchestration.playbook_runner import (
        load_playbook,
    )

    pb_path = REPO / "config" / "playbooks" / "technology-watch.yaml"
    if not pb_path.is_file():
        pytest.skip("playbook missing in this checkout")
    pb = load_playbook(pb_path)
    assert pb.id == "technology-watch"
    assert pb.flow_type == "sequential"
    assert pb.agents[0].id == "coordinator"
    assert "vigilancia-tech" in pb.mode_compatible
