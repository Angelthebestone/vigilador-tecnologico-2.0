"""ComplexityClassifier — classifies a user query as SIMPLE / MODERATE / COMPLEX.

Spec 021 FR-017 / F4a.A T092. Uses one LLM call (~50 tokens prompt,
~10 tokens response) to drive playbook selection downstream.

Constitución:
* SRP: this module classifies; it does NOT pick playbooks (PlaybookRunner does).
* POLA: the classifier always logs the reason so an operator can see why a
  query was routed somewhere unexpected.
* #4 explicit errors: timeouts and unparseable LLM outputs propagate; no
  silent fallback to a default complexity.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol

from vigilancia_multiagente.enterprise.governance.audit_log import AuditLogPort

logger = logging.getLogger(__name__)


class ComplexityLevel(StrEnum):
    SIMPLE = "SIMPLE"
    MODERATE = "MODERATE"
    COMPLEX = "COMPLEX"


@dataclass(frozen=True)
class ComplexityDecision:
    level: ComplexityLevel
    reason: str
    raw_response: str


class _LLMClientProto(Protocol):
    async def complete(
        self, messages: list[Any], **kwargs: Any
    ) -> Any: ...


_PROMPT_TEMPLATE = (
    "Classify the following user query as SIMPLE, MODERATE, or COMPLEX. "
    "SIMPLE = single-fact lookup or cookie-cutter task. "
    "MODERATE = multi-step task touching 1-2 data sources. "
    "COMPLEX = open-ended research, decision, or multi-stage workflow. "
    "Respond with strict JSON: "
    '{"level": "<SIMPLE|MODERATE|COMPLEX>", "reason": "<one short sentence>"}.'
)

_DEFAULT_TIMEOUT_S = 8.0


class ClassifierError(RuntimeError):
    """Raised when the LLM classifier cannot return a valid decision."""


@dataclass
class ComplexityClassifier:
    """Single-call LLM classifier for the orchestration tier."""

    llm_client: _LLMClientProto
    timeout_s: float = _DEFAULT_TIMEOUT_S
    model_kwargs: dict[str, Any] | None = None
    audit_log: AuditLogPort | None = None

    async def classify(
        self, query: str, session_id: str | None = None
    ) -> ComplexityDecision:
        """Classify ``query`` with one LLM call and log the reason."""
        if not isinstance(query, str) or not query.strip():
            raise ValueError("ComplexityClassifier.classify: 'query' must be non-empty")

        messages: list[dict[str, str]] = [
            {"role": "system", "content": _PROMPT_TEMPLATE},
            {"role": "user", "content": query.strip()[:1_000]},
        ]

        t0 = time.perf_counter()
        try:
            response = await asyncio.wait_for(
                self.llm_client.complete(
                    messages=messages, **(self.model_kwargs or {})
                ),
                timeout=self.timeout_s,
            )
        except TimeoutError as exc:
            raise ClassifierError(
                f"ComplexityClassifier: LLM call exceeded {self.timeout_s}s"
            ) from exc

        raw = _extract_text(response)
        decision = _parse_decision(raw)
        latency_ms = (time.perf_counter() - t0) * 1000
        logger.info(
            "ComplexityClassifier: query=%r -> level=%s reason=%r",
            query[:80], decision.level.value, decision.reason,
        )
        if self.audit_log is not None:
            self.audit_log.log_complexity_decision(
                query_excerpt=query,
                level=decision.level.value,
                reason=decision.reason,
                latency_ms=latency_ms,
                session_id=session_id,
            )
        return decision


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_text(response: Any) -> str:
    """Best-effort extraction of the textual payload from various LLM client shapes."""
    if response is None:
        return ""
    if isinstance(response, str):
        return response
    # OpenAI-style dict shape
    if isinstance(response, dict):
        choices = response.get("choices")
        if isinstance(choices, list) and choices:
            first = choices[0]
            if isinstance(first, dict):
                msg = first.get("message", {})
                if isinstance(msg, dict) and isinstance(msg.get("content"), str):
                    return msg["content"]
        if isinstance(response.get("content"), str):
            return response["content"]
    # Object with `.content`
    content = getattr(response, "content", None)
    if isinstance(content, str):
        return content
    # Object with `.choices[0].message.content`
    choices_attr = getattr(response, "choices", None)
    if isinstance(choices_attr, list) and choices_attr:
        msg = getattr(choices_attr[0], "message", None)
        if msg is not None:
            content = getattr(msg, "content", None)
            if isinstance(content, str):
                return content
    return str(response)


_JSON_BLOCK_RE = re.compile(r"\{.*?\}", re.DOTALL)


def _parse_decision(raw: str) -> ComplexityDecision:
    """Parse the LLM's strict JSON response. Raise on malformed output."""
    if not raw or not raw.strip():
        raise ClassifierError("ComplexityClassifier: empty LLM response")
    match = _JSON_BLOCK_RE.search(raw)
    if not match:
        raise ClassifierError(
            f"ComplexityClassifier: response has no JSON block: {raw[:200]!r}"
        )
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise ClassifierError(
            f"ComplexityClassifier: invalid JSON in response: {raw[:200]!r}"
        ) from exc

    level_raw = payload.get("level") if isinstance(payload, dict) else None
    if not isinstance(level_raw, str):
        raise ClassifierError(
            f"ComplexityClassifier: response missing 'level' field: {payload!r}"
        )
    level_norm = level_raw.strip().upper()
    if level_norm not in ComplexityLevel.__members__:
        raise ClassifierError(
            f"ComplexityClassifier: unknown level {level_raw!r} "
            f"(expected SIMPLE | MODERATE | COMPLEX)"
        )
    reason = str(payload.get("reason", "")).strip() or "(no reason provided)"
    return ComplexityDecision(
        level=ComplexityLevel(level_norm),
        reason=reason,
        raw_response=raw.strip(),
    )
