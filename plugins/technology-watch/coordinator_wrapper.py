"""Coordinator wrapper — delegates ``technology-watch`` playbook to
:class:`BranchCoordinator` (2.0).

Spec 021 F4a.D / T107. The plugin implements the ``AgentExecutor`` shape
that ``PlaybookRunner`` calls, but it does NOT subclass ``BranchCoordinator`` —
it wraps an existing instance via composition. This preserves constitución
#5 (cambios quirúrgicos): ``application/execution/branch_coordinator.py``
stays unchanged.

The mapping from playbook-side agent ids to 2.0 branch ids is declared
in ``technology-watch.yaml`` and resolved here at construction time. When
the runner calls ``execute(agent_id, inputs)``, this module routes it as
either:

* ``"coordinator"`` — runs the full 2.0 flow (the typical case for the MVP);
* ``"<branch_id>"``  — runs a single branch (for advanced future fan-outs).

Returns are normalised to dicts so ``PlaybookRunner.outputs`` carries
structured data the agent can post-process.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


class _BranchCoordinatorProto(Protocol):
    """The minimal slice of ``BranchCoordinator`` we depend on."""

    async def execute(self, session: Any, plan: Any) -> list[Any]: ...


@dataclass
class TechnologyWatchExecutor:
    """``AgentExecutor`` shim around a 2.0 ``BranchCoordinator`` instance."""

    coordinator: _BranchCoordinatorProto
    """Live :class:`BranchCoordinator` instance — wired by the composition root."""

    session_factory: Any | None = None
    """Optional callable that builds a ``ResearchSession`` from inputs.

    When ``None``, the wrapper assembles a minimal stub: ``id=uuid4()``,
    ``query`` taken from ``inputs['query']`` (or the only string value).
    Real wiring (``application.session.SessionFactory``) is the
    composition root's responsibility — kept optional so unit tests
    can drive the wrapper with a fake coordinator.
    """

    plan_factory: Any | None = None
    """Optional callable that builds a ``ResearchPlan`` from inputs."""

    async def execute(
        self, agent_id: str, inputs: dict[str, Any]
    ) -> dict[str, Any]:
        """Run the 2.0 coordinator (or a single branch) under ``agent_id``."""
        if agent_id == "coordinator":
            return await self._run_full_flow(inputs)
        # Per-branch routing is a roadmap path; for the MVP, the playbook
        # only declares a single ``coordinator`` agent that drives all 6
        # branches via the existing 2.0 logic.
        raise ValueError(
            f"TechnologyWatchExecutor: unknown agent_id '{agent_id}' — "
            f"the MVP playbook only declares 'coordinator'"
        )

    async def _run_full_flow(self, inputs: dict[str, Any]) -> dict[str, Any]:
        session = self._build_session(inputs)
        plan = self._build_plan(inputs)
        results = await self.coordinator.execute(session, plan)
        # ``BranchCoordinator.execute`` returns ``list[BranchResult]``; we
        # normalise to dicts for downstream serialisation.
        return {
            "value": [self._branch_result_to_dict(r) for r in results],
            "session_id": str(getattr(session, "id", "")),
            "branches": len(results),
            "_llm_calls": sum(
                int(getattr(r, "llm_calls", 0) or 0) for r in results
            ),
        }

    # ------------------------------------------------------------------
    # Stub builders — real composition root replaces these.
    # ------------------------------------------------------------------

    def _build_session(self, inputs: dict[str, Any]) -> Any:
        if self.session_factory is not None:
            return self.session_factory(inputs)
        # Minimal stub session — enough for the wrapper smoke tests.
        return _StubSession(
            id=uuid4(),
            query=str(inputs.get("query") or _first_string(inputs) or ""),
        )

    def _build_plan(self, inputs: dict[str, Any]) -> Any:
        if self.plan_factory is not None:
            return self.plan_factory(inputs)
        return _StubPlan(query=str(inputs.get("query") or ""))

    @staticmethod
    def _branch_result_to_dict(result: Any) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for attr in ("branch_type", "status", "summary", "findings"):
            value = getattr(result, attr, None)
            if value is not None:
                out[attr] = value if isinstance(value, (str, int, float, list, dict)) else str(value)
        return out


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@dataclass
class _StubSession:
    id: UUID
    query: str


@dataclass
class _StubPlan:
    query: str


def _first_string(inputs: dict[str, Any]) -> str | None:
    for value in inputs.values():
        if isinstance(value, str) and value.strip():
            return value
    return None
