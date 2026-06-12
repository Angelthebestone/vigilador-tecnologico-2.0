"""T081: Brave BaseHTTPProvider migration test."""

import os
from unittest.mock import patch

import pytest

from vigilancia_multiagente.enterprise.tooling.builtin.research.brave import BraveTool


def test_brave_healthcheck_no_key():
    """healthcheck returns UNCONFIGURED when API key is missing."""
    tool = BraveTool()
    with patch.dict("os.environ", {}, clear=False):
        os.environ.pop("VT_BRAVE_API_KEY", None)
        import asyncio

        result = asyncio.run(tool.healthcheck())
        assert result.status == "UNCONFIGURED"


def test_brave_auth_headers():
    """_auth_headers uses X-Subscription-Token instead of Bearer."""
    tool = BraveTool()
    headers = tool._auth_headers("test-key")
    assert headers == {"X-Subscription-Token": "test-key", "Accept": "application/json"}


def test_brave_unknown_tool_name():
    """Unknown tool_name raises ValueError."""
    tool = BraveTool()
    with pytest.raises(ValueError, match="unknown tool_name"):
        import asyncio

        asyncio.run(tool.execute("unknown_tool", {"query": "test"}))


def test_brave_missing_query():
    """Missing query raises ValueError."""
    tool = BraveTool()
    with pytest.raises(ValueError, match=r"query.*must be a non-empty string"):
        import asyncio

        asyncio.run(tool.execute("web_search", {}))


def test_brave_web_search_uses_base_get():
    """web_search uses BaseHTTPProvider.get() and returns results."""
    tool = BraveTool()
    mock_payload = {"web": {"results": [{"title": "Test", "url": "https://example.com"}]}}
    with patch.object(tool, "get", return_value=mock_payload) as mock_get:
        import asyncio

        result = asyncio.run(tool.execute("web_search", {"query": "test query", "count": 5}))
        assert result["query"] == "test query"
        assert len(result["results"]) == 1
        mock_get.assert_called_once_with("/web/search", params={"q": "test query", "count": 5})
