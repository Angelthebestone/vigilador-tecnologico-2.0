"""LlmAssumptionDetector — spec 007 T095 (WS-C, FR-C01).

Detecta asunciones implicitas en textos fuente via LLM con prompt
en prompts/evaluation/assumption_detection.txt.

Fallo del LLM -> StepError(severity=warning) y lista vacia.
"""

from __future__ import annotations

import json
import logging
import re
from typing import cast

from vigilancia_multiagente.application.evaluation.prompt_messages import (
    build_messages_with_fewshot,
)
from vigilancia_multiagente.domain.evaluation_entities import (
    AssumptionSeverity,
    ImplicitAssumption,
)
from vigilancia_multiagente.domain.models import Finding
from vigilancia_multiagente.domain.pipeline_errors import (
    StepError,
    StepErrorSeverity,
    Workstream,
)
from vigilancia_multiagente.domain.ports.assumption_detector import AssumptionDetector
from vigilancia_multiagente.domain.ports.llm_client import LLMClient
from vigilancia_multiagente.domain.ports.prompt_loader import PromptLoader

logger = logging.getLogger(__name__)

_JSON_BLOCK_RE = re.compile(r"\[.*?\]", re.DOTALL)


class LlmAssumptionDetector(AssumptionDetector):
    """Adapter LLM. Fallo -> StepError + lista vacia."""

    def __init__(
        self,
        llm: LLMClient,
        prompt_loader: PromptLoader,
        errors_sink: list[StepError] | None = None,
    ) -> None:
        self._llm = llm
        self._prompt_loader = prompt_loader
        self._errors = errors_sink

    async def detect(
        self,
        finding: Finding,
        source_text: str,
    ) -> list[ImplicitAssumption]:
        try:
            messages = build_messages_with_fewshot(
                prompt_loader=self._prompt_loader,
                base_path="evaluation/assumption_detection.txt",
                user_content=(f"Finding: {finding.statement}\nSource: {source_text[:2000]}"),
            )
        except FileNotFoundError as exc:
            self._record_error(exc, context={"prompt": "evaluation/assumption_detection.txt"})
            return []
        try:
            response = await self._llm.complete(messages)
        except Exception as exc:
            logger.warning("LlmAssumptionDetector failed: %s", exc, exc_info=True)
            self._record_error(exc, context={"finding_id": str(finding.id)})
            return []

        content = str(getattr(response, "content", "") or "")
        items = _extract_assumptions(content)
        finding_id = finding.id
        assumptions: list[ImplicitAssumption] = []
        for item in items:
            text = str(item.get("text") or item.get("assumption") or "").strip()
            if not text:
                continue
            try:
                raw = str(item.get("severity", "info")).lower()
                severity = AssumptionSeverity(raw)
            except ValueError:
                severity = AssumptionSeverity.INFO
            try:
                affects = float(cast(float, item.get("affects_confidence", 0.0)))
            except (TypeError, ValueError):
                affects = 0.0
            assumptions.append(
                ImplicitAssumption(
                    finding_id=finding_id,
                    text=text,
                    severity=severity,
                    affects_confidence=max(-1.0, min(0.0, affects)),
                )
            )
        return assumptions

    def _record_error(
        self, exc: BaseException, *, context: dict[str, object] | None = None
    ) -> None:
        if self._errors is None:
            return
        self._errors.append(
            StepError(
                workstream=Workstream.WS_C,
                step_name="LlmAssumptionDetector.detect",
                reason=str(exc) or exc.__class__.__name__,
                exception_type=exc.__class__.__name__,
                context=dict(context) if context else {},
                severity=StepErrorSeverity.WARNING,
            )
        )


def _extract_assumptions(text: str) -> list[dict[str, object]]:
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
