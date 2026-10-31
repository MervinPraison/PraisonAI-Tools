"""Unit tests for LinkUpTool."""

import os
from unittest.mock import MagicMock, patch

from praisonai_tools.tools.linkup_tool import LinkUpTool, linkup_fetch, linkup_search


def _mock_response(payload, status_code=200):
    resp = MagicMock()
    resp.json.return_value = payload
    resp.status_code = status_code
    return resp


# ── Configuration ───────────────────────────────────────────────────


class TestConfiguration:
    def test_api_key_from_arg(self):
        tool = LinkUpTool(api_key="lk_xyz")
        assert tool.api_key == "lk_xyz"

    def test_api_key_from_env(self):
        with patch.dict(os.environ, {"LINKUP_API_KEY": "envkey"}, clear=True):
            tool = LinkUpTool()
            assert tool.api_key == "envkey"


# ── search ──────────────────────────────────────────────────────────


class TestSearch:
    def test_requires_query(self):
        tool = LinkUpTool(api_key="x")
        assert tool.search(query="") == [{"error": "query is required"}]

    def test_missing_key(self):
        with patch.dict(os.environ, {}, clear=True):
            tool = LinkUpTool()
            assert tool.search(query="ai") == [{"error": "LINKUP_API_KEY required"}]

    def test_returns_results(self):
        tool = LinkUpTool(api_key="lk_xyz")
        payload = {
            "results": [
                {"type": "text", "name": "A", "url": "https://a.com", "content": "c"}
            ]
        }
        with patch("requests.post", return_value=_mock_response(payload)) as post:
            results = tool.search(query="ai news")
        kwargs = post.call_args.kwargs
        assert post.call_args.args[0] == "https://api.linkup.so/v1/search"
        assert kwargs["headers"]["Authorization"] == "Bearer lk_xyz"
        assert kwargs["json"] == {
            "q": "ai news",
            "depth": "standard",
            "outputType": "searchResults",
        }
        assert results[0]["url"] == "https://a.com"

    def test_sourced_answer(self):
        tool = LinkUpTool(api_key="x")
        payload = {"answer": "42", "sources": []}
        with patch("requests.post", return_value=_mock_response(payload)):
            results = tool.search(query="q", output_type="sourcedAnswer")
        assert results == [{"content": "42"}]

    def test_handles_request_exception(self):
        tool = LinkUpTool(api_key="x")
        with patch("requests.post", side_effect=RuntimeError("net")):
            assert tool.search(query="q") == [{"error": "net"}]


# ── fetch ───────────────────────────────────────────────────────────


class TestFetch:
    def test_requires_url(self):
        tool = LinkUpTool(api_key="x")
        assert tool.fetch(url="") == {"error": "url is required"}

    def test_missing_key(self):
        with patch.dict(os.environ, {}, clear=True):
            tool = LinkUpTool()
            assert tool.fetch(url="https://a.com") == {"error": "LINKUP_API_KEY required"}

    def test_returns_markdown(self):
        tool = LinkUpTool(api_key="lk_xyz")
        payload = {"markdown": "# Title"}
        with patch("requests.post", return_value=_mock_response(payload)) as post:
            page = tool.fetch(url="https://a.com")
        kwargs = post.call_args.kwargs
        assert post.call_args.args[0] == "https://api.linkup.so/v1/fetch"
        assert kwargs["headers"]["Authorization"] == "Bearer lk_xyz"
        assert kwargs["json"] == {"url": "https://a.com", "renderJs": False}
        assert page == {"url": "https://a.com", "markdown": "# Title"}

    def test_optional_flags(self):
        tool = LinkUpTool(api_key="x")
        payload = {"markdown": "md", "rawHtml": "<p>md</p>", "images": [{"url": "i"}]}
        with patch("requests.post", return_value=_mock_response(payload)) as post:
            page = tool.fetch(
                url="https://a.com",
                render_js=True,
                include_raw_html=True,
                extract_images=True,
            )
        assert post.call_args.kwargs["json"] == {
            "url": "https://a.com",
            "renderJs": True,
            "includeRawHtml": True,
            "extractImages": True,
        }
        assert page["raw_html"] == "<p>md</p>"
        assert page["images"] == [{"url": "i"}]

    def test_http_error_surfaces_status(self):
        tool = LinkUpTool(api_key="bad")
        with patch("requests.post", return_value=_mock_response({}, status_code=401)):
            result = tool.fetch(url="https://a.com")
        assert result["status_code"] == 401
        assert "HTTP 401" in result["error"]

    def test_handles_request_exception(self):
        tool = LinkUpTool(api_key="x")
        with patch("requests.post", side_effect=RuntimeError("net")):
            assert tool.fetch(url="https://a.com") == {"error": "net"}


# ── run() dispatcher ────────────────────────────────────────────────


class TestRunDispatcher:
    def test_unknown_action(self):
        tool = LinkUpTool(api_key="x")
        assert tool.run(action="bogus") == {"error": "Unknown action: bogus"}

    def test_routes_search(self):
        tool = LinkUpTool(api_key="x")
        with patch.object(tool, "search", return_value=[]) as m:
            tool.run(action="search", query="hi", depth="deep")
        m.assert_called_once_with(query="hi", depth="deep")

    def test_routes_fetch(self):
        tool = LinkUpTool(api_key="x")
        with patch.object(tool, "fetch", return_value={"ok": True}) as m:
            out = tool.run(action="fetch", url="https://a.com", render_js=True)
        m.assert_called_once_with(url="https://a.com", render_js=True)
        assert out == {"ok": True}


# ── Module-level helpers ────────────────────────────────────────────


class TestHelpers:
    def test_linkup_search_delegates(self):
        with patch.object(LinkUpTool, "search", return_value=["x"]) as m:
            assert linkup_search("q") == ["x"]
        m.assert_called_once_with(query="q")

    def test_linkup_fetch_delegates(self):
        with patch.object(LinkUpTool, "fetch", return_value={"markdown": "m"}) as m:
            assert linkup_fetch("https://a.com", render_js=True) == {"markdown": "m"}
        m.assert_called_once_with(url="https://a.com", render_js=True)
