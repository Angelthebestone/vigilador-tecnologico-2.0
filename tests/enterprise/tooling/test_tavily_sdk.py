"""T066: Tavily SDK migration test — respx-mocked TavilyClient.search()."""

from unittest.mock import patch

import pytest

from vigilancia_multiagente.enterprise.tooling.builtin.research.tavily import TavilyTool


def test_tavily_tool_healthcheck_no_key():
    """healthcheck returns UNCONFIGURED when API key is missing."""
    tool = TavilyTool()
    with patch.dict("os.environ", {}, clear=True):
        import asyncio

        result = asyncio.run(tool.healthcheck())
        assert result.status == "UNCONFIGURED"


def test_tavily_tool_healthcheck_with_key():
    """healthcheck returns UP when API key is set."""
    tool = TavilyTool()
    with patch.dict("os.environ", {"VT_TAVILY_API_KEY": "test-key"}):
        import asyncio

        result = asyncio.run(tool.healthcheck())
        assert result.status == "UP"


def test_tavily_web_search_uses_sdk():
    """web_search uses TavilyClient.search() and returns structured results."""
    tool = TavilyTool()
    mock_response = {
        "results": [{"title": "Test", "url": "https://example.com", "content": "Test content"}],
        "answer": "Test answer",
    }
    with (
        patch.dict("os.environ", {"VT_TAVILY_API_KEY": "test-key"}),
        patch(
            "vigilancia_multiagente.enterprise.tooling.builtin.research.tavily.TavilyClient"
        ) as MockClient,
    ):
        instance = MockClient.return_value
        instance.search.return_value = mock_response
        import asyncio

        result = asyncio.run(tool.execute("web_search", {"query": "test query"}))
        assert result["query"] == "test query"
        assert result["topic"] == "general"
        assert len(result["results"]) == 1
        assert result["answer"] == "Test answer"
        instance.search.assert_called_once_with(
            query="test query",
            max_results=5,
            topic="general",
            search_depth="advanced",
            include_answer=True,
        )


def test_tavily_news_search_topic():
    """news_search sets topic='news'."""
    tool = TavilyTool()
    mock_response = {"results": [], "answer": None}
    with (
        patch.dict("os.environ", {"VT_TAVILY_API_KEY": "test-key"}),
        patch(
            "vigilancia_multiagente.enterprise.tooling.builtin.research.tavily.TavilyClient"
        ) as MockClient,
    ):
        instance = MockClient.return_value
        instance.search.return_value = mock_response
        import asyncio

        result = asyncio.run(tool.execute("news_search", {"query": "AI news"}))
        assert result["topic"] == "news"
        instance.search.assert_called_once_with(
            query="AI news",
            max_results=5,
            topic="news",
            search_depth="advanced",
            include_answer=True,
        )


def test_tavily_unknown_tool_name():
    """Unknown tool_name raises ValueError."""
    tool = TavilyTool()
    with (
        patch.dict("os.environ", {"VT_TAVILY_API_KEY": "test-key"}),
        pytest.raises(ValueError, match=r"unknown tool_name"),
    ):
        import asyncio

        asyncio.run(tool.execute("unknown_tool", {}))


def test_tavily_missing_query():
    """Missing query raises ValueError."""
    tool = TavilyTool()
    with (
        patch.dict("os.environ", {"VT_TAVILY_API_KEY": "test-key"}),
        pytest.raises(ValueError, match=r"query.*must be a non-empty string"),
    ):
        import asyncio

        asyncio.run(tool.execute("web_search", {}))
