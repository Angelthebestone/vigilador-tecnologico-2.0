"""T072: Arxiv SDK migration test."""

from unittest.mock import MagicMock, patch

import pytest

from vigilancia_multiagente.enterprise.tooling.builtin.research.arxiv import ArxivTool


def test_arxiv_healthcheck():
    """healthcheck always returns UP since arXiv is anonymous-public."""
    tool = ArxivTool()
    import asyncio

    result = asyncio.run(tool.healthcheck())
    assert result.status == "UP"


def test_arxiv_unknown_tool_name():
    """Unknown tool_name raises ValueError."""
    tool = ArxivTool()
    with pytest.raises(ValueError, match="unknown tool_name"):
        import asyncio

        asyncio.run(tool.execute("unknown_tool", {"query": "test"}))


def test_arxiv_list_categories():
    """list_categories returns the curated subject list."""
    tool = ArxivTool()
    import asyncio

    result = asyncio.run(tool.execute("list_categories", {}))
    assert "categories" in result
    assert "cs.AI" in result["categories"]


def test_arxiv_missing_query():
    """Missing query raises ValueError."""
    tool = ArxivTool()
    with pytest.raises(ValueError, match=r"query.*must be a non-empty string"):
        import asyncio

        asyncio.run(tool.execute("search_papers", {}))


def test_arxiv_search_uses_sdk():
    """search_papers uses arxiv.Client().results() and returns structured results."""
    tool = ArxivTool()
    mock_paper = MagicMock()
    mock_paper.entry_id = "http://arxiv.org/abs/2401.12345v1"
    mock_paper.title = "Test Paper"
    mock_paper.summary = "Test summary"
    mock_paper.published = MagicMock(isoformat=MagicMock(return_value="2024-01-01T00:00:00"))
    mock_paper.authors = ["Author One"]
    mock_paper.categories = ["cs.AI"]
    mock_paper.pdf_url = "https://arxiv.org/pdf/2401.12345"

    with patch(
        "vigilancia_multiagente.enterprise.tooling.builtin.research.arxiv.arxiv.Client"
    ) as MockClient:
        instance = MockClient.return_value
        instance.results.return_value = [mock_paper]
        import asyncio

        result = asyncio.run(
            tool.execute("search_papers", {"query": "AI safety", "max_results": 5})
        )
        assert result["query"] == "AI safety"
        assert len(result["results"]) == 1
        assert result["results"][0]["title"] == "Test Paper"
