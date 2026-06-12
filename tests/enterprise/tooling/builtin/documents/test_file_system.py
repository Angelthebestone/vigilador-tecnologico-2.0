"""Tests for file_system tool — DB-free, uses tmp_path as root jail."""

from __future__ import annotations

import pytest

from vigilancia_multiagente.enterprise.tooling.builtin.documents._file_safety import (
    PathTraversalError,
    resolve_safe_path,
)
from vigilancia_multiagente.enterprise.tooling.builtin.documents.file_system import (
    FileSystemTool,
)


@pytest.fixture
def tool(tmp_path):
    return FileSystemTool(root=tmp_path)


# -- read/write round-trip --


@pytest.mark.asyncio
async def test_write_and_read_roundtrip(tool, tmp_path):
    result = await tool.execute("write_file", {"path": "hello.txt", "content": "world"})
    assert "error" not in result
    assert result["size"] == 5

    result = await tool.execute("read_file", {"path": "hello.txt"})
    assert result["content"] == "world"
    assert result["size"] == 5


@pytest.mark.asyncio
async def test_write_creates_subdirectories(tool, tmp_path):
    result = await tool.execute("write_file", {"path": "sub/dir/file.txt", "content": "nested"})
    assert "error" not in result
    assert (tmp_path / "sub" / "dir" / "file.txt").read_text() == "nested"


# -- list_dir --


@pytest.mark.asyncio
async def test_list_dir(tool, tmp_path):
    (tmp_path / "a.txt").write_text("a")
    (tmp_path / "b_dir").mkdir()
    result = await tool.execute("list_dir", {"path": "."})
    assert "error" not in result
    entries = result["entries"]
    names = {e["name"] for e in entries}
    assert "a.txt" in names
    assert "b_dir" in names


@pytest.mark.asyncio
async def test_list_dir_nonexistent(tool):
    result = await tool.execute("list_dir", {"path": "nope"})
    assert "error" in result


# -- patch_file --


@pytest.mark.asyncio
async def test_patch_file(tool, tmp_path):
    (tmp_path / "target.txt").write_text("hello world")
    result = await tool.execute(
        "patch_file",
        {"path": "target.txt", "old_text": "world", "new_text": "universe"},
    )
    assert "error" not in result
    assert result["replacements"] == 1
    assert (tmp_path / "target.txt").read_text() == "hello universe"


@pytest.mark.asyncio
async def test_patch_file_old_text_not_found(tool, tmp_path):
    (tmp_path / "f.txt").write_text("abc")
    result = await tool.execute("patch_file", {"path": "f.txt", "old_text": "xyz", "new_text": "q"})
    assert "error" in result
    assert "not found" in result["error"]


# -- path traversal rejection --


@pytest.mark.asyncio
async def test_traversal_rejected_read(tool):
    result = await tool.execute("read_file", {"path": "../../etc/passwd"})
    assert "error" in result
    assert "traversal" in result["error"].lower()


@pytest.mark.asyncio
async def test_traversal_rejected_write(tool):
    result = await tool.execute("write_file", {"path": "../../../tmp/evil.txt", "content": "bad"})
    assert "error" in result
    assert "traversal" in result["error"].lower()


@pytest.mark.asyncio
async def test_traversal_rejected_list(tool):
    result = await tool.execute("list_dir", {"path": "../../"})
    assert "error" in result
    assert "traversal" in result["error"].lower()


def test_resolve_safe_path_rejects_traversal(tmp_path):
    with pytest.raises(PathTraversalError):
        resolve_safe_path(tmp_path, "../../etc")


def test_resolve_safe_path_allows_nested(tmp_path):
    (tmp_path / "sub").mkdir()
    result = resolve_safe_path(tmp_path, "sub")
    assert result == (tmp_path / "sub").resolve()


# -- unknown capability --


@pytest.mark.asyncio
async def test_unknown_capability(tool):
    result = await tool.execute("delete_file", {"path": "x"})
    assert "error" in result
    assert "Unknown capability" in result["error"]


# -- healthcheck --


@pytest.mark.asyncio
async def test_healthcheck_up(tool):
    hc = await tool.healthcheck()
    assert hc.status == "UP"


@pytest.mark.asyncio
async def test_healthcheck_down(tmp_path):
    tool = FileSystemTool(root=tmp_path / "nonexistent")
    hc = await tool.healthcheck()
    assert hc.status == "DOWN"
