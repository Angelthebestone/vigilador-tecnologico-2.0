"""T078: Firecrawl SDK migration test."""
import pytest
from unittest.mock import patch, MagicMock

from vigilancia_multiagente.enterprise.tooling.builtin.research.firecrawl import FirecrawlTool


def test_firecrawl_healthcheck_no_key():
    """healthcheck returns UNCONFIGURED when API key is missing."""
    tool = FirecrawlTool()
    with patch.dict("os.environ", {}, clear=True):
        import asyncio
        result = asyncio.run(tool.healthcheck())
        assert result.status == "UNCONFIGURED"


def test_firecrawl_healthcheck_with_key():
    """healthcheck returns UP when API key is set."""
    tool = FirecrawlTool()
    with patch.dict("os.environ", {"VT_FIRECRAWL_API_KEY": "test-key"}):
        import asyncio
        result = asyncio.run(tool.healthcheck())
        assert result.status == "UP"


def test_firecrawl_unknown_tool_name():
    """Unknown tool_name raises ValueError."""
    tool = FirecrawlTool()
    with patch.dict("os.environ", {"VT_FIRECRAWL_API_KEY": "test-key"}):
        with patch("vigilancia_multiagente.enterprise.tooling.builtin.research.firecrawl.is_safe_url", return_value=True):
            with pytest.raises(ValueError, match="unknown tool_name"):
                import asyncio
                asyncio.run(tool.execute("unknown_tool", {"url": "https://example.com"}))


def test_firecrawl_missing_url():
    """Missing url raises ValueError."""
    tool = FirecrawlTool()
    with patch.dict("os.environ", {"VT_FIRECRAWL_API_KEY": "test-key"}):
        with pytest.raises(ValueError, match="url.*must be a non-empty string"):
            import asyncio
            asyncio.run(tool.execute("scrape_page", {}))


def test_firecrawl_scrape_uses_sdk():
    """scrape_page uses FirecrawlApp.scrape_url() and returns structured results."""
    tool = FirecrawlTool()
    mock_response = {
        "markdown": "# Test\nContent",
        "html": "<h1>Test</h1><p>Content</p>",
        "metadata": {"title": "Test"},
    }
    with patch.dict("os.environ", {"VT_FIRECRAWL_API_KEY": "test-key"}):
        with patch("vigilancia_multiagente.enterprise.tooling.builtin.research.firecrawl.is_safe_url", return_value=True):
            with patch("vigilancia_multiagente.enterprise.tooling.builtin.research.firecrawl.FirecrawlApp") as MockApp:
                instance = MockApp.return_value
                instance.scrape_url.return_value = mock_response
                import asyncio
                result = asyncio.run(tool.execute("scrape_page", {"url": "https://example.com"}))
                assert result["url"] == "https://example.com"
                assert result["markdown"] == "# Test\nContent"
                instance.scrape_url.assert_called_once_with("https://example.com", formats=["markdown", "html"])
