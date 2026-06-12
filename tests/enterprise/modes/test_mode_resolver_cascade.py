"""F4a.B tests — ModeResolver cascade + ModeContext invariants (Spec 021 FR-019)."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from vigilancia_multiagente.domain.mode_context import ModeContext
from vigilancia_multiagente.enterprise.modes.mode_resolver_cascade import (
    CascadeResolver,
    ResolutionRequest,
    heuristic_mode,
    load_channel_default,
)

# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------


class _StubRegistry:
    def __init__(self, modes: set[str]) -> None:
        self._modes = modes

    def exists(self, mode_id: str) -> bool:
        return mode_id in self._modes

    def list_available(self):
        return [type("M", (), {"id": m})() for m in self._modes]


class _CapturingClassifier:
    def __init__(self, returns: str = "") -> None:
        self.returns = returns
        self.last_message: str | None = None

    async def classify_mode(self, message: str) -> str:
        self.last_message = message
        return self.returns


# ---------------------------------------------------------------------------
# Step 1 — explicit /mode
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cascade_explicit_mode_short_circuits():
    reg = _StubRegistry({"default", "CEO", "vigilancia-tech"})
    resolver = CascadeResolver(registry=reg)
    out = await resolver.resolve(
        ResolutionRequest(session_id="s1", explicit_mode="CEO", message="anything")
    )
    assert out == "CEO"


@pytest.mark.asyncio
async def test_cascade_unknown_explicit_mode_falls_through():
    reg = _StubRegistry({"default"})
    resolver = CascadeResolver(registry=reg)
    out = await resolver.resolve(ResolutionRequest(session_id="s2", explicit_mode="unregistered"))
    assert out == "default"


# ---------------------------------------------------------------------------
# Step 2 — channel default
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cascade_uses_channel_default(tmp_path):
    channels = tmp_path / "channels"
    channels.mkdir()
    (channels / "slack.yaml").write_text("default_mode: vigilancia-tech\n", encoding="utf-8")
    reg = _StubRegistry({"default", "vigilancia-tech"})
    resolver = CascadeResolver(registry=reg, channels_dir=channels)
    out = await resolver.resolve(
        ResolutionRequest(session_id="s3", channel_id="slack", message="hi")
    )
    assert out == "vigilancia-tech"


def test_load_channel_default_returns_none_for_missing(tmp_path):
    assert load_channel_default(tmp_path, "nope") is None


def test_load_channel_default_returns_none_for_invalid_yaml(tmp_path):
    (tmp_path / "x.yaml").write_text("[unbalanced", encoding="utf-8")
    assert load_channel_default(tmp_path, "x") is None


# ---------------------------------------------------------------------------
# Step 3 — regex heuristic
# ---------------------------------------------------------------------------


def test_heuristic_matches_technology_watch_phrase():
    assert heuristic_mode("Run a technology watch on RAG vendors") == "vigilancia-tech"


def test_heuristic_matches_ceo_phrase():
    assert heuristic_mode("Prepare an investment memo for the board") == "CEO"


def test_heuristic_returns_none_for_unrelated_text():
    assert heuristic_mode("what's the weather like?") is None


@pytest.mark.asyncio
async def test_cascade_regex_matches_when_no_channel(tmp_path):
    reg = _StubRegistry({"default", "vigilancia-tech"})
    resolver = CascadeResolver(registry=reg)
    out = await resolver.resolve(
        ResolutionRequest(
            session_id="s4",
            message="vigilancia tecnológica de competidores",
        )
    )
    assert out == "vigilancia-tech"


# ---------------------------------------------------------------------------
# Step 4 — LLM classifier fallback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cascade_llm_classifier_used_when_regex_misses():
    reg = _StubRegistry({"default", "CEO"})
    cls = _CapturingClassifier(returns="CEO")
    resolver = CascadeResolver(registry=reg, classifier=cls)
    out = await resolver.resolve(
        ResolutionRequest(
            session_id="s5",
            message="design our next strategic offsite",
        )
    )
    assert out == "CEO"
    assert cls.last_message is not None


@pytest.mark.asyncio
async def test_cascade_llm_failure_falls_through_to_default():
    class _BoomClassifier:
        async def classify_mode(self, message: str):
            raise RuntimeError("downstream LLM dead")

    reg = _StubRegistry({"default"})
    resolver = CascadeResolver(registry=reg, classifier=_BoomClassifier())
    out = await resolver.resolve(
        ResolutionRequest(session_id="s6", message="random text not matching anything")
    )
    assert out == "default"


# ---------------------------------------------------------------------------
# Step 5 — default
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cascade_falls_to_default_when_nothing_matches():
    reg = _StubRegistry({"default"})
    resolver = CascadeResolver(registry=reg)
    out = await resolver.resolve(ResolutionRequest(session_id="s7", message="hi"))
    assert out == "default"


@pytest.mark.asyncio
async def test_cascade_raises_when_default_missing_too():
    from vigilancia_multiagente.enterprise.modes.mode_resolver import (
        ModeNotAvailableError,
    )

    reg = _StubRegistry(set())  # empty registry
    resolver = CascadeResolver(registry=reg, default_mode="default")
    with pytest.raises(ModeNotAvailableError):
        await resolver.resolve(ResolutionRequest(session_id="s8"))


# ---------------------------------------------------------------------------
# ModeContext immutability (FR-019)
# ---------------------------------------------------------------------------


def test_mode_context_is_frozen():
    ctx = ModeContext(
        soul_overlay="overlays/default.md",
        company_context={"name": "Acme"},
        skills_allowed=frozenset({"k_dense.adaptyv"}),
        playbooks_allowed=frozenset({"general"}),
        tools_allowed=frozenset({"tavily"}),
        company_geo={"country": "Colombia"},
    )
    with pytest.raises(FrozenInstanceError):
        ctx.soul_overlay = "/etc/passwd"  # type: ignore[misc]


def test_mode_context_company_geo_defaults_to_empty_dict():
    ctx = ModeContext(
        soul_overlay="x",
        company_context={},
        skills_allowed=frozenset(),
        playbooks_allowed=frozenset(),
        tools_allowed=frozenset(),
    )
    # Default factory must return a fresh dict each time.
    assert ctx.company_geo == {}


def test_mode_context_two_instances_have_independent_geo_dicts():
    a = ModeContext(
        soul_overlay="x",
        company_context={},
        skills_allowed=frozenset(),
        playbooks_allowed=frozenset(),
        tools_allowed=frozenset(),
    )
    b = ModeContext(
        soul_overlay="y",
        company_context={},
        skills_allowed=frozenset(),
        playbooks_allowed=frozenset(),
        tools_allowed=frozenset(),
    )
    assert a.company_geo is not b.company_geo
