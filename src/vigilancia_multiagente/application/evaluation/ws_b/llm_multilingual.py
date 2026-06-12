"""LlmMultilingualNormalizer — spec 007 T073.

Implementa MultilingualNormalizer via LLM.
Usa una sola llamada por documento para detectar idioma, traducir, y
calcular distribucion de idiomas.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from vigilancia_multiagente.domain.models import SourceRef
from vigilancia_multiagente.domain.ports.llm_client import LLMClient

logger = logging.getLogger(__name__)

_DETECT_PROMPT = (
    "Detect the language of the following text. Return a JSON object with "
    'a "language" field (ISO 639-1 code) and a "confidence" field (0-1).\n'
    "Text: {text}\n"
    "Response:"
)

_TRANSLATE_PROMPT = (
    "Translate the following text to {target}. "
    "Return a JSON object with a 'translated' field containing the translation.\n"
    "Text: {text}\n"
    "Response:"
)


class LlmMultilingualNormalizer:
    def __init__(self, llm_client: LLMClient) -> None:
        self._llm_client = llm_client

    async def detect_language(self, text: str) -> str:
        prompt = _DETECT_PROMPT.format(text=text[:2000])
        try:
            response = await self._llm_client.complete([{"role": "user", "content": prompt}])
            content = _extract_json(_extract_content(response))
            if isinstance(content, dict):
                return str(content.get("language", "en"))
            return "en"
        except Exception as exc:
            logger.warning("Language detection failed: %s", exc)
            return "en"

    async def translate(self, text: str, target: str = "en") -> str:
        prompt = _TRANSLATE_PROMPT.format(text=text[:2000], target=target)
        try:
            response = await self._llm_client.complete([{"role": "user", "content": prompt}])
            content = _extract_json(_extract_content(response))
            if isinstance(content, dict):
                return str(content.get("translated", text))
            return text
        except Exception as exc:
            logger.warning("Translation failed: %s", exc)
            return text

    async def language_distribution(self, sources: list[SourceRef]) -> dict[str, float]:
        if not sources:
            return {}

        texts_to_check = [s.title or s.url for s in sources if s.title or s.url]
        if not texts_to_check:
            return {"en": 1.0}

        lang_counts: dict[str, int] = {}
        for text in texts_to_check:
            lang = await self.detect_language(text)
            lang_counts[lang] = lang_counts.get(lang, 0) + 1

        total = sum(lang_counts.values())
        return {
            lang: round(count / total, 4)
            for lang, count in sorted(lang_counts.items(), key=lambda x: x[1], reverse=True)
        }


def _extract_content(response: Any) -> str:
    if isinstance(response, str):
        return response
    if isinstance(response, dict):
        choices = response.get("choices")
        if isinstance(choices, list) and choices:
            msg = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
            content = msg.get("content", "")
            return str(content) if content else ""
        content = response.get("content", "")
        return str(content) if content else ""
    return str(response)


def _extract_json(content: str) -> dict[str, object] | None:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        import re

        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
    return None
