"""Unit tests for the Serply Scholar tool (offline, requests is mocked)."""

import os
from unittest.mock import MagicMock, patch

from praisonai_tools.tools.serply_tool import SerplyTool, serply_scholar_search

ARTICLE = {
    "title": "Quantum Computing in the NISQ era",
    "link": "https://doi.org/10.22331/q-2018-08-06-79",
    "description": "John Preskill - Quantum, 2018",
    "author": {"names": "John Preskill - Quantum, 2018", "authors": []},
    "extras": {"citations": {"count": 8592, "link": "https://openalex.org/..."}},
    "doc": {"link": "https://quantum-journal.org/paper.pdf", "type": "PDF"},
}
NORMALIZED = {
    "title": "Quantum Computing in the NISQ era",
    "url": "https://doi.org/10.22331/q-2018-08-06-79",
    "authors": "John Preskill - Quantum, 2018",
    "snippet": "John Preskill - Quantum, 2018",
    "citations": 8592,
    "document_url": "https://quantum-journal.org/paper.pdf",
}


def _response(payload, status=200, text=""):
    resp = MagicMock()
    resp.status_code = status
    resp.text = text
    resp.json.return_value = payload
    return resp


class TestSerplyToolConfig:
    def test_missing_api_key_returns_error(self):
        with patch.dict(os.environ, {}, clear=True):
            result = SerplyTool().scholar("python")
        assert result == [{"error": "SERPLY_API_KEY not configured"}]

    def test_explicit_api_key_overrides_env(self):
        with patch.dict(os.environ, {"SERPLY_API_KEY": "env-key"}, clear=True):
            assert SerplyTool(api_key="explicit").api_key == "explicit"

    def test_query_required(self):
        assert SerplyTool(api_key="k").scholar("") == [{"error": "query is required"}]

    def test_unknown_action(self):
        assert SerplyTool(api_key="k").run(action="images", query="x") == {"error": "Unknown action: images"}

    def test_discoverable_from_package(self):
        from praisonai_tools.tools import SerplyTool as Discovered

        assert Discovered is SerplyTool


class TestSerplyScholar:
    def test_scholar_calls_api_and_normalizes(self):
        with patch("requests.get", return_value=_response({"articles": [ARTICLE]})) as get:
            results = SerplyTool(api_key="k").run(action="scholar", query="quantum computing", max_results=5)

        assert results == [NORMALIZED]
        args, kwargs = get.call_args
        assert args[0] == "https://api.serply.io/v1/scholar/"
        assert kwargs["headers"]["X-Api-Key"] == "k"
        assert kwargs["params"] == {"q": "quantum computing", "num": 5}

    def test_results_are_sliced_to_max_results(self):
        with patch("requests.get", return_value=_response({"articles": [ARTICLE] * 5})):
            assert len(SerplyTool(api_key="k").scholar("q", max_results=2)) == 2

    def test_page_size_is_capped_at_ten(self):
        with patch("requests.get", return_value=_response({"articles": []})) as get:
            SerplyTool(api_key="k").scholar("q", max_results=50)
        assert get.call_args.kwargs["params"]["num"] == 10

    def test_non_positive_max_results_is_clamped_to_one(self):
        for value in (0, -1):
            with patch("requests.get", return_value=_response({"articles": [ARTICLE] * 3})) as get:
                results = SerplyTool(api_key="k").scholar("q", max_results=value)
            assert get.call_args.kwargs["params"]["num"] == 1
            assert len(results) == 1

    def test_invalid_max_results_falls_back_to_ten(self):
        with patch("requests.get", return_value=_response({"articles": []})) as get:
            SerplyTool(api_key="k").scholar("q", max_results="many")
        assert get.call_args.kwargs["params"]["num"] == 10

    def test_http_error_is_reported(self):
        bad = _response({"detail": "Invalid API key"}, status=401, text='{"detail":"Invalid API key"}')
        with patch("requests.get", return_value=bad):
            results = SerplyTool(api_key="bad").scholar("q")
        assert len(results) == 1
        assert results[0]["error"].startswith("Serply API error 401")

    def test_any_2xx_status_is_treated_as_success(self):
        with patch("requests.get", return_value=_response({"articles": [ARTICLE]}, status=201)):
            assert SerplyTool(api_key="k").scholar("q") == [NORMALIZED]

    def test_redirects_are_not_followed(self):
        with patch("requests.get", return_value=_response({}, status=302)) as get:
            results = SerplyTool(api_key="k").scholar("q")
        assert get.call_args.kwargs["allow_redirects"] is False
        assert results == [{"error": "Serply API error 302: "}]

    def test_request_exception_is_reported(self):
        with patch("requests.get", side_effect=RuntimeError("boom")):
            assert SerplyTool(api_key="k").scholar("q") == [{"error": "boom"}]

    def test_module_function(self):
        with patch("requests.get", return_value=_response({"articles": [ARTICLE]})):
            with patch.dict(os.environ, {"SERPLY_API_KEY": "k"}, clear=True):
                assert serply_scholar_search("quantum computing") == [NORMALIZED]
