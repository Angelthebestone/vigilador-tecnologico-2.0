"""Tests for diff_engine module."""

from __future__ import annotations

import pytest

from vigilancia_multiagente.enterprise.governance.diff_engine import (
    compute_diff,
    generate_summary,
)


class TestComputeDiff:
    def test_produces_unified_diff(self) -> None:
        old = "line1\nline2\nline3\n"
        new = "line1\nmodified\nline3\n"
        result = compute_diff(old, new, "test.yaml")
        assert "--- a/test.yaml" in result
        assert "+++ b/test.yaml" in result
        assert "-line2\n" in result
        assert "+modified\n" in result

    def test_empty_diff_when_identical(self) -> None:
        content = "same content\n"
        result = compute_diff(content, content, "test.yaml")
        assert result == ""

    def test_handles_new_file(self) -> None:
        result = compute_diff("", "new content\n", "new.yaml")
        assert "+new content\n" in result


class TestGenerateSummary:
    @pytest.mark.asyncio
    async def test_returns_none_when_no_llm(self) -> None:
        result = await generate_summary("some diff", None)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_empty_diff(self) -> None:
        result = await generate_summary("", None)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_summary_from_llm(self) -> None:
        class FakeLLM:
            async def summarize_diff(self, diff: str) -> str:
                return "Changed line2 to modified"

        result = await generate_summary("some diff", FakeLLM())
        assert result == "Changed line2 to modified"

    @pytest.mark.asyncio
    async def test_returns_none_on_llm_error(self) -> None:
        class BrokenLLM:
            async def summarize_diff(self, diff: str) -> str:
                raise RuntimeError("LLM unavailable")

        result = await generate_summary("some diff", BrokenLLM())
        assert result is None
