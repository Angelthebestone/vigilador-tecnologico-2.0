from __future__ import annotations

from typing import Generic, TypeVar

from vigilancia_multiagente.application.agents.pipeline.base_step import PipelineStep

TIn = TypeVar("TIn")
TOut = TypeVar("TOut")


class Pipeline(Generic[TIn, TOut]):
    def __init__(self, steps: list[PipelineStep[object, object]]) -> None:
        self._steps = steps

    async def run(self, context: TIn) -> TOut:
        current: object = context
        for step in self._steps:
            current = await step.execute(current)
        return current  # type: ignore[return-value]
