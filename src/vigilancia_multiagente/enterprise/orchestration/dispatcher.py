"""Dispatcher — composition root for the spec-021 request flow.

Spec 021 F4a.H / T121. Wires:

    ChannelGateway (HTTP request body) →
    ModeResolver (5-step cascade) →
    ModeContext (frozen snapshot) →
    ComplexityClassifier (1 LLM call) →
    PlaybookRunner (loads YAML + runs agents) →
    (TechnologyWatchExecutor | LLMAgentExecutor) →
    ToolRegistry (universal Tool abstraction)

The dispatcher uses :class:`LLMAgentExecutor` for ``general`` and ``deep-research``
playbook agents, which calls the LLM when available and falls back to a structured
response when the LLM client is not configured.
The ``technology-watch`` agent uses :class:`TechnologyWatchExecutor`
wrapping ``BranchCoordinator``.

Constitución:
* SRP: one module = composition + dispatch glue.
* DIP: every dependency arrives as a Protocol-shaped object via the
  ``DispatcherDeps`` dataclass. Tests inject fakes; production wires
  real instances from ``api/enterprise_composition.py``.
* #4 explicit: missing deps surface as ``DispatcherUnavailableError``;
  unknown modes / playbooks raise typed errors with context.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from vigilancia_multiagente.domain.system_base import MiniMaxMessage
from vigilancia_multiagente.enterprise.modes.mode_resolver import (
    ModeResolver,
)
from vigilancia_multiagente.enterprise.modes.mode_resolver_cascade import (
    CascadeResolver,
    ResolutionRequest,
)
from vigilancia_multiagente.enterprise.orchestration.complexity_classifier import (
    ComplexityClassifier,
)
from vigilancia_multiagente.enterprise.orchestration.playbook_runner import (
    PlaybookError,
    PlaybookRunner,
    PlaybookRunResult,
    load_playbook,
)
from vigilancia_multiagente.infra.llm.minimax_client import MiniMaxClient

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class DispatcherUnavailableError(RuntimeError):
    """Raised when a required dispatcher dependency is not configured."""


class DispatcherInputError(ValueError):
    """Raised when the request payload is malformed."""


# ---------------------------------------------------------------------------
# LLM executor (real agent execution via MiniMaxClient)
# ---------------------------------------------------------------------------


class LLMAgentExecutor:
    """LLM-backed executor that generates real responses via MiniMaxClient.

    Falls back to stub behavior when llm_client is None.
    """

    def __init__(self, llm_client: MiniMaxClient | None = None, label: str = "llm") -> None:
        self.llm_client = llm_client
        self.label = label
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def execute(self, agent_id: str, inputs: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((agent_id, dict(inputs)))
        if self.llm_client is not None:
            try:
                messages = [MiniMaxMessage(role="user", content=str(inputs))]
                response = await self.llm_client.complete(messages)
                return {
                    "agent": agent_id,
                    "label": self.label,
                    "value": response.content,
                    "_llm_calls": 1,
                }
            except Exception as exc:
                logger.warning(
                    "LLMAgentExecutor: LLM call failed for agent %s: %s — falling back to stub",
                    agent_id,
                    exc,
                )
        # Fallback to stub behavior
        return {
            "agent": agent_id,
            "label": self.label,
            "value": (
                f"[stub:{self.label}] agent={agent_id} acknowledged. "
                "Real LLM execution lands in F4b/F5."
            ),
            "_llm_calls": 0,
        }


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


@dataclass
class DispatcherDeps:
    """Bundle of dependencies the dispatcher consumes."""

    cascade_resolver: CascadeResolver
    mode_resolver: ModeResolver
    complexity_classifier: ComplexityClassifier | None
    playbook_dir: Path
    executor_by_playbook: dict[str, Any] = field(default_factory=dict)
    """playbook_id → AgentExecutor."""
    llm_client: Any = None
    """Optional LLM client for LLMAgentExecutor fallback."""


@dataclass(frozen=True)
class DispatchRequest:
    session_id: str
    message: str
    channel_id: str = "chat"
    mode_hint: str | None = None


@dataclass(frozen=True)
class DispatchResponse:
    session_id: str
    resolved_mode: str
    playbook_id: str
    complexity: str | None
    complexity_reason: str | None
    run_result: PlaybookRunResult


class Dispatcher:
    """End-to-end request orchestrator for the spec-021 MVP flow."""

    def __init__(self, deps: DispatcherDeps) -> None:
        self._deps = deps

    async def dispatch(self, request: DispatchRequest) -> DispatchResponse:
        # 1. Mode cascade
        resolution = ResolutionRequest(
            session_id=request.session_id,
            channel_id=request.channel_id,
            message=request.message,
            explicit_mode=request.mode_hint,
        )
        mode_id = await self._deps.cascade_resolver.resolve(resolution)
        mode_config = self._deps.mode_resolver.activate(request.session_id, mode_id)

        # 2. Complexity classification (optional)
        complexity_level: str | None = None
        complexity_reason: str | None = None
        if self._deps.complexity_classifier is not None:
            try:
                decision = await self._deps.complexity_classifier.classify(request.message)
                complexity_level = decision.level.value
                complexity_reason = decision.reason
            except Exception as exc:
                logger.warning(
                    "Dispatcher: complexity classifier failed: %s — proceeding "
                    "without classification",
                    exc,
                )

        # 3. Resolve playbook from mode + (optional) complexity routing
        playbook_id = self._select_playbook(mode_config)
        playbook_path = self._deps.playbook_dir / f"{playbook_id}.yaml"
        try:
            playbook = load_playbook(playbook_path)
        except PlaybookError as exc:
            raise DispatcherUnavailableError(
                f"Dispatcher: cannot load playbook '{playbook_id}' for mode '{mode_id}': {exc}"
            ) from exc

        # 4. Pick executor for this playbook
        executor = self._deps.executor_by_playbook.get(playbook_id)
        if executor is None:
            executor = LLMAgentExecutor(
                llm_client=self._deps.llm_client,
                label=playbook_id,
            )
            logger.info(
                "Dispatcher: no executor for '%s' — using LLMAgentExecutor",
                playbook_id,
            )

        # 5. Run the playbook
        runner = PlaybookRunner(executor=executor)
        run_result = await runner.run(
            playbook,
            active_mode=mode_id,
            initial_inputs={"query": request.message},
        )

        return DispatchResponse(
            session_id=request.session_id,
            resolved_mode=mode_id,
            playbook_id=playbook.id,
            complexity=complexity_level,
            complexity_reason=complexity_reason,
            run_result=run_result,
        )

    @staticmethod
    def _select_playbook(mode_config: Any) -> str:
        """Resolve the playbook id from a mode config.

        Supports both shapes used in the codebase: legacy ``ModeConfig``
        with ``playbooks_default`` and 021 ``ModeConfig`` with
        ``playbooks.default``.
        """
        # 021 shape: ``mode.playbooks_default`` or ``mode.playbooks.default``
        candidate = getattr(mode_config, "playbooks_default", None)
        if isinstance(candidate, str) and candidate:
            return candidate
        playbooks = getattr(mode_config, "playbooks", None)
        if playbooks is not None:
            default = getattr(playbooks, "default", None) or (
                playbooks.get("default") if isinstance(playbooks, dict) else None
            )
            if isinstance(default, str) and default:
                return default
        return "general"
