# ROADMAP F5b - fuera de MVP 021; no registrar en runtime
"""Tasks agent: generates tasks.md with ordered task list."""

from __future__ import annotations

from dataclasses import dataclass

from vigilancia_multiagente.enterprise.orchestration.app_development.ports import (
    LLMPort,
    TemplatePort,
)


@dataclass(frozen=True)
class TasksResult:
    """Output of the tasks phase."""

    document: str


class TasksAgent:
    """Generates tasks.md from plan document via LLM."""

    def __init__(self, llm: LLMPort, template: TemplatePort) -> None:
        self._llm = llm
        self._template = template

    async def run(self, plan_doc: str) -> TasksResult:
        """Generate tasks document with ordered task list and dependencies."""
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a task decomposer. Given a plan, produce: "
                    "1) TASKS_LIST (ordered), 2) DEPENDENCIES between tasks. "
                    "Format:\nTASKS_LIST: ...\nDEPENDENCIES: ..."
                ),
            },
            {"role": "user", "content": plan_doc},
        ]
        response = await self._llm.complete(messages)
        parsed = _parse_tasks_response(response)
        document = self._template.render(
            "tasks.template.md",
            {
                "project_name": "app-project",
                "tasks_list": parsed["tasks_list"],
                "dependencies": parsed["dependencies"],
            },
        )
        return TasksResult(document=document)


def _parse_tasks_response(response: str) -> dict[str, str]:
    """Parse structured LLM response for tasks fields."""
    result: dict[str, str] = {"tasks_list": "", "dependencies": ""}
    for line in response.splitlines():
        upper_line = line.strip().upper()
        if upper_line.startswith("TASKS_LIST:"):
            result["tasks_list"] = line.split(":", 1)[1].strip()
        elif upper_line.startswith("DEPENDENCIES:"):
            result["dependencies"] = line.split(":", 1)[1].strip()
    return result
