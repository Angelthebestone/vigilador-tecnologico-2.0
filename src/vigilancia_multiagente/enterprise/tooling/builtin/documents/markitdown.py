"""Markitdown tool — native WRAP-SDK over Microsoft's ``markitdown`` PyPI package.

Spec 021 FR-053/054: native-first, universal Tool abstraction.
Catalog: ``markitdown`` / domain ``documents`` / capabilities
``[convert_to_markdown, extract_text]``.

Strategy: WRAP-SDK using the ``markitdown`` package (optional dependency).
No network calls — runs entirely in-process. Healthcheck reports
UNCONFIGURED if the package isn't installed.

The package supports many input formats (DOCX, PDF, XLSX, PPTX, HTML, ...).
We expose two capabilities:
* ``convert_to_markdown`` — full Markdown conversion preserving structure.
* ``extract_text`` — plain text fallback (Markdown stripped).
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from pathlib import Path

from vigilancia_multiagente.enterprise.governance.path_security import (
    has_traversal_component,
)
from vigilancia_multiagente.enterprise.tooling.tool_wrapper import HealthcheckResult


@dataclass(frozen=True)
class MarkitdownTool:
    """Native tool that calls the ``markitdown`` Python package."""

    name: str = "markitdown"
    domain: str = "documents"
    is_external_mcp: bool = False
    requires_auth: bool = False

    async def healthcheck(self) -> HealthcheckResult:
        """Verify the optional package is importable."""
        try:
            import markitdown  # noqa: F401  # presence-only import probe
        except ImportError:
            return HealthcheckResult(
                status="UNCONFIGURED",
                error=(
                    "markitdown package not installed; "
                    "run `pip install markitdown` to enable this tool"
                ),
            )
        return HealthcheckResult(status="UP")

    async def execute(self, tool_name: str, args: dict[str, object]) -> dict[str, object]:
        """Dispatch to the requested capability.

        Supported ``tool_name`` values:
        * ``convert_to_markdown`` — args: ``path`` (str). Returns
          ``{path, markdown}``.
        * ``extract_text`` — args: ``path`` (str). Returns ``{path, text}``
          where Markdown formatting is stripped.
        """
        path_str = args.get("path")
        if not isinstance(path_str, str) or not path_str.strip():
            raise ValueError("MarkitdownTool: 'path' must be a non-empty string")
        if has_traversal_component(path_str):
            raise PermissionError(
                f"MarkitdownTool: path '{path_str}' contains traversal components"
            )
        path = Path(path_str)
        if not path.exists():
            raise FileNotFoundError(f"MarkitdownTool: file not found: {path}")

        if tool_name == "convert_to_markdown":
            md = await self._convert(path)
            return {"path": str(path), "markdown": md}
        if tool_name == "extract_text":
            md = await self._convert(path)
            return {"path": str(path), "text": _strip_markdown(md)}
        raise ValueError(
            f"MarkitdownTool: unknown tool_name '{tool_name}' "
            f"(supported: convert_to_markdown, extract_text)"
        )

    async def _convert(self, path: Path) -> str:
        try:
            from markitdown import MarkItDown  # type: ignore[reportAttributeAccessIssue]
        except ImportError as exc:
            raise RuntimeError("MarkitdownTool: markitdown package not installed") from exc

        # MarkItDown is sync; offload to a worker thread.
        def _run() -> str:
            md = MarkItDown()
            result = md.convert(str(path))
            return result.text_content or ""

        return await asyncio.to_thread(_run)


# ---------------------------------------------------------------------------
# Markdown → plain text helper (KISS, regex-based)
# ---------------------------------------------------------------------------

_MARKDOWN_PATTERNS: list[tuple[str, str]] = [
    (r"```[\s\S]*?```", " "),  # fenced code blocks
    (r"`[^`]*`", " "),  # inline code
    (r"!\[([^\]]*)\]\([^)]*\)", r"\1"),  # images → alt text
    (r"\[([^\]]*)\]\([^)]*\)", r"\1"),  # links → text
    (
        r"^#{1,6}\s+",
        "",
    ),  # headings markers (multiline below)
    (r"[*_]{1,3}([^*_]+)[*_]{1,3}", r"\1"),  # bold/italic
    (r"^>\s?", ""),
    (r"\s+", " "),
]


def _strip_markdown(text: str) -> str:
    """Best-effort Markdown→plain text. KISS — regex pipeline."""
    out = text
    for pattern, repl in _MARKDOWN_PATTERNS:
        out = re.sub(pattern, repl, out, flags=re.MULTILINE)
    return out.strip()
