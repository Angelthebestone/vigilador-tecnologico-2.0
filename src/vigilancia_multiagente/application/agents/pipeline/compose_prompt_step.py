from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from vigilancia_multiagente.application.agents.pipeline.base_step import PipelineStep
from vigilancia_multiagente.application.governance.contract_loader import AgentSkillPolicy
from vigilancia_multiagente.application.governance.prompt_composer import (
    ComposedPrompt,
    PromptComposer,
)
from vigilancia_multiagente.application.governance.validators import PromptValidator
from vigilancia_multiagente.domain.models import BranchConfig, ResearchSession
from vigilancia_multiagente.domain.system_base import BranchOverlay, SystemBase


@dataclass(slots=True)
class ComposePromptContext:
    session: ResearchSession
    branch_config: BranchConfig
    policy: AgentSkillPolicy
    branch_overlay: BranchOverlay
    composed: ComposedPrompt | None = None


class ComposePromptStep(PipelineStep[ComposePromptContext, ComposePromptContext]):
    def __init__(
        self,
        prompt_composer: PromptComposer,
        system_base: SystemBase | None,
        validator: PromptValidator,
        cross_branch_hints: deque[str],
    ) -> None:
        self._prompt_composer = prompt_composer
        self._system_base = system_base
        self._validator = validator
        self._cross_branch_hints = cross_branch_hints

    async def execute(self, context: ComposePromptContext) -> ComposePromptContext:
        if self._system_base is not None:
            context.composed = self._prompt_composer.compose(
                system_base=self._system_base,
                overlay=context.branch_overlay,
                user_query=context.session.user_query,
                branch_config=context.branch_config,
                policy=context.policy,
                cross_branch_context=list(self._cross_branch_hints) or None,
            )
            self._validator.validate_composition(
                self._system_base, context.branch_overlay, context.session.user_query
            )
        return context
