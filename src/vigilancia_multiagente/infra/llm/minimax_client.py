from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx

from vigilancia_multiagente.config.settings import get_settings


@dataclass(slots=True, frozen=True)
class MiniMaxToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(slots=True, frozen=True)
class MiniMaxMessage:
    role: str
    content: str


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
        response = await self._client.post(
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {self._settings.minimax_api_key.get_secret_value()}"},
            json={
                "model": self._settings.minimax_model,
                "messages": [{"role": item.role, "content": item.content} for item in messages],
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
