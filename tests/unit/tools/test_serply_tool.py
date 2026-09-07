"""Unit tests for the Serply search tool (offline, requests is mocked)."""

import os
from unittest.mock import MagicMock, patch

from praisonai_tools.tools.serply_tool import (
    SerplyTool,
    serply_news_search,
    serply_scholar_search,
    serply_search,
)


def _response(payload, ok=True, status=200, text=""):
    resp = MagicMock()
    resp.ok = ok
    resp.status_code = status
    resp.text = text
    resp.json.return_value = payload
    return resp


class TestSerplyToolConfig:
    def test_missing_api_key_returns_error(self):
        with patch.dict(os.environ, {}, clear=True):
            result = SerplyTool().search("python")
        assert result == [{"error": "SERPLY_API_KEY not configured"}]

    def test_explicit_api_key_overrides_env(self):
        with patch.dict(os.environ, {"SERPLY_API_KEY": "env-key"}, clear=True):
            assert SerplyTool(api_key="explicit").api_key == "explicit"

    def test_query_required(self):
        assert SerplyTool(api_key="k").search("") == [{"error": "query is required"}]

    def test_unknown_action(self):
        assert SerplyTool(api_key="k").run(action="images", query="x") == {"error": "Unknown action: images"}

    def test_discoverable_from_package(self):
        from praisonai_tools.tools import SerplyTool as Discovered

        assert Discovered is SerplyTool


class TestSerplySearch:
    def test_search_calls_api_and_normalizes(self):
        payload = {
            "results": [
                {"title": "Python", "link": "https://python.org", "description": "Official site", "position": 1},
            ]
        }
        with patch("requests.get", return_value=_response(payload)) as get:
            results = SerplyTool(api_key="k").run(action="search", query="python", max_results=5)

        assert results == [
            {"title": "Python", "url": "https://python.org", "snippet": "Official site", "position": 1}
        ]
        args, kwargs = get.call_args
        assert args[0] == "https://api.serply.io/v1/search/"
        assert kwargs["headers"]["X-Api-Key"] == "k"
        assert kwargs["params"] == {"q": "python", "num": 5}

    def test_page_size_is_capped_at_ten(self):
        with patch("requests.get", return_value=_response({"results": []})) as get:
            SerplyTool(api_key="k").search("python", max_results=50)
        assert get.call_args.kwargs["params"]["num"] == 10

    def test_negative_max_results_is_clamped_to_one(self):
        payload = {"results": [{"title": "a", "link": "u", "description": "d", "position": 1}] * 3}
        with patch("requests.get", return_value=_response(payload)) as get:
            results = SerplyTool(api_key="k").search("python", max_results=-1)
        assert get.call_args.kwargs["params"]["num"] == 1
        assert len(results) == 1

    def test_zero_max_results_is_clamped_to_one(self):
        with patch("requests.get", return_value=_response({"results": []})) as get:
            SerplyTool(api_key="k").news("python", max_results=0)
        assert get.call_args.kwargs["params"]["num"] == 1

    def test_http_error_is_reported(self):
        bad = _response({"detail": "Invalid API key"}, ok=False, status=401, text='{"detail":"Invalid API key"}')
        with patch("requests.get", return_value=bad):
            results = SerplyTool(api_key="bad").search("python")
        assert len(results) == 1
        assert results[0]["error"].startswith("Serply API error 401")

    def test_request_exception_is_reported(self):
        with patch("requests.get", side_effect=RuntimeError("boom")):
            assert SerplyTool(api_key="k").search("python") == [{"error": "boom"}]

    def test_module_function(self):
        with patch("requests.get", return_value=_response({"results": []})):
            with patch.dict(os.environ, {"SERPLY_API_KEY": "k"}, clear=True):
                assert serply_search("python") == []


class TestSerplyNews:
    def test_news_slices_and_strips_html(self):
        entries = [
            {
                "title": f"Story {i}",
                "link": f"https://news.example/{i}",
                "published": "Wed, 26 Aug 2026 09:00:09 GMT",
                "source": {"href": "https://example.com", "title": "Example"},
                "summary": '<a href="https://x">Story</a>&nbsp;&nbsp;text',
            }
            for i in range(20)
        ]
        with patch("requests.get", return_value=_response({"entries": entries})) as get:
            with patch.dict(os.environ, {"SERPLY_API_KEY": "k"}, clear=True):
                results = serply_news_search("quantum", max_results=3)

        assert get.call_args.args[0] == "https://api.serply.io/v1/news/"
        assert len(results) == 3
        assert results[0] == {
            "title": "Story 0",
            "url": "https://news.example/0",
            "source": "Example",
            "date": "Wed, 26 Aug 2026 09:00:09 GMT",
            "snippet": "Story text",
        }


class TestSerplyScholar:
    def test_scholar_normalizes_articles(self):
        payload = {
            "articles": [
                {
                    "title": "Quantum Computing in the NISQ era",
                    "link": "https://doi.org/10.22331/q-2018-08-06-79",
                    "description": "John Preskill - Quantum, 2018",
                    "author": {"names": "John Preskill - Quantum, 2018", "authors": []},
                    "extras": {"citations": {"count": 8592, "link": "https://openalex.org/..."}},
                    "doc": {"link": "https://quantum-journal.org/paper.pdf", "type": "PDF"},
                }
            ]
        }
        with patch("requests.get", return_value=_response(payload)) as get:
            with patch.dict(os.environ, {"SERPLY_API_KEY": "k"}, clear=True):
                results = serply_scholar_search("quantum computing", max_results=2)

        assert get.call_args.args[0] == "https://api.serply.io/v1/scholar/"
        assert results == [
            {
                "title": "Quantum Computing in the NISQ era",
                "url": "https://doi.org/10.22331/q-2018-08-06-79",
                "authors": "John Preskill - Quantum, 2018",
                "snippet": "John Preskill - Quantum, 2018",
                "citations": 8592,
                "document_url": "https://quantum-journal.org/paper.pdf",
            }
        ]
