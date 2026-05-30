"""Specify agent: generates spec.md with functional requirements."""

from __future__ import annotations

from dataclasses import dataclass

from vigilancia_multiagente.enterprise.orchestration.app_development.ports import (
    LLMPort,
    TemplatePort,
)


@dataclass(frozen=True)
class SpecifyResult:
    """Output of the specify phase."""

    document: str


class SpecifyAgent:
    """Generates spec.md from constitution document via LLM."""

    def __init__(self, llm: LLMPort, template: TemplatePort) -> None:
        self._llm = llm
        self._template = template

    async def run(self, constitution_doc: str) -> SpecifyResult:
        """Generate spec document from constitution.

        Extracts functional requirements and success criteria.
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a spec writer. Given a constitution document, produce: "
                    "1) FUNCTIONAL_REQUIREMENTS, 2) SUCCESS_CRITERIA, 3) SCOPE. "
                    "Format:\nFUNCTIONAL_REQUIREMENTS: ...\nSUCCESS_CRITERIA: ...\nSCOPE: ..."
                ),
            },
            {"role": "user", "content": constitution_doc},
        ]
        response = await self._llm.complete(messages)
        parsed = _parse_spec_response(response)
        document = self._template.render(
            "spec.template.md",
            {
                "project_name": "app-project",
                "functional_requirements": parsed["functional_requirements"],
                "success_criteria": parsed["success_criteria"],
                "scope": parsed["scope"],
            },
        )
        return SpecifyResult(document=document)


def _parse_spec_response(response: str) -> dict[str, str]:
    """Parse structured LLM response for spec fields."""
    result: dict[str, str] = {
        "functional_requirements": "",
        "success_criteria": "",
        "scope": "",
    }
    for line in response.splitlines():
        upper_line = line.strip().upper()
        if upper_line.startswith("FUNCTIONAL_REQUIREMENTS:"):
            result["functional_requirements"] = line.split(":", 1)[1].strip()
        elif upper_line.startswith("SUCCESS_CRITERIA:"):
            result["success_criteria"] = line.split(":", 1)[1].strip()
        elif upper_line.startswith("SCOPE:"):
            result["scope"] = line.split(":", 1)[1].strip()
    return result
