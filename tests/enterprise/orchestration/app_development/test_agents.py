"""Tests for individual agents (T015)."""

from __future__ import annotations

import pytest

from vigilancia_multiagente.enterprise.orchestration.app_development.analyze_agent import (
    AnalyzeAgent,
)
from vigilancia_multiagente.enterprise.orchestration.app_development.constitution_agent import (
    ConstitutionAgent,
)
from vigilancia_multiagente.enterprise.orchestration.app_development.errors import (
    InconsistencyBlockError,
    SandboxExecutionError,
)
from vigilancia_multiagente.enterprise.orchestration.app_development.implement_agent import (
    ImplementAgent,
)
from vigilancia_multiagente.enterprise.orchestration.app_development.plan_agent import PlanAgent
from vigilancia_multiagente.enterprise.orchestration.app_development.specify_agent import (
    SpecifyAgent,
)
from vigilancia_multiagente.enterprise.orchestration.app_development.tasks_agent import TasksAgent
from vigilancia_multiagente.enterprise.orchestration.app_development.test_agent import TestAgent

from .conftest import FakeLLM, FakeSandbox, FakeTemplate


@pytest.mark.asyncio
async def test_constitution_agent_generates_document() -> None:
    llm = FakeLLM(response="STACK: Python\nCONSTRAINTS: none\nTARGET_DIRECTORY: /tmp/proj")
    template = FakeTemplate()
    agent = ConstitutionAgent(llm, template)
    result = await agent.run("Build a CLI tool")
    assert "Python" in result.stack
    assert "/tmp/proj" in result.target_directory
    assert "constitution.template.md" in result.document


@pytest.mark.asyncio
async def test_specify_agent_generates_spec() -> None:
    llm = FakeLLM(
        response="FUNCTIONAL_REQUIREMENTS: FR1\nSUCCESS_CRITERIA: SC1\nSCOPE: internal"
    )
    template = FakeTemplate()
    agent = SpecifyAgent(llm, template)
    result = await agent.run("constitution content")
    assert "spec.template.md" in result.document


@pytest.mark.asyncio
async def test_plan_agent_generates_plan() -> None:
    llm = FakeLLM(response="ARCHITECTURE: monolith\nDEPENDENCIES: none\nPHASES: 1,2,3")
    template = FakeTemplate()
    agent = PlanAgent(llm, template)
    result = await agent.run("constitution", "spec")
    assert "plan.template.md" in result.document


@pytest.mark.asyncio
async def test_tasks_agent_generates_tasks() -> None:
    llm = FakeLLM(response="TASKS_LIST: T1, T2\nDEPENDENCIES: T2 depends on T1")
    template = FakeTemplate()
    agent = TasksAgent(llm, template)
    result = await agent.run("plan content")
    assert "tasks.template.md" in result.document


@pytest.mark.asyncio
async def test_analyze_agent_detects_inconsistency_and_blocks() -> None:
    llm = FakeLLM(response="INCONSISTENCY: spec mentions API but plan has no API phase")
    template = FakeTemplate()
    agent = AnalyzeAgent(llm, template)
    with pytest.raises(InconsistencyBlockError) as exc_info:
        await agent.run("constitution", "spec", "plan", "tasks")
    assert len(exc_info.value.inconsistencies) == 1


@pytest.mark.asyncio
async def test_implement_agent_generates_code_in_sandbox() -> None:
    llm = FakeLLM(response="print('hello')")
    sandbox = FakeSandbox(output="hello")
    agent = ImplementAgent(llm, sandbox)
    result = await agent.run("tasks", "constitution")
    assert result.sandbox_output == "hello"
    assert len(sandbox.executions) == 1


@pytest.mark.asyncio
async def test_test_agent_executes_tests_in_sandbox() -> None:
    llm = FakeLLM(response="def test_x(): assert True")
    sandbox = FakeSandbox(output="1 passed")
    template = FakeTemplate()
    agent = TestAgent(llm, sandbox, template)
    result = await agent.run("tasks", "implement output")
    assert result.passed is True
    assert "checklist.template.md" in result.document
