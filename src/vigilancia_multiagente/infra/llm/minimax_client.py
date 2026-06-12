"""MiniMax M-2.7 client — OpenAI-compatible chat completion."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx

from vigilancia_multiagente.config.settings import get_settings
from vigilancia_multiagente.domain.system_base import MiniMaxMessage
from vigilancia_multiagente.infra.prompts.loader import load_prompt

_DEFAULT_SYSTEM = (
    "Eres un asistente de investigación tecnológica especializado en "
    "vigilancia tecnológica multiagente."
)
_DEFAULT_USER_SYSTEM = "Analista senior de vigilancia tecnológica."


def _load_example(path: str, default: str = "") -> str:
    """Return the example prompt at *path*, or *default* if the file is missing.

    Backed by ``load_prompt``'s LRU cache, so repeated calls do not hit disk.
    """
    try:
        return load_prompt(path)
    except FileNotFoundError:
        return default


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
            headers={
                "Authorization": f"Bearer {self._settings.minimax_api_key.get_secret_value()}"
            },
            json={
                "model": self._settings.minimax_model,
                "messages": [m.to_dict() for m in enriched],
                "temperature": 0.3,
                "max_tokens": 100000,
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
    system_prompt = _load_example("minimax_examples/system", _DEFAULT_SYSTEM)
    user_system = _load_example("minimax_examples/user_system", _DEFAULT_USER_SYSTEM)
    sample_user = _load_example("minimax_examples/sample_message_user")
    sample_ai = _load_example("minimax_examples/sample_message_ai")

    enriched: list[MiniMaxMessage] = [MiniMaxMessage(role="system", content=system_prompt)]
    if user_system:
        enriched.append(MiniMaxMessage(role="user_system", content=user_system))
    if sample_user and sample_ai:
        enriched.append(MiniMaxMessage(role="sample_message_user", content=sample_user))
        enriched.append(MiniMaxMessage(role="sample_message_ai", content=sample_ai))
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
