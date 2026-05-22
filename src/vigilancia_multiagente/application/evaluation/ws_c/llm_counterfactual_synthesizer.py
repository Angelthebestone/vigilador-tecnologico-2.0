"""LlmCounterfactualSynthesizer — spec 007 T097 (WS-C, FR-C04).

Genera escenarios contrafactuales via LLM usando prompt
en prompts/evaluation/counterfactual.txt.

Fallo del LLM -> StepError(severity=warning) y lista vacia.
"""

from __future__ import annotations

import json
import logging
import re
from typing import cast
from uuid import uuid4

from vigilancia_multiagente.domain.evaluation_entities import CounterfactualScenario
from vigilancia_multiagente.domain.models import FinalReport
from vigilancia_multiagente.domain.pipeline_errors import (
    StepError,
    StepErrorSeverity,
    Workstream,
)
from vigilancia_multiagente.application.evaluation.prompt_messages import (
    build_messages_with_fewshot,
)
from vigilancia_multiagente.domain.ports.counterfactual import CounterfactualSynthesizer
from vigilancia_multiagente.domain.ports.llm_client import LLMClient
from vigilancia_multiagente.domain.ports.prompt_loader import PromptLoader

logger = logging.getLogger(__name__)

_JSON_BLOCK_RE = re.compile(r"\[.*?\]", re.DOTALL)


class LlmCounterfactualSynthesizer(CounterfactualSynthesizer):
    """Adapter LLM con scenarios_n configurable (default 3)."""

    def __init__(
        self,
        llm: LLMClient,
        prompt_loader: PromptLoader,
        errors_sink: list[StepError] | None = None,
        scenarios_n: int = 3,
    ) -> None:
        self._llm = llm
        self._prompt_loader = prompt_loader
        self._errors = errors_sink
        self._scenarios_n = scenarios_n

    async def synthesize(
        self,
        report_draft: FinalReport,
        scenarios_n: int | None = None,
    ) -> list[CounterfactualScenario]:
        n = scenarios_n if scenarios_n is not None else self._scenarios_n

        summary = (
            report_draft.executive_summary
            or report_draft.markdown
            or report_draft.technical_section
        )[:3000]

        user_content = (
            f"Generate exactly {n} counterfactual scenarios for the following report.\n\n"
            f"Report:\n{summary}\n\n"
            f"Respond ONLY with a JSON array of {n} objects, each with:\n"
            f'- "question": str (e.g. "What would happen if..."),\n'
            f'- "probability": float [0, 1],\n'
            f'- "impact_summary": str\n'
        )

        try:
            messages = build_messages_with_fewshot(
                prompt_loader=self._prompt_loader,
                base_path="evaluation/counterfactual.txt",
                user_content=user_content,
            )
        except FileNotFoundError as exc:
            self._record_error(exc, context={"prompt": "evaluation/counterfactual.txt"})
            return []
        try:
            response = await self._llm.complete(messages)
        except Exception as exc:
            logger.warning("LlmCounterfactualSynthesizer failed: %s", exc, exc_info=True)
            self._record_error(exc, context={"report_id": str(report_draft.session_id)})
            return []

        content = str(getattr(response, "content", "") or "")
        items = _extract_scenarios(content)
        scenarios: list[CounterfactualScenario] = []
        for item in items:
            question = str(item.get("question", "")).strip()
            if not question:
                continue
            try:
                probability = float(cast(float, item.get("probability", 0.5)))
            except (TypeError, ValueError):
                probability = 0.5
            impact = str(item.get("impact_summary", "")).strip()
            scenarios.append(
                CounterfactualScenario(
                    id=uuid4(),
                    question=question,
                    probability=max(0.0, min(1.0, probability)),
                    impact_summary=impact,
                )
            )
        return scenarios[:n]

    def _record_error(
        self, exc: BaseException, *, context: dict[str, object] | None = None
    ) -> None:
        if self._errors is None:
            return
        self._errors.append(
            StepError(
                workstream=Workstream.WS_C,
                step_name="LlmCounterfactualSynthesizer.synthesize",
                reason=str(exc) or exc.__class__.__name__,
                exception_type=exc.__class__.__name__,
                context=dict(context) if context else {},
                severity=StepErrorSeverity.WARNING,
            )
        )


def _extract_scenarios(text: str) -> list[dict[str, object]]:
    candidate = text.strip()
    try:
        parsed = json.loads(candidate)
        if isinstance(parsed, list):
            return [item for item in parsed if isinstance(item, dict)]
    except json.JSONDecodeError:
        pass
    match = _JSON_BLOCK_RE.search(text)
    if match:
        try:
            parsed = json.loads(match.group(0))
            if isinstance(parsed, list):
                return [item for item in parsed if isinstance(item, dict)]
        except json.JSONDecodeError:
            pass
    return []
