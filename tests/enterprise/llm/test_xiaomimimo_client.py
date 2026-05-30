"""Tests for XiaomimimoClient."""

import json
from dataclasses import dataclass, field

import pytest
import respx
from httpx import Response
from pydantic import SecretStr

from vigilancia_multiagente.infra.llm.xiaomimimo_client import ChatResponse, XiaomimimoClient

BASE_URL = "https://platform.xiaomimimo.com/v1"


@dataclass
class FakeSettings:
    xiaomimimo_api_key: SecretStr | None = field(default_factory=lambda: SecretStr("test-key"))
    xiaomimimo_model: str = "mimo-v2-flash"
    xiaomimimo_base_url: str = BASE_URL


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(
        "vigilancia_multiagente.infra.llm.xiaomimimo_client.get_settings",
        lambda: FakeSettings(),
    )
    return XiaomimimoClient()


@respx.mock
@pytest.mark.asyncio
async def test_chat_completion(client):
    respx.post(f"{BASE_URL}/chat/completions").mock(
        return_value=Response(
            200,
            json={
                "choices": [{"message": {"content": "Hello!", "tool_calls": None}}],
                "model": "mimo-v2-flash",
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            },
        )
    )

    result = await client.chat_completion(messages=[{"role": "user", "content": "Hi"}])

    assert isinstance(result, ChatResponse)
    assert result.content == "Hello!"
    assert result.tool_calls == []
    assert result.model == "mimo-v2-flash"
    assert result.usage["total_tokens"] == 15


@respx.mock
@pytest.mark.asyncio
async def test_tool_calling(client):
    respx.post(f"{BASE_URL}/chat/completions").mock(
        return_value=Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call_abc",
                                    "type": "function",
                                    "function": {
                                        "name": "search",
                                        "arguments": json.dumps({"query": "AI"}),
                                    },
                                }
                            ],
                        }
                    }
                ],
                "model": "mimo-v2-flash",
                "usage": {"prompt_tokens": 8, "completion_tokens": 12, "total_tokens": 20},
            },
        )
    )

    tools = [{"type": "function", "function": {"name": "search", "parameters": {}}}]
    result = await client.chat_completion(
        messages=[{"role": "user", "content": "search AI"}], tools=tools
    )

    assert result.content is None
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].id == "call_abc"
    assert result.tool_calls[0].name == "search"
    assert result.tool_calls[0].arguments == json.dumps({"query": "AI"})


@respx.mock
@pytest.mark.asyncio
async def test_error_401_propagates(client):
    respx.post(f"{BASE_URL}/chat/completions").mock(
        return_value=Response(401, json={"error": "unauthorized"})
    )

    from openai import AuthenticationError

    with pytest.raises(AuthenticationError):
        await client.chat_completion(messages=[{"role": "user", "content": "Hi"}])


@respx.mock
@pytest.mark.asyncio
async def test_error_429_propagates(client):
    respx.post(f"{BASE_URL}/chat/completions").mock(
        return_value=Response(429, json={"error": "rate limited"})
    )

    from openai import RateLimitError

    with pytest.raises(RateLimitError):
        await client.chat_completion(messages=[{"role": "user", "content": "Hi"}])


@respx.mock
@pytest.mark.asyncio
async def test_default_model_applied(client):
    route = respx.post(f"{BASE_URL}/chat/completions").mock(
        return_value=Response(
            200,
            json={
                "choices": [{"message": {"content": "ok", "tool_calls": None}}],
                "model": "mimo-v2-flash",
                "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7},
            },
        )
    )

    await client.chat_completion(messages=[{"role": "user", "content": "test"}])

    request_body = json.loads(route.calls[0].request.content)
    assert request_body["model"] == "mimo-v2-flash"
