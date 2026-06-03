"""Tests for BaseHTTPProvider and retry policy."""

from __future__ import annotations

import os

import httpx
import pytest
import respx

from vigilancia_multiagente.enterprise.tooling.builtin._base import (
    BaseHTTPProvider,
    ProviderError,
    ProviderServerError,
    ProviderTimeoutError,
    ProviderUnconfiguredError,
    RetryPolicy,
)
from vigilancia_multiagente.enterprise.tooling.tool_wrapper import HealthcheckResult


class _StubProvider(BaseHTTPProvider):
    name = "stub"
    domain = "test"
    base_url = "https://stub.example.com"
    auth_env_var = "STUB_API_KEY"

    async def execute(self, tool_name: str, args: dict) -> dict:
        return await self.post("/api/echo", json=args)


@pytest.mark.asyncio
@respx.mock
async def test_retry_on_503_recovers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STUB_API_KEY", "secret")
    p = _StubProvider()
    route = respx.post("https://stub.example.com/api/echo").mock(
        side_effect=[
            httpx.Response(503),
            httpx.Response(503),
            httpx.Response(200, json={"ok": True}),
        ]
    )
    result = await p.execute("test", {"x": 1})
    assert result == {"ok": True}
    assert route.call_count == 3
    await p.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_retry_exhausts_then_raises_server_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STUB_API_KEY", "secret")
    p = _StubProvider(retry_policy=RetryPolicy(max_attempts=2))
    respx.post("https://stub.example.com/api/echo").mock(return_value=httpx.Response(503))
    
    with pytest.raises(ProviderServerError):
        await p.execute("test", {"x": 1})
    await p.aclose()


@pytest.mark.asyncio
async def test_missing_api_key_raises_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("STUB_API_KEY", raising=False)
    p = _StubProvider()
    
    with pytest.raises(ProviderUnconfiguredError):
        await p.execute("test", {"x": 1})
    await p.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_timeout_raises_provider_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STUB_API_KEY", "secret")
    p = _StubProvider()
    respx.post("https://stub.example.com/api/echo").mock(side_effect=httpx.ReadTimeout("timeout"))
    
    with pytest.raises(ProviderTimeoutError):
        await p.execute("test", {"x": 1})
    await p.aclose()


@pytest.mark.asyncio
async def test_aclose_closes_client() -> None:
    p = _StubProvider()
    _ = p.client  # Initialize client
    assert p._client is not None
    assert not p._client.is_closed
    
    await p.aclose()
    assert p._client.is_closed


@pytest.mark.asyncio
@respx.mock
async def test_post_uses_pool_singleton(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STUB_API_KEY", "secret")
    p = _StubProvider()
    respx.post("https://stub.example.com/api/echo").mock(return_value=httpx.Response(200, json={"ok": True}))
    
    client1 = p.client
    client2 = p.client
    assert client1 is client2  # Same instance
    
    await p.aclose()


@pytest.mark.asyncio
async def test_healthcheck_unconfigured_no_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("STUB_API_KEY", raising=False)
    p = _StubProvider()
    
    result = await p.healthcheck()
    assert result.status == "UNCONFIGURED"
    assert "Missing API key" in (result.error or "")
