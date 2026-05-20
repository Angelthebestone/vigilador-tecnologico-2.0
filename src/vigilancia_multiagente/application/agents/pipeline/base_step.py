from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

TIn = TypeVar("TIn")
TOut = TypeVar("TOut")


class PipelineStep(ABC, Generic[TIn, TOut]):
    @abstractmethod
    async def execute(self, context: TIn) -> TOut: ...
