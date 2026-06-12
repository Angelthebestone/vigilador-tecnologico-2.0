"""Retry policy and exponential backoff for HTTP providers."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, TypeVar

import httpx

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ProviderError(Exception):
    """Base class for provider errors."""


class ProviderUnconfiguredError(ProviderError):
    """Missing required api_key in environment."""


class ProviderAuthError(ProviderError):
    """Authentication failed."""


class ProviderNotFoundError(ProviderError):
    """Resource not found (404)."""


class ProviderRateLimitError(ProviderError):
    """Rate limit exceeded (429)."""


class ProviderServerError(ProviderError):
    """Server error (5xx)."""


class ProviderResponseError(ProviderError):
    """Unexpected response format."""


class ProviderTimeoutError(ProviderError):
    """Request timed out."""


@dataclass
class ExponentialBackoff:
    """Exponential backoff configuration."""

    initial: float = 1.0
    max: float = 8.0
    multiplier: float = 2.0


@dataclass
class RetryPolicy:
    """Retry policy configuration."""

    max_attempts: int = 3
    backoff: ExponentialBackoff = field(default_factory=ExponentialBackoff)
    retry_on: tuple[type[Exception], ...] = (
        httpx.ConnectError,
        httpx.ReadTimeout,
        ProviderServerError,
    )


def retry_with_policy(policy: RetryPolicy | None = None):
    """Decorator to apply retry policy to async functions."""

    def decorator(func: Callable[..., Any]):
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            actual_policy = policy or RetryPolicy()
            last_exception: Exception | None = None

            for attempt in range(actual_policy.max_attempts):
                try:
                    return await func(*args, **kwargs)
                except actual_policy.retry_on as exc:
                    last_exception = exc
                    if attempt == actual_policy.max_attempts - 1:
                        logger.error(
                            f"Provider call failed after {actual_policy.max_attempts} attempts"
                        )
                        raise

                    wait_time = min(
                        actual_policy.backoff.initial * (actual_policy.backoff.multiplier**attempt),
                        actual_policy.backoff.max,
                    )
                    logger.warning(
                        f"Provider call failed (attempt {attempt + 1}/{actual_policy.max_attempts}), "
                        f"retrying in {wait_time:.1f}s: {exc}"
                    )
                    await asyncio.sleep(wait_time)
                except Exception:
                    # Non-retryable exception, raise immediately
                    raise

            raise last_exception or ProviderError("Unknown provider error")

        return wrapper

    return decorator
