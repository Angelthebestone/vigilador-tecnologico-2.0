"""LlmFalsificationProber — spec 007 T026 (WS-E, FR-E03).

Formula escenarios hipoteticos de evidencia que tumbarian una conclusion.
Si el LLM no genera ningun escenario plausible, la conclusion se marca
como no-falsable (warning del gate).

Fallo del LLM -> StepError(severity=warning) y lista vacia.
"""

from __future__ import annotations

import json
import logging
import re
from typing import cast
from uuid import UUID, uuid4

from vigilancia_multiagente.domain.evaluation_entities import FalsificationScenario
from vigilancia_multiagente.domain.pipeline_errors import (
    StepError,
    StepErrorSeverity,
    Workstream,
)
from vigilancia_multiagente.application.evaluation.prompt_messages import (
    build_messages_with_fewshot,
)
from vigilancia_multiagente.domain.ports.llm_client import LLMClient
from vigilancia_multiagente.domain.ports.prompt_loader import PromptLoader

logger = logging.getLogger(__name__)

_JSON_BLOCK_RE = re.compile(r"\[\s*\{.*?\}\s*\]", re.DOTALL)


class LlmFalsificationProber:
    def __init__(
        self,
        llm: LLMClient,
        prompt_loader: PromptLoader,
        errors_sink: list[StepError] | None = None,
    ) -> None:
        self._llm = llm
        self._prompt_loader = prompt_loader
        self._errors = errors_sink

    async def probe(self, conclusion: str) -> list[FalsificationScenario]:
        try:
            messages = build_messages_with_fewshot(
                prompt_loader=self._prompt_loader,
                base_path="evaluation/falsification.txt",
                user_content=conclusion,
            )
        except FileNotFoundError as exc:
            self._record_error(exc, context={"prompt": "evaluation/falsification.txt"})
            return []
        try:
            response = await self._llm.complete(messages)
        except Exception as exc:  # noqa: BLE001 — adapter de frontera externa
            logger.warning("LlmFalsificationProber failed: %s", exc, exc_info=True)
            self._record_error(exc, context={"conclusion_excerpt": conclusion[:120]})
            return []

        content = str(getattr(response, "content", "") or "")
        scenarios_data = _extract_scenarios(content)
        conclusion_id = uuid4()
        scenarios: list[FalsificationScenario] = []
        for item in scenarios_data:
            evidence = str(item.get("hypothetical_evidence") or item.get("evidence") or "").strip()
            if not evidence:
                continue
            try:
                plausibility = float(cast(float, item.get("plausibility", 0.5)))
            except (TypeError, ValueError):
                plausibility = 0.5
            scenarios.append(
                FalsificationScenario(
                    conclusion_id=conclusion_id,
                    hypothetical_evidence=evidence,
                    plausibility=max(0.0, min(1.0, plausibility)),
                    falsifiable=True,
                )
            )
        return scenarios

    def _record_error(
        self, exc: BaseException, *, context: dict[str, object] | None = None
    ) -> None:
        if self._errors is None:
            return
        self._errors.append(
            StepError(
                workstream=Workstream.WS_E,
                step_name="LlmFalsificationProber.probe",
                reason=str(exc) or exc.__class__.__name__,
                exception_type=exc.__class__.__name__,
                context=dict(context) if context else {},
                severity=StepErrorSeverity.WARNING,
            )
        )


def _extract_scenarios(text: str) -> list[dict[str, object]]:
    """Tolera respuestas con JSON puro o con prefacio narrativo + JSON."""
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
            return []
    return []
