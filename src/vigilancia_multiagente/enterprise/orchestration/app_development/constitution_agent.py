"""Constitution agent: defines stack, constraints, and target directory."""

from __future__ import annotations

from dataclasses import dataclass

from vigilancia_multiagente.enterprise.orchestration.app_development.ports import (
    LLMPort,
    TemplatePort,
)


@dataclass(frozen=True)
class ConstitutionResult:
    """Output of the constitution phase."""

    document: str
    stack: str
    constraints: str
    target_directory: str


class ConstitutionAgent:
    """Generates constitution.md from user requirements via LLM."""

    def __init__(self, llm: LLMPort, template: TemplatePort) -> None:
        self._llm = llm
        self._template = template

    async def run(self, user_requirements: str) -> ConstitutionResult:
        """Generate constitution document from user requirements.

        Uses LLM to extract stack, constraints, and target directory,
        then renders the constitution template.
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a constitution agent. Extract from the user requirements: "
                    "1) stack (technologies), 2) constraints, 3) target_directory (absolute path). "
                    "Respond in format:\nSTACK: ...\nCONSTRAINTS: ...\nTARGET_DIRECTORY: ..."
                ),
            },
            {"role": "user", "content": user_requirements},
        ]
        response = await self._llm.complete(messages)
        parsed = _parse_llm_response(response)
        document = self._template.render(
            "constitution.template.md",
            {
                "project_name": "app-project",
                "stack": parsed["stack"],
                "constraints": parsed["constraints"],
                "target_directory": parsed["target_directory"],
                "user_requirements": user_requirements,
            },
        )
        return ConstitutionResult(
            document=document,
            stack=parsed["stack"],
            constraints=parsed["constraints"],
            target_directory=parsed["target_directory"],
        )


def _parse_llm_response(response: str) -> dict[str, str]:
    """Parse structured LLM response into fields."""
    result: dict[str, str] = {"stack": "", "constraints": "", "target_directory": ""}
    for line in response.splitlines():
        upper_line = line.strip().upper()
        if upper_line.startswith("STACK:"):
            result["stack"] = line.split(":", 1)[1].strip()
        elif upper_line.startswith("CONSTRAINTS:"):
            result["constraints"] = line.split(":", 1)[1].strip()
        elif upper_line.startswith("TARGET_DIRECTORY:"):
            result["target_directory"] = line.split(":", 1)[1].strip()
    return result
