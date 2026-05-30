"""Plan agent: generates plan.md with architecture and dependencies."""

from __future__ import annotations

from dataclasses import dataclass

from vigilancia_multiagente.enterprise.orchestration.app_development.ports import (
    LLMPort,
    TemplatePort,
)


@dataclass(frozen=True)
class PlanResult:
    """Output of the plan phase."""

    document: str


class PlanAgent:
    """Generates plan.md from constitution + spec via LLM."""

    def __init__(self, llm: LLMPort, template: TemplatePort) -> None:
        self._llm = llm
        self._template = template

    async def run(self, constitution_doc: str, spec_doc: str) -> PlanResult:
        """Generate plan document with architecture and dependencies."""
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an architect. Given constitution and spec, produce: "
                    "1) ARCHITECTURE, 2) DEPENDENCIES, 3) PHASES. "
                    "Format:\nARCHITECTURE: ...\nDEPENDENCIES: ...\nPHASES: ..."
                ),
            },
            {"role": "user", "content": f"CONSTITUTION:\n{constitution_doc}\n\nSPEC:\n{spec_doc}"},
        ]
        response = await self._llm.complete(messages)
        parsed = _parse_plan_response(response)
        document = self._template.render(
            "plan.template.md",
            {
                "project_name": "app-project",
                "architecture": parsed["architecture"],
                "dependencies": parsed["dependencies"],
                "phases": parsed["phases"],
            },
        )
        return PlanResult(document=document)


def _parse_plan_response(response: str) -> dict[str, str]:
    """Parse structured LLM response for plan fields."""
    result: dict[str, str] = {"architecture": "", "dependencies": "", "phases": ""}
    for line in response.splitlines():
        upper_line = line.strip().upper()
        if upper_line.startswith("ARCHITECTURE:"):
            result["architecture"] = line.split(":", 1)[1].strip()
        elif upper_line.startswith("DEPENDENCIES:"):
            result["dependencies"] = line.split(":", 1)[1].strip()
        elif upper_line.startswith("PHASES:"):
            result["phases"] = line.split(":", 1)[1].strip()
    return result
