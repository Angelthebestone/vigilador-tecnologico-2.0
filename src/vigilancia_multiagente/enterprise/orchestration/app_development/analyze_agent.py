"""Analyze agent: verifies coherence between phase documents."""

from __future__ import annotations

from dataclasses import dataclass

from vigilancia_multiagente.enterprise.orchestration.app_development.errors import (
    InconsistencyBlockError,
)
from vigilancia_multiagente.enterprise.orchestration.app_development.ports import (
    LLMPort,
    TemplatePort,
)


@dataclass(frozen=True)
class AnalyzeResult:
    """Output of the analyze phase."""

    document: str
    has_inconsistencies: bool
    inconsistencies: list[str]


class AnalyzeAgent:
    """Verifies coherence between constitution/spec/plan/tasks documents."""

    def __init__(self, llm: LLMPort, template: TemplatePort) -> None:
        self._llm = llm
        self._template = template

    async def run(
        self,
        constitution_doc: str,
        spec_doc: str,
        plan_doc: str,
        tasks_doc: str,
    ) -> AnalyzeResult:
        """Analyze documents for inconsistencies.

        Raises InconsistencyBlockError if critical inconsistencies found.
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a coherence verifier. Check consistency between the "
                    "constitution, spec, plan, and tasks documents. "
                    "If inconsistencies exist, list them prefixed with 'INCONSISTENCY:'. "
                    "If none, respond with 'STATUS: sin issues'."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"CONSTITUTION:\n{constitution_doc}\n\n"
                    f"SPEC:\n{spec_doc}\n\n"
                    f"PLAN:\n{plan_doc}\n\n"
                    f"TASKS:\n{tasks_doc}"
                ),
            },
        ]
        response = await self._llm.complete(messages)
        inconsistencies = _extract_inconsistencies(response)
        has_issues = len(inconsistencies) > 0
        status = "inconsistencies found" if has_issues else "sin issues"
        recommendations = response if has_issues else "No action needed."
        document = self._template.render(
            "analyze-report.template.md",
            {
                "project_name": "app-project",
                "status": status,
                "inconsistencies": "\n".join(inconsistencies) if inconsistencies else "None",
                "recommendations": recommendations,
            },
        )
        result = AnalyzeResult(
            document=document,
            has_inconsistencies=has_issues,
            inconsistencies=inconsistencies,
        )
        if has_issues:
            raise InconsistencyBlockError(inconsistencies)
        return result


def _extract_inconsistencies(response: str) -> list[str]:
    """Extract inconsistency lines from LLM response."""
    items: list[str] = []
    for line in response.splitlines():
        stripped = line.strip()
        if stripped.upper().startswith("INCONSISTENCY:"):
            items.append(stripped.split(":", 1)[1].strip())
    return items
