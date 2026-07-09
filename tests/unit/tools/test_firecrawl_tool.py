"""Unit tests for FirecrawlTool (firecrawl-py v2/>=4)."""

import os
from unittest.mock import MagicMock, patch

from praisonai_tools.tools.firecrawl_tool import (
    FirecrawlTool,
    firecrawl_search,
)


def _tool_with_mock_client():
    tool = FirecrawlTool(api_key="fc-test")
    tool._client = MagicMock()
    return tool


# ── scrape ──────────────────────────────────────────────────────────


class TestScrape:
    def test_missing_url_returns_error(self):
        tool = FirecrawlTool(api_key="fc-test")
        assert tool.scrape(url="") == {"error": "url is required"}

    def test_missing_api_key_returns_error(self):
        with patch.dict(os.environ, {}, clear=True):
            tool = FirecrawlTool()
            assert tool.scrape(url="https://a.com") == {
                "error": "FIRECRAWL_API_KEY not configured"
            }

    def test_coerces_typed_metadata_to_dict(self):
        tool = _tool_with_mock_client()
        metadata = MagicMock()
        metadata.model_dump.return_value = {"source_url": "https://a.com"}
        doc = MagicMock(markdown="# Hello", metadata=metadata)
        tool._client.scrape.return_value = doc

        result = tool.scrape(url="https://a.com")

        assert result["url"] == "https://a.com"
        assert result["markdown"] == "# Hello"
        assert result["metadata"] == {"source_url": "https://a.com"}

    def test_none_metadata_becomes_empty_dict(self):
        tool = _tool_with_mock_client()
        doc = MagicMock(markdown="x", metadata=None)
        tool._client.scrape.return_value = doc

        assert tool.scrape(url="https://a.com")["metadata"] == {}


# ── crawl ───────────────────────────────────────────────────────────


class TestCrawl:
    def test_missing_url_returns_error(self):
        tool = FirecrawlTool(api_key="fc-test")
        assert tool.crawl(url="") == [{"error": "url is required"}]

    def test_parses_typed_crawljob_data(self):
        tool = _tool_with_mock_client()
        meta = MagicMock(source_url="https://a.com/1", title="Page 1")
        page = MagicMock(markdown="# P1", metadata=meta)
        tool._client.crawl.return_value = MagicMock(data=[page])

        result = tool.crawl(url="https://a.com", limit=5)

        assert result == [
            {"url": "https://a.com/1", "title": "Page 1", "markdown": "# P1"}
        ]

    def test_string_limit_is_coerced(self):
        tool = _tool_with_mock_client()
        tool._client.crawl.return_value = MagicMock(data=[])

        tool.crawl(url="https://a.com", limit="3")

        _, kwargs = tool._client.crawl.call_args
        assert kwargs["limit"] == 3

    def test_invalid_limit_falls_back_to_default(self):
        tool = _tool_with_mock_client()
        tool._client.crawl.return_value = MagicMock(data=[])

        tool.crawl(url="https://a.com", limit="not-a-number")

        _, kwargs = tool._client.crawl.call_args
        assert kwargs["limit"] == 10


# ── search ──────────────────────────────────────────────────────────


class TestSearch:
    def test_missing_query_returns_error(self):
        tool = FirecrawlTool(api_key="fc-test")
        assert tool.search(query="") == [{"error": "query is required"}]

    def test_reads_web_results_from_searchdata(self):
        tool = _tool_with_mock_client()
        item = MagicMock(
            url="https://a.com",
            title="A",
            description="desc",
            markdown="",
        )
        tool._client.search.return_value = MagicMock(web=[item])

        result = tool.search(query="hello", limit=3)

        assert result == [
            {
                "url": "https://a.com",
                "title": "A",
                "description": "desc",
                "markdown": "",
            }
        ]

    def test_string_limit_is_coerced(self):
        tool = _tool_with_mock_client()
        tool._client.search.return_value = MagicMock(web=[])

        tool.search(query="hi", limit="2")

        args, kwargs = tool._client.search.call_args
        assert kwargs.get("limit", args[1] if len(args) > 1 else None) == 2

    def test_invalid_limit_falls_back_to_default(self):
        tool = _tool_with_mock_client()
        tool._client.search.return_value = MagicMock(web=[])

        tool.search(query="hi", limit=None)

        args, kwargs = tool._client.search.call_args
        assert kwargs.get("limit", args[1] if len(args) > 1 else None) == 5


# ── run() dispatcher ────────────────────────────────────────────────


class TestRunDispatch:
    def test_routes_search_action(self):
        tool = _tool_with_mock_client()
        tool._client.search.return_value = MagicMock(web=[])

        result = tool.run(action="search", query="hi", limit=2)

        assert result == []
        tool._client.search.assert_called_once()

    def test_unknown_action(self):
        tool = FirecrawlTool(api_key="fc-test")
        assert tool.run(action="nope") == {"error": "Unknown action: nope"}


# ── module-level helper ─────────────────────────────────────────────


def test_firecrawl_search_helper_delegates():
    with patch(
        "praisonai_tools.tools.firecrawl_tool.FirecrawlTool.search"
    ) as mock_search:
        mock_search.return_value = [{"url": "https://a.com"}]
        assert firecrawl_search("hi", limit=1) == [{"url": "https://a.com"}]
        mock_search.assert_called_once_with(query="hi", limit=1)
