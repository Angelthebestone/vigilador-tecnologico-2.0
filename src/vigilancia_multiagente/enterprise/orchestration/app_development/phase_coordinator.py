"""Phase coordinator: orchestrates the app-development pipeline."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from vigilancia_multiagente.enterprise.orchestration.app_development.analyze_agent import (
    AnalyzeAgent,
    AnalyzeResult,
)
from vigilancia_multiagente.enterprise.orchestration.app_development.complexity_router import (
    resolve_phases,
)
from vigilancia_multiagente.enterprise.orchestration.app_development.constitution_agent import (
    ConstitutionAgent,
)
from vigilancia_multiagente.enterprise.orchestration.app_development.errors import (
    ApprovalDeniedError,
    DirectoryNotWritableError,
    GuardrailViolationError,
    InconsistencyBlockError,
)
from vigilancia_multiagente.enterprise.orchestration.app_development.implement_agent import (
    ImplementAgent,
)
from vigilancia_multiagente.enterprise.orchestration.app_development.plan_agent import PlanAgent
from vigilancia_multiagente.enterprise.orchestration.app_development.ports import (
    ApprovalPort,
    AuditPort,
    FileSystemPort,
    LLMPort,
    SandboxPort,
    TemplatePort,
)
from vigilancia_multiagente.enterprise.orchestration.app_development.specify_agent import (
    SpecifyAgent,
)
from vigilancia_multiagente.enterprise.orchestration.app_development.tasks_agent import TasksAgent
from vigilancia_multiagente.enterprise.orchestration.app_development.test_agent import TestAgent

APPROVAL_GATES: frozenset[str] = frozenset({"constitution", "analyze"})
DEFAULT_MAX_LLM_CALLS = 500
DEFAULT_MAX_DURATION_SECONDS = 86400


@dataclass
class PipelineState:
    """Mutable state of the pipeline execution."""

    completed_phases: list[str] = field(default_factory=list)
    documents: dict[str, str] = field(default_factory=dict)
    llm_calls: int = 0
    start_time: float = field(default_factory=time.time)


class PhaseCoordinator:
    """Orchestrates the sequential app-development pipeline.

    Loads phases from complexity routing, executes agents in order,
    enforces approval gates and guardrails.
    """

    def __init__(
        self,
        llm: LLMPort,
        template: TemplatePort,
        sandbox: SandboxPort,
        approval: ApprovalPort,
        audit: AuditPort,
        file_system: FileSystemPort,
        max_llm_calls: int = DEFAULT_MAX_LLM_CALLS,
        max_duration_seconds: int = DEFAULT_MAX_DURATION_SECONDS,
    ) -> None:
        self._llm = llm
        self._template = template
        self._sandbox = sandbox
        self._approval = approval
        self._audit = audit
        self._fs = file_system
        self._max_llm_calls = max_llm_calls
        self._max_duration = max_duration_seconds

    async def run(self, complexity: str, user_requirements: str) -> PipelineState:
        """Execute the full pipeline for the given complexity.

        Returns the final PipelineState with all documents.
        Raises on guardrail violations, approval denials, or errors.
        """
        phases = resolve_phases(complexity)
        state = PipelineState()
        for phase in phases:
            self._check_guardrails(state)
            await self._execute_phase(phase, state, user_requirements)
            state.completed_phases.append(phase)
            await self._audit.record(
                triggered_by="app_development_phase",
                target_file=f"app-project/{phase}.md",
                phase=phase,
            )
            if phase in APPROVAL_GATES:
                approved = await self._approval.request_approval(
                    phase, state.documents.get(phase, "")
                )
                if not approved:
                    raise ApprovalDeniedError(phase)
        return state

    async def _execute_phase(
        self, phase: str, state: PipelineState, user_requirements: str
    ) -> None:
        """Dispatch to the appropriate agent for the phase."""
        if phase == "constitution":
            await self._run_constitution(state, user_requirements)
        elif phase == "specify":
            await self._run_specify(state)
        elif phase == "plan":
            await self._run_plan(state)
        elif phase == "tasks":
            await self._run_tasks(state)
        elif phase == "analyze":
            await self._run_analyze(state)
        elif phase == "implement":
            await self._run_implement(state)
        elif phase == "test":
            await self._run_test(state)
        state.llm_calls += 1

    async def _run_constitution(self, state: PipelineState, user_requirements: str) -> None:
        agent = ConstitutionAgent(self._llm, self._template)
        result = await agent.run(user_requirements)
        state.documents["constitution"] = result.document

    async def _run_specify(self, state: PipelineState) -> None:
        agent = SpecifyAgent(self._llm, self._template)
        result = await agent.run(state.documents["constitution"])
        state.documents["specify"] = result.document

    async def _run_plan(self, state: PipelineState) -> None:
        agent = PlanAgent(self._llm, self._template)
        result = await agent.run(state.documents["constitution"], state.documents["specify"])
        state.documents["plan"] = result.document

    async def _run_tasks(self, state: PipelineState) -> None:
        agent = TasksAgent(self._llm, self._template)
        result = await agent.run(state.documents["plan"])
        state.documents["tasks"] = result.document

    async def _run_analyze(self, state: PipelineState) -> None:
        agent = AnalyzeAgent(self._llm, self._template)
        result: AnalyzeResult
        try:
            result = await agent.run(
                state.documents["constitution"],
                state.documents["specify"],
                state.documents["plan"],
                state.documents["tasks"],
            )
        except InconsistencyBlockError:
            raise
        state.documents["analyze"] = result.document

    async def _run_implement(self, state: PipelineState) -> None:
        agent = ImplementAgent(self._llm, self._sandbox)
        result = await agent.run(state.documents["tasks"], state.documents["constitution"])
        state.documents["implement"] = result.sandbox_output

    async def _run_test(self, state: PipelineState) -> None:
        agent = TestAgent(self._llm, self._sandbox, self._template)
        result = await agent.run(state.documents["tasks"], state.documents.get("implement", ""))
        state.documents["test"] = result.document

    def _check_guardrails(self, state: PipelineState) -> None:
        """Enforce guardrail limits. Raises GuardrailViolationError on breach."""
        if state.llm_calls >= self._max_llm_calls:
            raise GuardrailViolationError(
                "max_total_llm_calls", state.llm_calls, self._max_llm_calls
            )
        elapsed = int(time.time() - state.start_time)
        if elapsed >= self._max_duration:
            raise GuardrailViolationError(
                "max_session_duration_seconds", elapsed, self._max_duration
            )

    async def copy_final(self, state: PipelineState, target_directory: str) -> None:
        """Copy final artifacts to target directory after approval.

        Raises DirectoryNotWritableError if target is not accessible.
        """
        exists = await self._fs.path_exists(target_directory)
        if not exists:
            raise DirectoryNotWritableError(target_directory)
        for phase_name, content in state.documents.items():
            path = f"{target_directory}/{phase_name}.md"
            await self._fs.write_file(path, content)
