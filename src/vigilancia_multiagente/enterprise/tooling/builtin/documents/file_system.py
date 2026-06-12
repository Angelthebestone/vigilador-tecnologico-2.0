# Adapted from Hermes Agent -- original: tools/file_tools.py -- License: MIT
"""file_system — Facade tool for filesystem operations (FR-019, spec 018).

Implements the ToolWrapper protocol with 4 capabilities:
read_file, write_file, list_dir, patch_file.
"""

from __future__ import annotations

from pathlib import Path

from vigilancia_multiagente.enterprise.tooling.builtin.documents._file_operations import (
    list_dir,
    patch_file,
    read_file,
    write_file,
)
from vigilancia_multiagente.enterprise.tooling.builtin.documents._file_safety import (
    PathTraversalError,
)
from vigilancia_multiagente.enterprise.tooling.builtin.documents._file_state import (
    FileStateTracker,
)
from vigilancia_multiagente.enterprise.tooling.tool_wrapper import HealthcheckResult

_CAPABILITIES = frozenset({"read_file", "write_file", "list_dir", "patch_file"})


class FileSystemTool:
    """Root-jailed filesystem tool implementing ToolWrapper."""

    name: str = "file_system"
    domain: str = "documents"
    is_external_mcp: bool = False
    requires_auth: bool = False

    def __init__(self, root: Path) -> None:
        self._root = root.resolve()
        self._state = FileStateTracker()

    async def healthcheck(self) -> HealthcheckResult:
        """Check that the root directory exists and is accessible."""
        if self._root.is_dir():
            return HealthcheckResult(status="UP")
        return HealthcheckResult(
            status="DOWN",
            error=f"Root directory not found: {self._root}",
        )

    async def execute(self, tool_name: str, args: dict[str, object]) -> dict[str, object]:
        """Dispatch to the requested file operation.

        tool_name must be one of: read_file, write_file, list_dir, patch_file.
        """
        if tool_name not in _CAPABILITIES:
            return {"error": (f"Unknown capability '{tool_name}'. Valid: {sorted(_CAPABILITIES)}")}

        try:
            if tool_name == "read_file":
                return self._read(args)
            if tool_name == "write_file":
                return self._write(args)
            if tool_name == "list_dir":
                return self._list(args)
            return self._patch(args)  # patch_file
        except PathTraversalError as exc:
            return {"error": str(exc)}

    # -- private dispatchers --

    def _read(self, args: dict[str, object]) -> dict[str, object]:
        path = args.get("path")
        if not isinstance(path, str) or not path:
            return {"error": "Missing or invalid 'path' argument"}
        return read_file(self._root, path)

    def _write(self, args: dict[str, object]) -> dict[str, object]:
        path = args.get("path")
        if not isinstance(path, str) or not path:
            return {"error": "Missing or invalid 'path' argument"}
        content = args.get("content")
        if not isinstance(content, str):
            return {"error": "Missing or invalid 'content' argument"}
        return write_file(self._root, path, content)

    def _list(self, args: dict[str, object]) -> dict[str, object]:
        path = str(args.get("path", "."))
        return list_dir(self._root, path)

    def _patch(self, args: dict[str, object]) -> dict[str, object]:
        path = args.get("path")
        if not isinstance(path, str) or not path:
            return {"error": "Missing or invalid 'path' argument"}
        old_text = args.get("old_text")
        if not isinstance(old_text, str):
            return {"error": "Missing or invalid 'old_text' argument"}
        new_text = args.get("new_text")
        if not isinstance(new_text, str):
            return {"error": "Missing or invalid 'new_text' argument"}
        return patch_file(self._root, path, old_text, new_text)
