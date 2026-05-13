"""MiniMax M-2.7 client — OpenAI-compatible chat completion."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx

from vigilancia_multiagente.config.settings import get_settings
from vigilancia_multiagente.domain.system_base import MiniMaxMessage
from vigilancia_multiagente.infra.prompts.loader import load_prompt

# Module-level cache for few-shot example content (loaded once)
_SYSTEM_PROMPT: str = ""
_USER_SYSTEM_PROMPT: str = ""
_SAMPLE_USER: str = ""
_SAMPLE_AI: str = ""


def _ensure_examples() -> None:
    """Load MiniMax example prompts once into module globals.

    Files live in ``src/prompts/minimax_examples/``.
    Missing files are silently ignored (no error raised).
    """
    global _SYSTEM_PROMPT, _USER_SYSTEM_PROMPT, _SAMPLE_USER, _SAMPLE_AI
    if not _SYSTEM_PROMPT:
        try:
            _SYSTEM_PROMPT = load_prompt("minimax_examples/system")
        except FileNotFoundError:
            _SYSTEM_PROMPT = "Eres un asistente de investigación tecnológica especializado en vigilancia tecnológica multiagente."
    if not _USER_SYSTEM_PROMPT:
        try:
            _USER_SYSTEM_PROMPT = load_prompt("minimax_examples/user_system")
        except FileNotFoundError:
            _USER_SYSTEM_PROMPT = "Analista senior de vigilancia tecnológica."
    if not _SAMPLE_USER:
        try:
            _SAMPLE_USER = load_prompt("minimax_examples/sample_message_user")
        except FileNotFoundError:
            _SAMPLE_USER = ""
    if not _SAMPLE_AI:
        try:
            _SAMPLE_AI = load_prompt("minimax_examples/sample_message_ai")
        except FileNotFoundError:
            _SAMPLE_AI = ""


@dataclass(slots=True, frozen=True)
class MiniMaxToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(slots=True, frozen=True)
class MiniMaxResponse:
    content: str
    reasoning: str = ""
    tool_calls: tuple[MiniMaxToolCall, ...] = field(default_factory=tuple)
    raw: dict[str, Any] = field(default_factory=dict)


class MiniMaxClient:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._client = httpx.AsyncClient(base_url=self._settings.minimax_base_url)

    async def close(self) -> None:
        await self._client.aclose()

    async def complete(
        self,
        messages: list[MiniMaxMessage],
        *,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = None,
        stream: bool = False,
    ) -> MiniMaxResponse:
        if not self._settings.minimax_api_key:
            raise RuntimeError("VT_MINIMAX_API_KEY is required for MiniMax completion")

        # Build enriched messages with system prompt + few-shot examples on first call
        enriched = _build_enriched_messages(messages)

        response = await self._client.post(
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {self._settings.minimax_api_key.get_secret_value()}"},
            json={
                "model": self._settings.minimax_model,
                "messages": [m.to_dict() for m in enriched],
                "max_tokens": 100000,
                "temperature": 0.3,
                "stream": stream,
                "reasoning_split": True,
                "tools": tools or [],
                "tool_choice": tool_choice or "auto",
            },
            timeout=120.0,
        )
        response.raise_for_status()
        data = response.json()
        return _parse_response(data)


def _build_enriched_messages(messages: list[MiniMaxMessage]) -> list[MiniMaxMessage]:
    """Prepend system, user_system, and few-shot examples.

    Returns the enriched list. Original *messages* are not mutated.
    """
    _ensure_examples()
    enriched: list[MiniMaxMessage] = [
        MiniMaxMessage(role="system", content=_SYSTEM_PROMPT),
    ]
    if _USER_SYSTEM_PROMPT:
        enriched.append(MiniMaxMessage(role="user_system", content=_USER_SYSTEM_PROMPT))
    if _SAMPLE_USER and _SAMPLE_AI:
        enriched.append(MiniMaxMessage(role="sample_message_user", content=_SAMPLE_USER))
        enriched.append(MiniMaxMessage(role="sample_message_ai", content=_SAMPLE_AI))
    enriched.extend(messages)
    return enriched


def _parse_response(payload: dict[str, Any]) -> MiniMaxResponse:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise TypeError("MiniMax payload missing choices")
    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise TypeError("MiniMax payload missing message")
    content = str(message.get("content") or "")
    reasoning = ""
    details = message.get("reasoning_details")
    if isinstance(details, dict):
        reasoning = str(details.get("reasoning") or details.get("thinking") or "")
    elif isinstance(details, str):
        reasoning = details
    tool_calls_payload = message.get("tool_calls") or []
    tool_calls = tuple(_parse_tool_call(item) for item in tool_calls_payload)
    return MiniMaxResponse(content=content, reasoning=reasoning, tool_calls=tool_calls, raw=payload)


def _parse_tool_call(payload: Any) -> MiniMaxToolCall:
    if not isinstance(payload, dict):
        raise TypeError("Tool call payload must be an object")
    function = payload.get("function")
    if not isinstance(function, dict):
        raise TypeError("Tool call payload missing function")
    arguments = function.get("arguments") or {}
    if isinstance(arguments, str):
        import json

        arguments = json.loads(arguments)
    if not isinstance(arguments, dict):
        raise TypeError("Tool call arguments must be an object")
    return MiniMaxToolCall(
        id=str(payload.get("id") or ""),
        name=str(function.get("name") or ""),
        arguments=arguments,
    )
