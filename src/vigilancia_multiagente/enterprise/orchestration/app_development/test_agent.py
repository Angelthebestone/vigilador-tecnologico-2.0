"""Test agent: executes tests in sandbox and generates checklist."""

from __future__ import annotations

from dataclasses import dataclass

from vigilancia_multiagente.enterprise.orchestration.app_development.errors import (
    SandboxExecutionError,
)
from vigilancia_multiagente.enterprise.orchestration.app_development.ports import (
    LLMPort,
    SandboxPort,
    TemplatePort,
)

MAX_RETRIES = 2


@dataclass(frozen=True)
class TestResult:
    """Output of the test phase."""

    document: str
    passed: bool
    output: str


class TestAgent:
    """Executes tests in sandbox and generates checklist.md."""

    __test__ = False  # Not a pytest test class

    def __init__(self, llm: LLMPort, sandbox: SandboxPort, template: TemplatePort) -> None:
        self._llm = llm
        self._sandbox = sandbox
        self._template = template

    async def run(self, tasks_doc: str, implement_output: str) -> TestResult:
        """Run tests in sandbox with up to MAX_RETRIES attempts.

        Each retry reports failure context before retrying (constitution #4).
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a test writer. Given tasks and implementation output, "
                    "produce pytest test code. Output only the code."
                ),
            },
            {
                "role": "user",
                "content": f"TASKS:\n{tasks_doc}\n\nIMPLEMENTATION:\n{implement_output}",
            },
        ]
        test_code = await self._llm.complete(messages)
        last_error = ""
        for attempt in range(1, MAX_RETRIES + 1):
            output = await self._sandbox.execute(test_code)
            if "FAILED" not in output.upper() and "ERROR" not in output.upper():
                document = self._template.render(
                    "checklist.template.md",
                    {
                        "project_name": "app-project",
                        "test_results": output,
                        "coverage": "N/A",
                        "pass_fail": "PASS",
                    },
                )
                return TestResult(document=document, passed=True, output=output)
            last_error = f"Attempt {attempt}/{MAX_RETRIES}: {output}"
        raise SandboxExecutionError("test", last_error, MAX_RETRIES)
