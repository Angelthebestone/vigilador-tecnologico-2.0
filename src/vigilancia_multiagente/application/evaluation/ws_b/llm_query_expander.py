"""LlmContextualQueryExpander — spec 007 T070.

Implementa ContextualQueryExpander via LLM.
Aprende terminos de IterationResult previas.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from vigilancia_multiagente.domain.ports.llm_client import LLMClient
from vigilancia_multiagente.domain.ports.query_expander import (
    PriorIterationView,
)

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).resolve().parents[4] / "prompts" / "evaluation" / "query_expand.txt"


class LlmContextualQueryExpander:
    def __init__(self, llm_client: LLMClient) -> None:
        self._llm_client = llm_client
        self._prompt_template = _load_prompt()

    async def expand(
        self,
        base_query: str,
        prior_iterations: list[PriorIterationView],
    ) -> list[str]:
        prior_text = _format_prior(prior_iterations)
        prompt = self._prompt_template.format(
            base_query=base_query,
            prior_iterations=prior_text,
        )
        try:
            response = await self._llm_client.complete([{"role": "user", "content": prompt}])
            content = _extract_content(response)
            expansions = json.loads(content)
            if isinstance(expansions, list):
                return [str(e).strip() for e in expansions if str(e).strip()]
            return []
        except Exception as exc:
            logger.warning("Query expansion failed: %s", exc)
            return []


def _load_prompt() -> str:
    try:
        return _PROMPT_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        return (
            "Given the base query: {base_query}\n"
            "And previous iterations: {prior_iterations}\n"
            "Generate up to 3 query expansions as a JSON list of strings."
        )


def _format_prior(iterations: list[PriorIterationView]) -> str:
    if not iterations:
        return "none"
    lines: list[str] = []
    for i, it in enumerate(iterations, start=1):
        lines.append(f"{i}. query={it.get('query', '')} type={it.get('query_type', '')}")
    return "\n".join(lines)


def _extract_content(response: Any) -> str:
    if isinstance(response, str):
        return response
    if isinstance(response, dict):
        choices = response.get("choices")
        if isinstance(choices, list) and choices:
            msg = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
            content = msg.get("content", "")
            if isinstance(content, str):
                return content
            return str(content)
        content = response.get("content", "")
        if isinstance(content, str):
            return content
        return str(content)
    return str(response)
