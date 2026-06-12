"""T069: OpenAlex SDK migration test — verifies polite pool configuration."""

from unittest.mock import MagicMock, patch

import pytest

from vigilancia_multiagente.enterprise.tooling.builtin.research.openalex import OpenAlexTool


def test_openalex_healthcheck():
    """healthcheck always returns UP since OpenAlex is anonymous-public."""
    tool = OpenAlexTool()
    import asyncio

    result = asyncio.run(tool.healthcheck())
    assert result.status == "UP"


def test_openalex_unknown_tool_name():
    """Unknown tool_name raises ValueError."""
    tool = OpenAlexTool()
    with pytest.raises(ValueError, match="unknown tool_name"):
        import asyncio

        asyncio.run(tool.execute("unknown_tool", {"query": "test"}))


def test_openalex_missing_query():
    """Missing query raises ValueError."""
    tool = OpenAlexTool()
    with pytest.raises(ValueError, match=r"query.*must be a non-empty string"):
        import asyncio

        asyncio.run(tool.execute("search_works", {}))


def test_openalex_polite_pool_config():
    """_configure() sets pyalex.config.email from VT_OPENALEX_EMAIL."""
    import pyalex

    tool = OpenAlexTool()
    with patch.dict("os.environ", {"VT_OPENALEX_EMAIL": "test@example.com"}):
        tool._configure()
        assert pyalex.config.email == "test@example.com"


def test_openalex_api_key_config():
    """_configure() sets pyalex.config.api_key from VT_OPENALEX_API_KEY."""
    import pyalex

    tool = OpenAlexTool()
    with patch.dict("os.environ", {"VT_OPENALEX_API_KEY": "test-key"}):
        tool._configure()
        assert pyalex.config.api_key == "test-key"


def test_openalex_search_works_uses_sdk():
    """search_works uses pyalex Works().search().get() and returns results."""
    tool = OpenAlexTool()
    mock_results = [{"id": "W123", "title": "Test Work"}]
    with (
        patch.dict("os.environ", {"VT_OPENALEX_EMAIL": "test@example.com"}),
        patch(
            "vigilancia_multiagente.enterprise.tooling.builtin.research.openalex.Works"
        ) as MockWorks,
    ):
        mock_instance = MagicMock()
        mock_instance.search.return_value = mock_instance
        mock_instance.per_page.return_value = mock_instance
        mock_instance.get.return_value = mock_results
        MockWorks.return_value = mock_instance
        import asyncio

        result = asyncio.run(tool.execute("search_works", {"query": "AI safety", "per_page": 10}))
        assert result["query"] == "AI safety"
        assert result["tool"] == "search_works"
        assert result["results"] == mock_results
        mock_instance.search.assert_called_once_with("AI safety")
        mock_instance.per_page.assert_called_once_with(10)
        mock_instance.get.assert_called_once()
