"""F4a.H / T121 — Dispatcher composition smoke tests.

Verifies the end-to-end glue without exercising the real LLM stack:

* Dispatcher resolves the mode via the cascade.
* Activates it on the (real) ``ModeResolver``.
* Loads the chosen playbook YAML.
* Runs it through ``PlaybookRunner`` with a stub executor.
* Returns a structured ``DispatchResponse`` with all fields populated.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from vigilancia_multiagente.enterprise.modes.mode_resolver import ModeResolver
from vigilancia_multiagente.enterprise.modes.mode_resolver_cascade import (
    CascadeResolver,
)
from vigilancia_multiagente.enterprise.orchestration.dispatcher import (
    Dispatcher,
    DispatcherDeps,
    DispatcherUnavailableError,
    DispatchRequest,
    LLMAgentExecutor,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _write_playbook(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(body), encoding="utf-8")
    return path


class _FakeMode:
    """Minimal duck-typed ModeConfig the dispatcher consumes."""

    def __init__(self, mode_id: str, default_playbook: str) -> None:
        self.id = mode_id
        self.status = "active"
        self.playbooks_default = default_playbook


class _FakeRegistry:
    def __init__(self, modes: dict[str, _FakeMode]) -> None:
        self._modes = modes

    def get(self, mode_id: str):
        return self._modes.get(mode_id)

    def exists(self, mode_id: str) -> bool:
        return mode_id in self._modes

    def list_available(self):
        return list(self._modes.values())


@pytest.fixture
def playbook_dir(tmp_path):
    pb_dir = tmp_path / "playbooks"
    _write_playbook(
        pb_dir / "general.yaml",
        """
        id: general
        mode_compatible: ["*"]
        agents:
          - id: lead
        flow:
          type: sequential
          steps:
            - {agent: lead, input_key: query}
        """,
    )
    _write_playbook(
        pb_dir / "deep-research.yaml",
        """
        id: deep-research
        mode_compatible: ["*"]
        agents:
          - id: lead
        flow:
          type: sequential
          steps:
            - {agent: lead, input_key: query}
        """,
    )
    return pb_dir


@pytest.fixture
def fake_registry():
    return _FakeRegistry(
        {
            "default": _FakeMode("default", "general"),
            "CEO": _FakeMode("CEO", "deep-research"),
        }
    )


@pytest.fixture
def dispatcher(fake_registry, playbook_dir):
    cascade = CascadeResolver(registry=fake_registry, default_mode="default")
    deps = DispatcherDeps(
        cascade_resolver=cascade,
        mode_resolver=ModeResolver(fake_registry),
        complexity_classifier=None,
        playbook_dir=playbook_dir,
        executor_by_playbook={},
    )
    return Dispatcher(deps=deps)


# ---------------------------------------------------------------------------
# End-to-end smoke
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dispatch_with_explicit_mode_runs_corresponding_playbook(dispatcher):
    response = await dispatcher.dispatch(
        DispatchRequest(
            session_id="s-1",
            message="run a deep research on RAG vendors",
            mode_hint="CEO",
        )
    )
    assert response.session_id == "s-1"
    assert response.resolved_mode == "CEO"
    assert response.playbook_id == "deep-research"
    assert response.run_result.completed_steps == 1
    # Stub executor returns the placeholder output keyed by agent_id.
    assert "lead" in response.run_result.outputs


@pytest.mark.asyncio
async def test_dispatch_falls_back_to_default_when_mode_hint_unknown(dispatcher):
    response = await dispatcher.dispatch(
        DispatchRequest(session_id="s-2", message="hi", mode_hint="not-a-mode")
    )
    assert response.resolved_mode == "default"
    assert response.playbook_id == "general"


@pytest.mark.asyncio
async def test_dispatch_uses_custom_executor_when_registered(playbook_dir, fake_registry):
    custom = LLMAgentExecutor(label="custom")
    cascade = CascadeResolver(registry=fake_registry, default_mode="default")
    deps = DispatcherDeps(
        cascade_resolver=cascade,
        mode_resolver=ModeResolver(fake_registry),
        complexity_classifier=None,
        playbook_dir=playbook_dir,
        executor_by_playbook={"general": custom},
    )
    dispatcher = Dispatcher(deps=deps)
    await dispatcher.dispatch(
        DispatchRequest(session_id="s-3", message="anything", mode_hint="default")
    )
    assert custom.calls and custom.calls[0][0] == "lead"


@pytest.mark.asyncio
async def test_dispatch_raises_unavailable_when_playbook_missing(fake_registry, tmp_path):
    """Pointing at an empty playbook dir surfaces a typed error."""
    cascade = CascadeResolver(registry=fake_registry, default_mode="default")
    deps = DispatcherDeps(
        cascade_resolver=cascade,
        mode_resolver=ModeResolver(fake_registry),
        complexity_classifier=None,
        playbook_dir=tmp_path / "no-playbooks",
        executor_by_playbook={},
    )
    dispatcher = Dispatcher(deps=deps)
    with pytest.raises(DispatcherUnavailableError, match="cannot load playbook"):
        await dispatcher.dispatch(
            DispatchRequest(session_id="s-4", message="hi", mode_hint="default")
        )


@pytest.mark.asyncio
async def test_dispatch_passes_complexity_when_classifier_present(playbook_dir, fake_registry):
    class _StubClassifier:
        async def classify(self, query):
            from vigilancia_multiagente.enterprise.orchestration.complexity_classifier import (
                ComplexityDecision,
                ComplexityLevel,
            )

            return ComplexityDecision(
                level=ComplexityLevel.MODERATE,
                reason="2-step lookup",
                raw_response="{}",
            )

    cascade = CascadeResolver(registry=fake_registry, default_mode="default")
    deps = DispatcherDeps(
        cascade_resolver=cascade,
        mode_resolver=ModeResolver(fake_registry),
        complexity_classifier=_StubClassifier(),
        playbook_dir=playbook_dir,
        executor_by_playbook={},
    )
    dispatcher = Dispatcher(deps=deps)
    response = await dispatcher.dispatch(
        DispatchRequest(session_id="s-5", message="x", mode_hint="default")
    )
    assert response.complexity == "MODERATE"
    assert response.complexity_reason == "2-step lookup"
