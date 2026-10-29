"""Unit tests for SerperTool, focused on configurable base-URL routing."""

import os
from unittest.mock import MagicMock, patch

from praisonai_tools.tools.serper_tool import SerperTool


def _mock_requests(response_json):
    """Return a MagicMock standing in for the lazily-imported ``requests`` module."""
    response = MagicMock()
    response.json.return_value = response_json
    requests = MagicMock()
    requests.post.return_value = response
    return requests


class TestBaseUrlRouting:
    def test_default_base_url(self):
        tool = SerperTool(api_key="k")
        requests = _mock_requests({"organic": []})
        with patch.dict(os.environ, {}, clear=True):
            with patch.dict("sys.modules", {"requests": requests}):
                tool.search(query="python")
        url = requests.post.call_args.args[0]
        assert url == "https://google.serper.dev/search"

    def test_custom_base_url(self):
        tool = SerperTool(api_key="k")
        requests = _mock_requests({"organic": []})
        with patch.dict(os.environ, {"SERPER_BASE_URL": "https://litescrape.com"}, clear=True):
            with patch.dict("sys.modules", {"requests": requests}):
                tool.search(query="python")
        url = requests.post.call_args.args[0]
        assert url == "https://litescrape.com/search"

    def test_trailing_slash_is_stripped(self):
        tool = SerperTool(api_key="k")
        requests = _mock_requests({"organic": []})
        with patch.dict(os.environ, {"SERPER_BASE_URL": "https://litescrape.com/"}, clear=True):
            with patch.dict("sys.modules", {"requests": requests}):
                tool.search(query="python")
        url = requests.post.call_args.args[0]
        assert url == "https://litescrape.com/search"

    def test_custom_base_url_routes_news_and_images(self):
        tool = SerperTool(api_key="k")
        for action, payload in (("news", {"news": []}), ("images", {"images": []})):
            requests = _mock_requests(payload)
            with patch.dict(os.environ, {"SERPER_BASE_URL": "https://example.org"}, clear=True):
                with patch.dict("sys.modules", {"requests": requests}):
                    getattr(tool, action)(query="python")
            url = requests.post.call_args.args[0]
            assert url == f"https://example.org/{action}"


class TestMissingApiKey:
    def test_no_api_key_returns_error(self):
        with patch.dict(os.environ, {}, clear=True):
            tool = SerperTool()
            result = tool.search(query="python")
        assert result == [{"error": "SERPER_API_KEY not configured"}]
