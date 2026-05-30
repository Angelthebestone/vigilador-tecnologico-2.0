"""Implement agent: generates code in sandbox from tasks."""

from __future__ import annotations

from dataclasses import dataclass

from vigilancia_multiagente.enterprise.orchestration.app_development.errors import (
    SandboxExecutionError,
)
from vigilancia_multiagente.enterprise.orchestration.app_development.ports import (
    LLMPort,
    SandboxPort,
)

MAX_RETRIES = 2


@dataclass(frozen=True)
class ImplementResult:
    """Output of the implement phase."""

    files_generated: list[str]
    sandbox_output: str


class ImplementAgent:
    """Generates code in sandbox by iterating tasks."""

    def __init__(self, llm: LLMPort, sandbox: SandboxPort) -> None:
        self._llm = llm
        self._sandbox = sandbox

    async def run(self, tasks_doc: str, constitution_doc: str) -> ImplementResult:
        """Generate code for each task in the sandbox.

        Retries up to MAX_RETRIES on sandbox failure.
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a code generator. Given tasks and constitution, "
                    "produce Python code that implements all tasks. "
                    "Output only the code, no explanations."
                ),
            },
            {
                "role": "user",
                "content": f"TASKS:\n{tasks_doc}\n\nCONSTITUTION:\n{constitution_doc}",
            },
        ]
        code = await self._llm.complete(messages)
        last_error = ""
        for _attempt in range(1, MAX_RETRIES + 1):
            sandbox_output = await self._sandbox.execute(code)
            if "ERROR" not in sandbox_output.upper():
                return ImplementResult(
                    files_generated=["main.py"],
                    sandbox_output=sandbox_output,
                )
            last_error = sandbox_output
        raise SandboxExecutionError("implement", last_error, MAX_RETRIES)
