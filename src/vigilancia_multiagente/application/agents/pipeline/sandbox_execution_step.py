from __future__ import annotations

from vigilancia_multiagente.application.agents.pipeline.base_step import PipelineStep
from vigilancia_multiagente.application.agents.pipeline.tool_loop_step import ToolLoopContext


class SandboxExecutionStep(PipelineStep[ToolLoopContext, ToolLoopContext]):
    """No-op placeholder: sandbox runs inside tool loop when tools request it."""

    async def execute(self, context: ToolLoopContext) -> ToolLoopContext:
        return context
