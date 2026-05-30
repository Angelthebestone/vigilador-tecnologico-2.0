"""Diff engine: computes unified diffs and optional LLM summaries."""

from __future__ import annotations

import difflib
from typing import Protocol


class LLMClient(Protocol):
    """Minimal protocol for LLM summary generation."""

    async def summarize_diff(self, diff: str) -> str: ...


def compute_diff(old_content: str, new_content: str, filename: str) -> str:
    """Generate a unified diff between old and new content."""
    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)
    diff_lines = difflib.unified_diff(
        old_lines, new_lines, fromfile=f"a/{filename}", tofile=f"b/{filename}"
    )
    return "".join(diff_lines)


async def generate_summary(diff: str, llm_client: LLMClient | None) -> str | None:
    """Generate a 1-2 line summary of the diff via LLM. Returns None if unavailable."""
    if llm_client is None:
        return None
    if not diff:
        return None
    try:
        return await llm_client.summarize_diff(diff)
    except Exception:
        return None
