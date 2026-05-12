"""Tests for MiniMaxClient request payload and response parsing."""

from dataclasses import dataclass
from unittest.mock import AsyncMock

import pytest
from pydantic import SecretStr

from vigilancia_multiagente.infra.llm.minimax_client import MiniMaxClient, MiniMaxMessage, _parse_response


@dataclass
class FakeSettings:
    minimax_api_key: SecretStr | None = SecretStr("test-key")
    minimax_model: str = "MiniMax-M2.7"
    minimax_base_url: str = "https://api.minimax.io"


@pytest.fixture
def client(monkeypatch):
    """MiniMaxClient with fake settings and mocked HTTP client."""
    monkeypatch.setattr("vigilancia_multiagente.infra.llm.minimax_client.get_settings", lambda: FakeSettings())
    c = MiniMaxClient()
    c._client = AsyncMock()
    return c


def _ok_response(choices: list[dict]) -> AsyncMock:
    resp = AsyncMock()
    resp.status_code = 200
    resp.json = lambda: {"choices": choices}
    return resp


def test_complete_sends_max_tokens(client: MiniMaxClient):
    """MiniMaxClient sends max_tokens=100000 in the request payload."""
    client._client.post = AsyncMock(return_value=_ok_response([{"message": {"content": "hello", "tool_calls": []}}]))

    import asyncio
    asyncio.run(client.complete(messages=[MiniMaxMessage(role="user", content="test")]))

    payload = client._client.post.call_args.kwargs["json"]
    assert payload["max_tokens"] == 100000
    assert payload["temperature"] == 0.3
    assert payload["stream"] is False
    assert payload["reasoning_split"] is True


def test_complete_sends_stream_true(client: MiniMaxClient):
    """MiniMaxClient sends stream=True when requested."""
    client._client.post = AsyncMock(return_value=_ok_response([{"message": {"content": "hello", "tool_calls": []}}]))

    import asyncio
    asyncio.run(client.complete(messages=[MiniMaxMessage(role="user", content="test")], stream=True))

    assert client._client.post.call_args.kwargs["json"]["stream"] is True


def test_complete_sends_correct_url(client: MiniMaxClient):
    """MiniMaxClient posts to /v1/chat/completions."""
    client._client.post = AsyncMock(return_value=_ok_response([{"message": {"content": "hello", "tool_calls": []}}]))

    import asyncio
    asyncio.run(client.complete(messages=[MiniMaxMessage(role="user", content="test")]))

    assert client._client.post.call_args.args[0] == "/v1/chat/completions"


def test_complete_raises_without_api_key(monkeypatch):
    """MiniMaxClient raises RuntimeError when VT_MINIMAX_API_KEY is not set."""
    monkeypatch.setattr("vigilancia_multiagente.infra.llm.minimax_client.get_settings",
                        lambda: FakeSettings(minimax_api_key=None))  # type: ignore[arg-type]
    c = MiniMaxClient()
    with pytest.raises(RuntimeError, match="VT_MINIMAX_API_KEY"):
        import asyncio
        asyncio.run(c.complete(messages=[MiniMaxMessage(role="user", content="test")]))


# --- _parse_response tests (pure function, no client needed) ---


def test_parse_response_extracts_reasoning():
    """_parse_response extracts reasoning from reasoning_details field."""
    payload = {
        "choices": [{
            "message": {
                "content": "Final answer",
                "reasoning_details": {"reasoning": "I think step by step..."},
                "tool_calls": [],
            }
        }]
    }
    result = _parse_response(payload)
    assert result.content == "Final answer"
    assert result.reasoning == "I think step by step..."


def test_parse_response_handles_missing_reasoning():
    """_parse_response works when reasoning_details is absent."""
    payload = {
        "choices": [{"message": {"content": "Just answer", "tool_calls": []}}]
    }
    result = _parse_response(payload)
    assert result.content == "Just answer"
    assert result.reasoning == ""


def test_parse_response_handles_tool_calls():
    """_parse_response extracts tool_calls from response."""
    payload = {
        "choices": [{
            "message": {
                "content": "",
                "tool_calls": [
                    {"id": "call_1", "function": {"name": "search", "arguments": '{"q":"test"}'}}
                ],
            }
        }]
    }
    result = _parse_response(payload)
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].name == "search"
    assert result.tool_calls[0].arguments == {"q": "test"}
