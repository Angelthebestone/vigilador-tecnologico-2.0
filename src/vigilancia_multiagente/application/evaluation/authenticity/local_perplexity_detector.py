"""LocalPerplexityAuthenticityDetector — spec 007 T075.

Combina perplejidad/burstiness (LLM log-prob) + heuristicas boilerplate.
Devuelve ContentAuthenticitySignal con ai_probability y effective_freshness.
"""

from __future__ import annotations

import logging
import math
import re
from uuid import UUID

from vigilancia_multiagente.domain.evaluation_entities import ContentAuthenticitySignal
from vigilancia_multiagente.domain.models import SourceRef
from vigilancia_multiagente.domain.ports.llm_client import LLMClient

logger = logging.getLogger(__name__)

_BOILERPLATE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"as an (AI|language model)", re.IGNORECASE),
    re.compile(r"I don't have (access to|the ability)", re.IGNORECASE),
    re.compile(r"I cannot provide", re.IGNORECASE),
    re.compile(r"I'm sorry, I cannot", re.IGNORECASE),
    re.compile(r"I'm an AI", re.IGNORECASE),
    re.compile(r"as an AI assistant", re.IGNORECASE),
    re.compile(r"there are several (key|important) (factors|aspects)"),
    re.compile(r"In conclusion,? (it is|we can)"),
    re.compile(r"Here('s| is) (a|an|the) (detailed|comprehensive|complete)"),
    re.compile(r"It is important to note that"),
]


class LocalPerplexityAuthenticityDetector:
    def __init__(self, llm_client: LLMClient, penalty_factor: float = 0.5) -> None:
        self._llm_client = llm_client
        self._penalty_factor = penalty_factor

    async def analyze(
        self,
        source: SourceRef,
        raw_text: str,
        raw_freshness: float,
    ) -> ContentAuthenticitySignal:
        perplexity = await self._compute_perplexity(raw_text)
        boost = self._compute_burstiness(raw_text)
        boilerplate_hits = self._count_boilerplate(raw_text)
        ai_prob = self._combine(perplexity, boost, boilerplate_hits)
        effective = raw_freshness * (1.0 - ai_prob * self._penalty_factor)
        return ContentAuthenticitySignal(
            source_id=source.id,
            ai_probability=ai_prob,
            perplexity=perplexity,
            burstiness=boost,
            boilerplate_hits=boilerplate_hits,
            effective_freshness=max(0.0, min(1.0, effective)),
            penalty_factor=self._penalty_factor,
        )

    async def _compute_perplexity(self, text: str) -> float:
        if not text.strip():
            return 0.0
        try:
            response = await self._llm_client.complete(
                [{"role": "user", "content": text[:1000]}],
                logprobs=True,
            )
            logprob = _extract_logprob(response)
            if logprob is not None:
                return math.exp(-logprob)
            return 0.5
        except Exception as exc:
            logger.warning("Perplexity computation failed: %s", exc)
            return 0.5

    @staticmethod
    def _compute_burstiness(text: str) -> float:
        sentences = re.split(r"[.!?]+", text)
        sentences = [s.strip() for s in sentences if s.strip()]
        if len(sentences) < 3:
            return 0.0
        lengths = [float(len(s)) for s in sentences]
        mean = sum(lengths) / len(lengths)
        if mean == 0:
            return 0.0
        variance = sum((x - mean) ** 2 for x in lengths) / len(lengths)
        burstiness = min(1.0, math.sqrt(variance) / mean)
        return burstiness

    @staticmethod
    def _count_boilerplate(text: str) -> int:
        count = 0
        for pattern in _BOILERPLATE_PATTERNS:
            count += len(pattern.findall(text))
        return count

    @staticmethod
    def _combine(perplexity: float, burstiness: float, boilerplate: int) -> float:
        boilerplate_score = min(1.0, boilerplate / 5.0) * 0.3
        if perplexity > 0:
            perplexity_score = max(0.0, 1.0 - perplexity / 10.0) * 0.4
        else:
            perplexity_score = 0.0
        boost_score = (1.0 - burstiness) * 0.3
        return min(1.0, perplexity_score + boost_score + boilerplate_score)


def _extract_logprob(response: object) -> float | None:
    if isinstance(response, dict):
        choices = response.get("choices")
        if isinstance(choices, list) and choices:
            choice = choices[0]
            if isinstance(choice, dict):
                lp = choice.get("logprobs")
                if isinstance(lp, dict):
                    tokens = lp.get("token_logprobs")
                    if isinstance(tokens, list) and tokens:
                        valid = [t for t in tokens if isinstance(t, (int, float))]
                        if valid:
                            return float(sum(valid)) / len(valid)
    return None
