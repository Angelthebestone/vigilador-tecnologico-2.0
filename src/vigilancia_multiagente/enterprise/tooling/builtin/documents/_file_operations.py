# Adapted from Hermes Agent -- original: tools/file_operations.py -- License: MIT
"""File operations: read, write, list_dir, patch.

All operations are root-jailed via _file_safety.resolve_safe_path.
"""

from __future__ import annotations

from pathlib import Path

from vigilancia_multiagente.enterprise.tooling.builtin.documents._file_safety import (
    resolve_safe_path,
)


def read_file(root: Path, path: str) -> dict[str, object]:
    """Read a file's content within the root jail.

    Returns dict with 'content' and 'size', or 'error'.
    """
    resolved = resolve_safe_path(root, path)
    if not resolved.exists():
        return {"error": f"File not found: '{path}'"}
    if not resolved.is_file():
        return {"error": f"Not a file: '{path}'"}
    content = resolved.read_text(encoding="utf-8")
    return {"content": content, "size": len(content)}


def write_file(root: Path, path: str, content: str) -> dict[str, object]:
    """Write content to a file within the root jail.

    Creates parent directories as needed.
    Returns dict with 'written_path' and 'size', or 'error'.
    """
    resolved = resolve_safe_path(root, path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(content, encoding="utf-8")
    return {"written_path": str(resolved), "size": len(content)}


def list_dir(root: Path, path: str = ".") -> dict[str, object]:
    """List directory contents within the root jail.

    Returns dict with 'entries' list of {name, type, size}.
    """
    resolved = resolve_safe_path(root, path)
    if not resolved.exists():
        return {"error": f"Directory not found: '{path}'"}
    if not resolved.is_dir():
        return {"error": f"Not a directory: '{path}'"}

    entries: list[dict[str, object]] = []
    for item in sorted(resolved.iterdir()):
        entry: dict[str, object] = {"name": item.name}
        if item.is_dir():
            entry["type"] = "directory"
        else:
            entry["type"] = "file"
            entry["size"] = item.stat().st_size
        entries.append(entry)
    return {"entries": entries}


def patch_file(root: Path, path: str, old_text: str, new_text: str) -> dict[str, object]:
    """Replace first occurrence of old_text with new_text in a file.

    Returns dict with 'patched_path' and 'replacements', or 'error'.
    """
    resolved = resolve_safe_path(root, path)
    if not resolved.exists():
        return {"error": f"File not found: '{path}'"}
    if not resolved.is_file():
        return {"error": f"Not a file: '{path}'"}

    content = resolved.read_text(encoding="utf-8")
    if old_text not in content:
        return {"error": f"old_text not found in '{path}'"}

    new_content = content.replace(old_text, new_text, 1)
    resolved.write_text(new_content, encoding="utf-8")
    return {"patched_path": str(resolved), "replacements": 1}
