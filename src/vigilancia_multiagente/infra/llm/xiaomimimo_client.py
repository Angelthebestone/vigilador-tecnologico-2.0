"""Xiaomimimo LLM client — OpenAI-compatible endpoint."""

from __future__ import annotations

import time
from dataclasses import dataclass

import openai

from vigilancia_multiagente.config.settings import get_settings
from vigilancia_multiagente.enterprise.governance.audit_log import AuditLogPort


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
    def __init__(self, audit_log: AuditLogPort | None = None) -> None:
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
        self._audit_log = audit_log

    async def chat_completion(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        model: str | None = None,
        agent_id: str | None = None,
        session_id: str | None = None,
    ) -> ChatResponse:
        model = model or self._settings.xiaomimimo_model

        kwargs: dict = {
            "model": model,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools

        t0 = time.perf_counter()
        error: str | None = None
        try:
            response = await self._client.chat.completions.create(**kwargs)
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            self._audit(
                model=model,
                latency_ms=(time.perf_counter() - t0) * 1000,
                prompt_tokens=0,
                completion_tokens=0,
                agent_id=agent_id,
                session_id=session_id,
                prompt_excerpt=self._first_user_message(messages),
                error=error,
            )
            raise

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

        usage = {
            "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
            "completion_tokens": response.usage.completion_tokens if response.usage else 0,
            "total_tokens": response.usage.total_tokens if response.usage else 0,
        }
        self._audit(
            model=response.model,
            latency_ms=(time.perf_counter() - t0) * 1000,
            prompt_tokens=usage["prompt_tokens"],
            completion_tokens=usage["completion_tokens"],
            agent_id=agent_id,
            session_id=session_id,
            prompt_excerpt=self._first_user_message(messages),
            error=None,
        )

        return ChatResponse(
            content=msg.content,
            tool_calls=tool_calls,
            model=response.model,
            usage=usage,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _first_user_message(messages: list[dict]) -> str | None:
        for m in messages:
            if isinstance(m, dict) and m.get("role") == "user":
                content = m.get("content")
                if isinstance(content, str):
                    return content
        return None

    def _audit(
        self,
        *,
        model: str,
        latency_ms: float,
        prompt_tokens: int,
        completion_tokens: int,
        agent_id: str | None,
        session_id: str | None,
        prompt_excerpt: str | None,
        error: str | None,
    ) -> None:
        if self._audit_log is None:
            return
        self._audit_log.log_llm_call(
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            agent_id=agent_id,
            session_id=session_id,
            prompt_excerpt=prompt_excerpt,
            error=error,
        )
