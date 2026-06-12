"""ModeResolver cascade — Spec 021 FR-019 (5-step resolution).

Co-located helper module so the original ``mode_resolver.py`` stays minimal.
The cascade decides which mode to activate for a request when the user has
not issued an explicit ``/mode <id>`` command.

Resolution order (each step short-circuits on a match):

1. **Explicit command** — request body / channel adapter sets ``mode_hint``.
2. **Channel default** — ``config/channels/<channel_id>.yaml`` declares
   ``default_mode`` for the channel where the message arrived.
3. **Regex heuristic** — first user message matched against a small,
   curated list of ``mode_id -> regex`` pairs (cheapest signal beyond
   channel default).
4. **LLM fallback** — :class:`ComplexityClassifier` style, single LLM call
   that tags the intent with the best-matching mode id.
5. **Default mode** — ``"default"``. Always present in the registry.

Constitución:
* SRP: this module decides; it does NOT activate (caller does via
  ``ModeResolver.activate``).
* DIP: depends on protocols, not concrete classes (registry, channel
  config loader, optional LLM classifier).
* #4 explicit: ``ModeNotAvailableError`` (already exported by
  ``mode_resolver``) propagates if the resolved mode is not registered.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import yaml

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResolutionRequest:
    """Inputs the cascade consumes."""

    session_id: str
    channel_id: str = "chat"
    message: str = ""
    explicit_mode: str | None = None  # "/mode <id>" or HTTP body field


# ---------------------------------------------------------------------------
# Pluggable dependencies (DIP)
# ---------------------------------------------------------------------------


class _RegistryProto(Protocol):
    def exists(self, mode_id: str) -> bool: ...
    def list_available(self) -> list[Any]: ...


class _ClassifierProto(Protocol):
    async def classify_mode(self, message: str) -> str: ...


# ---------------------------------------------------------------------------
# Channel defaults loader
# ---------------------------------------------------------------------------


def load_channel_default(channels_dir: Path, channel_id: str) -> str | None:
    """Return ``default_mode`` declared in ``<channel_id>.yaml`` or ``None``."""
    if not channels_dir.is_dir():
        return None
    path = channels_dir / f"{channel_id}.yaml"
    if not path.is_file():
        return None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        logger.warning("ModeResolver: invalid channel YAML %s: %s", path, exc)
        return None
    if isinstance(data, dict):
        mode = data.get("default_mode")
        if isinstance(mode, str) and mode:
            return mode
    return None


# ---------------------------------------------------------------------------
# Regex heuristic
# ---------------------------------------------------------------------------

# Small curated set — order matters (first hit wins). Patterns intentionally
# narrow so they don't false-positive on benign queries.
_REGEX_HEURISTICS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "vigilancia-tech",
        re.compile(
            r"\b(technology\s+watch|vigilancia\s+tecnol[oó]gica|"
            r"competitor\s+intel|patent\s+landscape|patent\s+search|"
            r"signal\s+detection)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "CEO",
        re.compile(
            r"\b(strategic\s+plan|ceo\b|board\s+meeting|deep\s+research|"
            r"investment\s+memo|due\s+diligence)\b",
            re.IGNORECASE,
        ),
    ),
)


def heuristic_mode(message: str) -> str | None:
    if not message or not message.strip():
        return None
    for mode_id, pattern in _REGEX_HEURISTICS:
        if pattern.search(message):
            return mode_id
    return None


# ---------------------------------------------------------------------------
# Cascade resolver
# ---------------------------------------------------------------------------


@dataclass
class CascadeResolver:
    """Implements the 5-step resolution. Returns the chosen ``mode_id``."""

    registry: _RegistryProto
    channels_dir: Path | None = None
    classifier: _ClassifierProto | None = None
    default_mode: str = "default"

    async def resolve(self, request: ResolutionRequest) -> str:
        # 1. Explicit /mode
        if request.explicit_mode and self.registry.exists(request.explicit_mode):
            logger.info(
                "ModeResolver: session=%s explicit -> %s",
                request.session_id,
                request.explicit_mode,
            )
            return request.explicit_mode

        # 2. Channel default
        if self.channels_dir is not None:
            channel_default = load_channel_default(self.channels_dir, request.channel_id)
            if channel_default and self.registry.exists(channel_default):
                logger.info(
                    "ModeResolver: session=%s channel=%s -> %s",
                    request.session_id,
                    request.channel_id,
                    channel_default,
                )
                return channel_default

        # 3. Regex heuristic
        regex_match = heuristic_mode(request.message)
        if regex_match and self.registry.exists(regex_match):
            logger.info("ModeResolver: session=%s regex -> %s", request.session_id, regex_match)
            return regex_match

        # 4. LLM classifier fallback
        if self.classifier is not None and request.message.strip():
            try:
                llm_mode = await self.classifier.classify_mode(request.message)
            except Exception as exc:
                logger.warning("ModeResolver: classifier failed: %s", exc)
                llm_mode = ""
            if llm_mode and self.registry.exists(llm_mode):
                logger.info(
                    "ModeResolver: session=%s llm -> %s",
                    request.session_id,
                    llm_mode,
                )
                return llm_mode

        # 5. Default
        if not self.registry.exists(self.default_mode):
            available = [m.id for m in self.registry.list_available()]
            from vigilancia_multiagente.enterprise.modes.mode_resolver import (
                ModeNotAvailableError,
            )

            raise ModeNotAvailableError(self.default_mode, available)
        logger.info(
            "ModeResolver: session=%s default -> %s",
            request.session_id,
            self.default_mode,
        )
        return self.default_mode
