"""F4a.A tests — ComplexityClassifier (FR-017) + PlaybookRunner (FR-018)."""

from __future__ import annotations

import asyncio
import textwrap
from pathlib import Path
from typing import Any

import pytest

from vigilancia_multiagente.enterprise.orchestration.complexity_classifier import (
    ClassifierError,
    ComplexityClassifier,
    ComplexityLevel,
)
from vigilancia_multiagente.enterprise.orchestration.playbook_runner import (
    PlaybookError,
    PlaybookRunner,
    load_playbook,
)

# ---------------------------------------------------------------------------
# ComplexityClassifier
# ---------------------------------------------------------------------------


class _StubLLM:
    def __init__(self, payload: str | dict | None = None,
                 raise_timeout: bool = False) -> None:
        self.payload = payload
        self.raise_timeout = raise_timeout
        self.last_messages: list | None = None
        self.last_kwargs: dict | None = None

    async def complete(self, messages, **kwargs):
        self.last_messages = messages
        self.last_kwargs = kwargs
        if self.raise_timeout:
            await asyncio.sleep(10)  # let the wait_for fire first
        return self.payload


@pytest.mark.asyncio
async def test_classifier_decodes_strict_json_response():
    llm = _StubLLM(payload='{"level": "MODERATE", "reason": "needs 2 lookups"}')
    clf = ComplexityClassifier(llm_client=llm)
    decision = await clf.classify("compare prices on these 3 SKUs")
    assert decision.level == ComplexityLevel.MODERATE
    assert decision.reason == "needs 2 lookups"


@pytest.mark.asyncio
async def test_classifier_logs_reason(caplog):
    llm = _StubLLM(payload='{"level": "SIMPLE", "reason": "single lookup"}')
    clf = ComplexityClassifier(llm_client=llm)
    with caplog.at_level("INFO"):
        await clf.classify("what is the capital of Colombia?")
    assert any("level=SIMPLE" in rec.message for rec in caplog.records)
    assert any("single lookup" in rec.message for rec in caplog.records)


@pytest.mark.asyncio
async def test_classifier_uses_injected_llm_kwargs():
    llm = _StubLLM(payload='{"level": "COMPLEX", "reason": "multi-step"}')
    clf = ComplexityClassifier(
        llm_client=llm, model_kwargs={"temperature": 0.0, "max_tokens": 32}
    )
    await clf.classify("plan a 6-month research roadmap")
    assert llm.last_kwargs == {"temperature": 0.0, "max_tokens": 32}


@pytest.mark.asyncio
async def test_classifier_timeout_propagates_explicit_error():
    llm = _StubLLM(payload="ignored", raise_timeout=True)
    clf = ComplexityClassifier(llm_client=llm, timeout_s=0.05)
    with pytest.raises(ClassifierError, match="LLM call exceeded"):
        await clf.classify("anything")


@pytest.mark.asyncio
async def test_classifier_rejects_unknown_level():
    llm = _StubLLM(payload='{"level": "BANANA", "reason": "x"}')
    clf = ComplexityClassifier(llm_client=llm)
    with pytest.raises(ClassifierError, match="unknown level"):
        await clf.classify("x")


@pytest.mark.asyncio
async def test_classifier_rejects_empty_query():
    llm = _StubLLM(payload="ignored")
    with pytest.raises(ValueError, match="non-empty"):
        await ComplexityClassifier(llm_client=llm).classify("")


@pytest.mark.asyncio
async def test_classifier_handles_openai_response_shape():
    """Common dict shape from OpenAI-compatible clients."""
    payload = {
        "choices": [
            {"message": {"content": '{"level":"COMPLEX","reason":"deep"}'}}
        ]
    }
    llm = _StubLLM(payload=payload)
    decision = await ComplexityClassifier(llm_client=llm).classify("design a system")
    assert decision.level == ComplexityLevel.COMPLEX


# ---------------------------------------------------------------------------
# PlaybookRunner
# ---------------------------------------------------------------------------


def _write_playbook(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(body), encoding="utf-8")
    return path


def test_load_playbook_parses_well_formed_yaml(tmp_path):
    p = _write_playbook(
        tmp_path / "general.yaml",
        """
        id: general
        display_name: "General assistant"
        description: "Single-agent generalist."
        mode_compatible: ["*"]
        agents:
          - id: lead
            skill: "k_dense.literature.arxiv-paper-search"
        flow:
          type: sequential
          steps:
            - { agent: lead, input_key: "query" }
        guardrails:
          max_total_llm_calls: 5
        """,
    )
    pb = load_playbook(p)
    assert pb.id == "general"
    assert pb.flow_type == "sequential"
    assert len(pb.flow_steps) == 1
    assert pb.guardrails["max_total_llm_calls"] == 5


def test_load_playbook_raises_on_unknown_flow_type(tmp_path):
    p = _write_playbook(
        tmp_path / "bad.yaml",
        """
        id: bad
        agents: [{id: lead}]
        flow: {type: parallel}
        """,
    )
    with pytest.raises(PlaybookError, match=r"flow\.type must be"):
        load_playbook(p)


def test_load_playbook_raises_when_missing_id(tmp_path):
    p = _write_playbook(tmp_path / "noid.yaml", "agents: []\n")
    with pytest.raises(PlaybookError, match="missing 'id'"):
        load_playbook(p)


# Sequential / Rounds runner ---------------------------------------------


class _RecordingExecutor:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    async def execute(self, agent_id: str, inputs: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((agent_id, dict(inputs)))
        return {"value": f"out-{agent_id}", "_llm_calls": 1}


@pytest.mark.asyncio
async def test_runner_rejects_mode_outside_compatible(tmp_path):
    p = _write_playbook(
        tmp_path / "x.yaml",
        """
        id: x
        mode_compatible: ["CEO"]
        agents: [{id: lead}]
        flow: {type: sequential, steps: [{agent: lead}]}
        """,
    )
    pb = load_playbook(p)
    runner = PlaybookRunner(executor=_RecordingExecutor())
    with pytest.raises(PlaybookError, match="not compatible with mode"):
        await runner.run(pb, active_mode="default")


@pytest.mark.asyncio
async def test_runner_executes_sequential_flow(tmp_path):
    p = _write_playbook(
        tmp_path / "seq.yaml",
        """
        id: seq
        mode_compatible: ["*"]
        agents:
          - id: a
          - id: b
        flow:
          type: sequential
          steps:
            - { agent: a, input_key: "query" }
            - { agent: b, input_key: "a.value" }
        """,
    )
    pb = load_playbook(p)
    exec_ = _RecordingExecutor()
    runner = PlaybookRunner(executor=exec_)
    result = await runner.run(pb, active_mode="default", initial_inputs={"query": "hi"})
    assert result.completed_steps == 2
    assert result.outputs["a"]["value"] == "out-a"
    assert result.outputs["b"]["value"] == "out-b"
    # b's input resolves "a.value" through the dotted-path helper.
    assert exec_.calls[1][1]["a.value"] == "out-a"


@pytest.mark.asyncio
async def test_runner_executes_rounds_flow(tmp_path):
    p = _write_playbook(
        tmp_path / "rnd.yaml",
        """
        id: rnd
        mode_compatible: ["*"]
        agents: [{id: a}, {id: b}]
        flow:
          type: rounds
          rounds:
            max: 2
            agents: [a, b]
        """,
    )
    pb = load_playbook(p)
    exec_ = _RecordingExecutor()
    runner = PlaybookRunner(executor=exec_)
    result = await runner.run(pb, active_mode="default")
    # 2 rounds x 2 agents = 4 executor calls
    assert len(exec_.calls) == 4
    assert "round_0" in result.outputs
    assert "round_1" in result.outputs


@pytest.mark.asyncio
async def test_runner_enforces_max_total_llm_calls(tmp_path):
    p = _write_playbook(
        tmp_path / "budget.yaml",
        """
        id: budget
        mode_compatible: ["*"]
        agents: [{id: a}, {id: b}, {id: c}]
        flow:
          type: sequential
          steps:
            - {agent: a}
            - {agent: b}
            - {agent: c}
        guardrails:
          max_total_llm_calls: 2
        """,
    )
    pb = load_playbook(p)
    runner = PlaybookRunner(executor=_RecordingExecutor())
    with pytest.raises(PlaybookError, match="max_total_llm_calls=2"):
        await runner.run(pb, active_mode="default")


@pytest.mark.asyncio
async def test_runner_rejects_unknown_agent_in_step(tmp_path):
    p = _write_playbook(
        tmp_path / "u.yaml",
        """
        id: u
        mode_compatible: ["*"]
        agents: [{id: a}]
        flow:
          type: sequential
          steps:
            - {agent: nope}
        """,
    )
    pb = load_playbook(p)
    runner = PlaybookRunner(executor=_RecordingExecutor())
    with pytest.raises(PlaybookError, match="unknown agent"):
        await runner.run(pb, active_mode="default")
