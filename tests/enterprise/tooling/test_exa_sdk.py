"""T075: Exa SDK migration test."""
import pytest
from unittest.mock import patch, MagicMock

from vigilancia_multiagente.enterprise.tooling.builtin.research.exa import ExaTool


def test_exa_healthcheck_no_key():
    """healthcheck returns UNCONFIGURED when API key is missing."""
    tool = ExaTool()
    with patch.dict("os.environ", {}, clear=True):
        import asyncio
        result = asyncio.run(tool.healthcheck())
        assert result.status == "UNCONFIGURED"


def test_exa_healthcheck_with_key():
    """healthcheck returns UP when API key is set."""
    tool = ExaTool()
    with patch.dict("os.environ", {"VT_EXA_API_KEY": "test-key"}):
        import asyncio
        result = asyncio.run(tool.healthcheck())
        assert result.status == "UP"


def test_exa_unknown_tool_name():
    """Unknown tool_name raises ValueError."""
    tool = ExaTool()
    with patch.dict("os.environ", {"VT_EXA_API_KEY": "test-key"}):
        with pytest.raises(ValueError, match="unknown tool_name"):
            import asyncio
            asyncio.run(tool.execute("unknown_tool", {}))


def test_exa_missing_query():
    """Missing query raises ValueError."""
    tool = ExaTool()
    with patch.dict("os.environ", {"VT_EXA_API_KEY": "test-key"}):
        with pytest.raises(ValueError, match="query.*must be a non-empty string"):
            import asyncio
            asyncio.run(tool.execute("semantic_search", {}))


def test_exa_search_uses_sdk():
    """semantic_search uses Exa.search() and returns results."""
    tool = ExaTool()
    mock_result = MagicMock()
    mock_result.url = "https://example.com"
    mock_result.title = "Test"
    mock_result.text = "Test content"
    mock_response = MagicMock()
    mock_response.results = [mock_result]
    with patch.dict("os.environ", {"VT_EXA_API_KEY": "test-key"}):
        with patch("vigilancia_multiagente.enterprise.tooling.builtin.research.exa.Exa") as MockExa:
            instance = MockExa.return_value
            instance.search.return_value = mock_response
            import asyncio
            result = asyncio.run(tool.execute("semantic_search", {"query": "AI safety", "num_results": 5}))
            assert result["query"] == "AI safety"
            assert len(result["results"]) == 1
            assert result["results"][0]["url"] == "https://example.com"
