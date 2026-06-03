"""Base HTTP provider for tooling providers."""

from __future__ import annotations

import logging
import os
from typing import Any, ClassVar

import httpx

from vigilancia_multiagente.enterprise.tooling.builtin._base.retry_policy import (
    ProviderAuthError,
    ProviderError,
    ProviderNotFoundError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderServerError,
    ProviderTimeoutError,
    ProviderUnconfiguredError,
    RetryPolicy,
    retry_with_policy,
)
from vigilancia_multiagente.enterprise.tooling.tool_wrapper import HealthcheckResult

logger = logging.getLogger(__name__)


class BaseHTTPProvider:
    """Base class for HTTP-based tool providers.

    Subclasses must define:
    - name: ClassVar[str]
    - domain: ClassVar[str]
    - base_url: ClassVar[str]
    - auth_env_var: ClassVar[str | None]
    - requires_auth: ClassVar[bool] = True
    """

    name: ClassVar[str]
    domain: ClassVar[str]
    base_url: ClassVar[str]
    auth_env_var: ClassVar[str | None] = None
    requires_auth: ClassVar[bool] = True
    is_external_mcp: ClassVar[bool] = False

    def __init__(self, retry_policy: RetryPolicy | None = None) -> None:
        self._client: httpx.AsyncClient | None = None
        self._retry_policy = retry_policy or RetryPolicy()

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
                timeout=httpx.Timeout(30.0, connect=5.0),
            )
        return self._client

    async def aclose(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _api_key(self) -> str | None:
        if not self.auth_env_var:
            return None
        return os.environ.get(self.auth_env_var)

    def _auth_headers(self, api_key: str) -> dict[str, str]:
        """Default Bearer token auth. Subclasses override for custom patterns."""
        return {"Authorization": f"Bearer {api_key}"}

    def _handle_response_error(self, response: httpx.Response) -> None:
        """Map HTTP status codes to specific ProviderError subclasses."""
        if response.status_code == 401:
            raise ProviderAuthError(f"Authentication failed: {response.status_code}")
        if response.status_code == 404:
            raise ProviderNotFoundError(f"Resource not found: {response.status_code}")
        if response.status_code == 429:
            raise ProviderRateLimitError(f"Rate limit exceeded: {response.status_code}")
        if response.status_code >= 500:
            raise ProviderServerError(f"Server error: {response.status_code}")
        raise ProviderResponseError(f"Unexpected response: {response.status_code}")

    @retry_with_policy()
    async def post(self, path: str, json: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        api_key = await self._api_key()
        if self.requires_auth and not api_key:
            raise ProviderUnconfiguredError(f"Missing required API key for {self.name}")

        headers = {**(kwargs.pop("headers", {})), **self._auth_headers(api_key)}
        try:
            response = await self.client.post(path, json=json, headers=headers, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            self._handle_response_error(exc.response)
            raise
        except httpx.ReadTimeout as exc:
            raise ProviderTimeoutError("Request timed out") from exc
        except httpx.RequestError as exc:
            raise ProviderError(f"Request failed: {exc}") from exc

    @retry_with_policy()
    async def get(self, path: str, **kwargs: Any) -> dict[str, Any]:
        api_key = await self._api_key()
        if self.requires_auth and not api_key:
            raise ProviderUnconfiguredError(f"Missing required API key for {self.name}")

        headers = {**(kwargs.pop("headers", {})), **self._auth_headers(api_key)}
        try:
            response = await self.client.get(path, headers=headers, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            self._handle_response_error(exc.response)
            raise
        except httpx.ReadTimeout as exc:
            raise ProviderTimeoutError("Request timed out") from exc
        except httpx.RequestError as exc:
            raise ProviderError(f"Request failed: {exc}") from exc

    async def healthcheck(self) -> HealthcheckResult:
        """Default healthcheck: api_key gating. Subclasses override for endpoint pings."""
        if self.requires_auth and not (await self._api_key()):
            return HealthcheckResult(
                status="UNCONFIGURED",
                error=f"Missing API key for {self.name}",
            )
        return HealthcheckResult(status="UP")

    async def execute(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        """Execute the tool. Subclasses must implement this."""
        raise NotImplementedError(f"Subclass must implement execute() for {self.name}")
