"""Xiaomimimo LLM client — OpenAI-compatible endpoint."""

from __future__ import annotations

from dataclasses import dataclass

import openai

from vigilancia_multiagente.config.settings import get_settings


@dataclass(frozen=True, slots=True)
class ToolCall:
    id: str
    name: str
    arguments: str


@dataclass(frozen=True, slots=True)
class ChatResponse:
    content: str | None
    tool_calls: list[ToolCall]
    model: str
    usage: dict[str, int]


class XiaomimimoClient:
    def __init__(self) -> None:
        self._settings = get_settings()
        api_key = (
            self._settings.xiaomimimo_api_key.get_secret_value()
            if self._settings.xiaomimimo_api_key
            else ""
        )
        self._client = openai.AsyncOpenAI(
            api_key=api_key,
            base_url=self._settings.xiaomimimo_base_url,
        )

    async def chat_completion(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        model: str | None = None,
    ) -> ChatResponse:
        model = model or self._settings.xiaomimimo_model

        kwargs: dict = {
            "model": model,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools

        response = await self._client.chat.completions.create(**kwargs)

        choice = response.choices[0]
        msg = choice.message

        tool_calls: list[ToolCall] = []
        if msg.tool_calls:
            tool_calls = [
                ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=tc.function.arguments,
                )
                for tc in msg.tool_calls
            ]

        return ChatResponse(
            content=msg.content,
            tool_calls=tool_calls,
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            },
        )
