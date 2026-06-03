"""PlaybookRunner — executes a playbook YAML against a ``ModeContext``.

Spec 021 FR-018 / F4a.A T094.

A playbook YAML has the shape::

    id: deep-research
    display_name: "Deep research"
    description: "Clarify -> Plan -> Approve -> Execute -> Fuse -> Report"
    mode_compatible: ["*"]            # or ["CEO", "default"]
    agents:
      - id: lead
        skill: "k_dense.literature.arxiv-paper-search"
      - id: synth
        skill: "agency_agents.specialized.synthesizer"
    flow:
      type: "sequential"              # | "rounds"
      steps:                          # for sequential
        - { agent: "lead",  input_key: "query" }
        - { agent: "synth", input_key: "lead.output" }
      rounds:                         # for rounds
        max: 3
        agents: ["lead", "synth"]
    guardrails:
      max_total_llm_calls: 20
      max_runtime_s: 300

Constitución:
* SRP: this module loads + validates + runs. It does NOT implement individual
  agents (those live in ``application/`` or ``plugins/``).
* OCP: new flow types plug in via the dispatch table — no edits to core run()
  required. Today only ``sequential`` and ``rounds`` are wired.
* DIP: depends on an ``AgentExecutor`` Protocol; adapters supply the actual
  agent invocation (e.g. wrapping ``BranchCoordinator`` 2.0 for technology-watch).
* #4 explicit errors: malformed YAML, mode mismatch, or guardrail breach all
  raise a typed exception with context.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import yaml

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AgentSpec:
    id: str
    skill: str = ""
    config: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PlaybookConfig:
    id: str
    display_name: str
    description: str
    mode_compatible: tuple[str, ...]
    agents: tuple[AgentSpec, ...]
    flow_type: str
    flow_steps: tuple[dict[str, Any], ...]
    flow_rounds: dict[str, Any]
    guardrails: dict[str, Any]


@dataclass(frozen=True)
class PlaybookRunResult:
    playbook_id: str
    completed_steps: int
    total_llm_calls: int
    duration_s: float
    outputs: dict[str, Any]


class PlaybookError(RuntimeError):
    """Raised when a playbook fails validation or hits a guardrail."""


class AgentExecutor(Protocol):
    """The minimal surface ``PlaybookRunner`` needs from agents."""

    async def execute(
        self, agent_id: str, inputs: dict[str, Any]
    ) -> dict[str, Any]:
        """Run ``agent_id`` against ``inputs`` and return a dict (output)."""
        ...


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def load_playbook(path: Path) -> PlaybookConfig:
    """Load + validate a playbook YAML."""
    if not path.is_file():
        raise PlaybookError(f"playbook file not found: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise PlaybookError(f"playbook YAML invalid ({path}): {exc}") from exc
    if not isinstance(data, dict):
        raise PlaybookError(f"playbook must be a mapping at top level ({path})")

    pb_id = data.get("id")
    if not isinstance(pb_id, str) or not pb_id:
        raise PlaybookError(f"playbook missing 'id' ({path})")

    mode_raw = data.get("mode_compatible") or []
    if isinstance(mode_raw, str):
        mode_compatible: tuple[str, ...] = (mode_raw,)
    elif isinstance(mode_raw, list):
        mode_compatible = tuple(str(x) for x in mode_raw)
    else:
        raise PlaybookError(
            f"playbook {pb_id!r}: mode_compatible must be string or list"
        )

    agents_raw = data.get("runner_agents") or data.get("agents") or []
    if not isinstance(agents_raw, list):
        raise PlaybookError(f"playbook {pb_id!r}: agents must be a list")
    agents: list[AgentSpec] = []
    for entry in agents_raw:
        if not isinstance(entry, dict) or "id" not in entry:
            raise PlaybookError(
                f"playbook {pb_id!r}: agent entry missing 'id': {entry!r}"
            )
        agents.append(
            AgentSpec(
                id=str(entry["id"]),
                skill=str(entry.get("skill", "")),
                config=dict(entry.get("config", {})),
            )
        )

    flow = data.get("flow") or {}
    if not isinstance(flow, dict):
        raise PlaybookError(f"playbook {pb_id!r}: flow must be a mapping")
    flow_type = str(flow.get("type", "")).lower()
    if flow_type not in ("sequential", "rounds"):
        raise PlaybookError(
            f"playbook {pb_id!r}: flow.type must be 'sequential' or 'rounds' "
            f"(got {flow_type!r})"
        )
    flow_steps_raw = flow.get("steps") or []
    if not isinstance(flow_steps_raw, list):
        raise PlaybookError(f"playbook {pb_id!r}: flow.steps must be a list")
    flow_steps = tuple(dict(s) for s in flow_steps_raw)
    flow_rounds = dict(flow.get("rounds") or {})

    guardrails = dict(data.get("guardrails") or {})
    return PlaybookConfig(
        id=pb_id,
        display_name=str(data.get("display_name", pb_id)),
        description=str(data.get("description", "")),
        mode_compatible=mode_compatible,
        agents=tuple(agents),
        flow_type=flow_type,
        flow_steps=flow_steps,
        flow_rounds=flow_rounds,
        guardrails=guardrails,
    )


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


@dataclass
class PlaybookRunner:
    """Executes playbooks via an injected ``AgentExecutor``."""

    executor: AgentExecutor

    async def run(
        self,
        playbook: PlaybookConfig,
        *,
        active_mode: str,
        initial_inputs: dict[str, Any] | None = None,
    ) -> PlaybookRunResult:
        """Run ``playbook`` under ``active_mode``.

        Raises ``PlaybookError`` if the mode is not in ``mode_compatible`` or
        a guardrail trips during execution.
        """
        self._check_mode(playbook, active_mode)
        agents_by_id = {a.id: a for a in playbook.agents}
        outputs: dict[str, Any] = dict(initial_inputs or {})
        started = time.monotonic()
        total_llm_calls = 0
        completed = 0

        max_calls = int(playbook.guardrails.get("max_total_llm_calls", 100))
        max_runtime = float(playbook.guardrails.get("max_runtime_s", 0)) or None

        if playbook.flow_type == "sequential":
            for idx, step in enumerate(playbook.flow_steps):
                self._enforce_runtime(started, max_runtime, playbook.id)
                total_llm_calls = self._enforce_llm_budget(
                    total_llm_calls, max_calls, playbook.id, completed
                )
                agent_id = str(step.get("agent", ""))
                if agent_id not in agents_by_id:
                    raise PlaybookError(
                        f"playbook {playbook.id!r}: step {idx} references "
                        f"unknown agent {agent_id!r}"
                    )
                inputs = self._resolve_inputs(step, outputs)
                step_out = await self.executor.execute(agent_id, inputs)
                outputs[agent_id] = step_out
                completed += 1
                total_llm_calls += int(step_out.get("_llm_calls", 1))
        elif playbook.flow_type == "rounds":
            rounds_max = int(playbook.flow_rounds.get("max", 1))
            round_agents = list(playbook.flow_rounds.get("agents", []))
            if not round_agents:
                raise PlaybookError(
                    f"playbook {playbook.id!r}: flow.rounds.agents empty"
                )
            for r in range(rounds_max):
                self._enforce_runtime(started, max_runtime, playbook.id)
                total_llm_calls = self._enforce_llm_budget(
                    total_llm_calls, max_calls, playbook.id, completed
                )
                round_outputs: dict[str, Any] = {}
                for agent_id in round_agents:
                    if agent_id not in agents_by_id:
                        raise PlaybookError(
                            f"playbook {playbook.id!r}: round agent "
                            f"{agent_id!r} not declared in agents[]"
                        )
                    inputs = {"round": r, "previous": outputs}
                    step_out = await self.executor.execute(agent_id, inputs)
                    round_outputs[agent_id] = step_out
                    total_llm_calls += int(step_out.get("_llm_calls", 1))
                outputs[f"round_{r}"] = round_outputs
                completed += 1
        else:  # pragma: no cover — guarded in load_playbook
            raise PlaybookError(
                f"playbook {playbook.id!r}: unsupported flow.type {playbook.flow_type!r}"
            )

        duration = time.monotonic() - started
        logger.info(
            "PlaybookRunner: %s completed in %.2fs (%d steps, %d LLM calls)",
            playbook.id, duration, completed, total_llm_calls,
        )
        return PlaybookRunResult(
            playbook_id=playbook.id,
            completed_steps=completed,
            total_llm_calls=total_llm_calls,
            duration_s=duration,
            outputs=outputs,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _check_mode(playbook: PlaybookConfig, active_mode: str) -> None:
        compat = playbook.mode_compatible
        if "*" in compat or active_mode in compat:
            return
        raise PlaybookError(
            f"playbook {playbook.id!r} not compatible with mode "
            f"{active_mode!r} (compat={compat!r})"
        )

    @staticmethod
    def _resolve_inputs(
        step: dict[str, Any], outputs: dict[str, Any]
    ) -> dict[str, Any]:
        inputs: dict[str, Any] = {}
        for k, v in step.items():
            if k == "agent":
                continue
            if k == "input_key" and isinstance(v, str):
                # Dotted lookup: "agent_id.field" or just "agent_id"
                parts = v.split(".")
                root = outputs.get(parts[0])
                cursor: Any = root
                for p in parts[1:]:
                    if isinstance(cursor, dict):
                        cursor = cursor.get(p)
                    else:
                        cursor = None
                        break
                inputs[v] = cursor
            else:
                inputs[k] = v
        return inputs

    @staticmethod
    def _enforce_llm_budget(
        used: int, budget: int, pb_id: str, step: int
    ) -> int:
        if budget > 0 and used >= budget:
            raise PlaybookError(
                f"playbook {pb_id!r}: max_total_llm_calls={budget} reached "
                f"after step {step}"
            )
        return used

    @staticmethod
    def _enforce_runtime(
        started: float, limit: float | None, pb_id: str
    ) -> None:
        if limit is None:
            return
        if time.monotonic() - started > limit:
            raise PlaybookError(
                f"playbook {pb_id!r}: max_runtime_s={limit:.1f}s exceeded"
            )
