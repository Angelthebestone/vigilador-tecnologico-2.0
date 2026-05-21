"""LlmConflictOfInterestAnalyzer — spec 007 T055.

Analiza metadatos de fuente para detectar conflictos de interes mediante
prompts LLM dirigidos. Parse menciones de financiadores y estima
proporcion de financiamiento corporativo vs academico.
"""

from __future__ import annotations

import json
import logging
import re
from typing import cast

from vigilancia_multiagente.domain.evaluation_entities import (
    ConflictOfInterest,
    FunderType,
    RiskLevel,
)
from vigilancia_multiagente.domain.models import SourceRef
from vigilancia_multiagente.domain.pipeline_errors import (
    StepError,
    StepErrorSeverity,
    Workstream,
)
from vigilancia_multiagente.domain.ports.llm_client import LLMClient
from vigilancia_multiagente.domain.system_base import MiniMaxMessage

logger = logging.getLogger(__name__)

_JSON_BLOCK_RE = re.compile(r"\{.*?\}", re.DOTALL)

_PROMPT_TEMPLATE = """You are analyzing metadata for conflicts of interest.
Given the following source information, identify funders and classify them.

Source title: {title}
Source URL: {url}
Provider: {provider}

Return a JSON object with:
- "funder_entity": the name of the funding entity found, or "unknown"
- "funder_type": "corporate", "academic", "government", or "unknown"
- "corporate_ratio": a float between 0 and 1 estimating corporate vs total funding

Return ONLY the JSON object with no commentary."""


class LlmConflictOfInterestAnalyzer:
    def __init__(
        self,
        llm: LLMClient,
        errors_sink: list[StepError] | None = None,
    ) -> None:
        self._llm = llm
        self._errors = errors_sink

    async def analyze(self, source: SourceRef) -> ConflictOfInterest | None:
        prompt = _PROMPT_TEMPLATE.format(
            title=source.title or "",
            url=source.url,
            provider=source.provider,
        )
        messages = [
            MiniMaxMessage(role="system", content="You are a financial conflict-of-interest analyst."),
            MiniMaxMessage(role="user", content=prompt),
        ]
        try:
            response = await self._llm.complete(messages)
        except Exception as exc:
            logger.warning("LlmConflictOfInterestAnalyzer failed: %s", exc, exc_info=True)
            self._record_error(exc, context={"source_id": str(source.id)})
            return ConflictOfInterest(
                source_id=source.id,
                funder_entity="unknown",
                funder_type=FunderType.UNKNOWN,
                corporate_ratio=0.0,
                risk_level=RiskLevel.LOW,
            )

        content = str(getattr(response, "content", "") or "")
        data = _extract_json(content)
        if data is None:
            return ConflictOfInterest(
                source_id=source.id,
                funder_entity="unknown",
                funder_type=FunderType.UNKNOWN,
                corporate_ratio=0.0,
                risk_level=RiskLevel.LOW,
            )
        return _parse_conflict(source.id, data)

    def _record_error(
        self, exc: BaseException, *, context: dict[str, object] | None = None
    ) -> None:
        if self._errors is None:
            return
        self._errors.append(
            StepError(
                workstream=Workstream.WS_A,
                step_name="LlmConflictOfInterestAnalyzer.analyze",
                reason=str(exc) or exc.__class__.__name__,
                exception_type=exc.__class__.__name__,
                context=dict(context) if context else {},
                severity=StepErrorSeverity.WARNING,
            )
        )


def _extract_json(text: str) -> dict[str, object] | None:
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    match = _JSON_BLOCK_RE.search(text)
    if match:
        try:
            parsed = json.loads(match.group(0))
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return None
    return None


def _parse_conflict(source_id, data: dict[str, object]) -> ConflictOfInterest:
    funder_entity = str(data.get("funder_entity", "unknown"))
    try:
        funder_type = FunderType(str(data.get("funder_type", "unknown")))
    except ValueError:
        funder_type = FunderType.UNKNOWN
    try:
        corporate_ratio = max(0.0, min(1.0, float(cast(float, data.get("corporate_ratio", 0.0)))))
    except (TypeError, ValueError):
        corporate_ratio = 0.0
    if corporate_ratio >= 0.7:
        risk_level = RiskLevel.HIGH
    elif corporate_ratio >= 0.4:
        risk_level = RiskLevel.MEDIUM
    else:
        risk_level = RiskLevel.LOW
    return ConflictOfInterest(
        source_id=source_id,
        funder_entity=funder_entity,
        funder_type=funder_type,
        corporate_ratio=corporate_ratio,
        risk_level=risk_level,
    )
