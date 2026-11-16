"""Unit tests for KeenableSearchTool."""

import json
import os
from unittest.mock import MagicMock, patch

from praisonai_tools.tools.keenable_search_tool import (
    KEENABLE_MAX_RESULTS,
    KEENABLE_MAX_SNIPPET_CHARS,
    KEENABLE_MAX_TITLE_CHARS,
    KEENABLE_MAX_URL_CHARS,
    KEENABLE_PUBLIC_SEARCH_URL,
    KEENABLE_SEARCH_URL,
    KeenableSearchTool,
    _NoRedirect,
    keenable_search,
)


class _FakeResponse:
    """Minimal stand-in for an ``http.client.HTTPResponse`` context manager."""

    def __init__(self, raw: bytes):
        self._raw = raw

    def read(self, amt=None):
        """Return at most ``amt`` bytes, honouring the caller's read cap."""
        if amt is None:
            return self._raw
        return self._raw[:amt]

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def _payload(results):
    return json.dumps({"results": results}).encode("utf-8")


# ── Import + schema (CI smoke) ──────────────────────────────────────


class TestImportAndSchema:
    def test_import_via_package(self):
        from praisonai_tools import KeenableSearchTool as PkgTool

        assert PkgTool is KeenableSearchTool

    def test_schema_generation(self):
        tool = KeenableSearchTool()
        schema = tool.get_schema()
        assert schema["function"]["name"] == "keenable_search"
        assert "description" in schema["function"]
        assert "action" in schema["function"]["parameters"]["properties"]


# ── Endpoint selection ──────────────────────────────────────────────


class TestEndpointSelection:
    def test_public_endpoint_without_key(self):
        with patch.dict(os.environ, {}, clear=True):
            tool = KeenableSearchTool()
        assert tool.api_key == ""

        captured = {}

        def fake_open(request, timeout=None):
            captured["url"] = request.full_url
            captured["headers"] = dict(request.header_items())
            return _FakeResponse(_payload([]))

        opener = MagicMock()
        opener.open.side_effect = fake_open
        with patch("urllib.request.build_opener", return_value=opener):
            tool.search("python", max_results=3)

        assert captured["url"] == KEENABLE_PUBLIC_SEARCH_URL
        header_names = {k.lower() for k in captured["headers"]}
        assert "x-api-key" not in header_names
        assert "X-keenable-title" in captured["headers"] or "X-Keenable-Title" in captured["headers"]

    def test_authenticated_endpoint_with_key(self):
        tool = KeenableSearchTool(api_key="secret-key")
        captured = {}

        def fake_open(request, timeout=None):
            captured["url"] = request.full_url
            captured["headers"] = dict(request.header_items())
            return _FakeResponse(_payload([]))

        opener = MagicMock()
        opener.open.side_effect = fake_open
        with patch("urllib.request.build_opener", return_value=opener):
            tool.search("python", max_results=3)

        assert captured["url"] == KEENABLE_SEARCH_URL
        # urllib title-cases header keys.
        assert captured["headers"].get("X-api-key") == "secret-key"


# ── Result mapping + bounds ─────────────────────────────────────────


class TestResultMapping:
    def _run(self, tool, results):
        opener = MagicMock()
        opener.open.return_value = _FakeResponse(_payload(results))
        with patch("urllib.request.build_opener", return_value=opener):
            return tool.search("q", max_results=10)

    def test_maps_fields(self):
        out = self._run(
            KeenableSearchTool(),
            [{"title": "T", "url": "https://example.com", "snippet": "hello world"}],
        )
        assert out == [{
            "title": "T",
            "url": "https://example.com",
            "snippet": "hello world",
            "provider": "keenable",
        }]

    def test_skips_entries_without_url(self):
        out = self._run(
            KeenableSearchTool(),
            [{"title": "no url"}, {"title": "ok", "url": "https://a.com"}],
        )
        assert len(out) == 1
        assert out[0]["url"] == "https://a.com"

    def test_respects_max_results(self):
        tool = KeenableSearchTool()
        many = [{"url": f"https://a.com/{i}"} for i in range(10)]
        opener = MagicMock()
        opener.open.return_value = _FakeResponse(_payload(many))
        with patch("urllib.request.build_opener", return_value=opener):
            out = tool.search("q", max_results=3)
        assert len(out) == 3

    def test_zero_max_results_short_circuits(self):
        out = KeenableSearchTool().search("q", max_results=0)
        assert out == []

    def test_empty_query_errors(self):
        out = KeenableSearchTool().search("", max_results=5)
        assert out == [{"error": "query is required"}]


# ── Error handling ──────────────────────────────────────────────────


class TestErrorHandling:
    def test_invalid_shape_errors(self):
        tool = KeenableSearchTool()
        opener = MagicMock()
        opener.open.return_value = _FakeResponse(b'{"not_results": 1}')
        with patch("urllib.request.build_opener", return_value=opener):
            out = tool.search("q")
        assert out and "error" in out[0]

    def test_oversized_response_errors(self):
        tool = KeenableSearchTool()
        oversized = b"x" * (1_000_001 + 1)
        opener = MagicMock()
        opener.open.return_value = _FakeResponse(oversized)
        with patch("urllib.request.build_opener", return_value=opener):
            out = tool.search("q")
        assert out == [{"error": "Keenable returned an oversized response"}]

    def test_http_error_is_captured(self):
        tool = KeenableSearchTool()
        opener = MagicMock()
        opener.open.side_effect = RuntimeError("boom")
        with patch("urllib.request.build_opener", return_value=opener):
            out = tool.search("q")
        assert out == [{"error": "boom"}]


# ── Protective bounds + redirect refusal ────────────────────────────


class TestProtections:
    def _capture_body(self, tool, requested):
        """Run a search and return the decoded JSON request body sent."""
        captured = {}

        def fake_open(request, timeout=None):
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return _FakeResponse(_payload([]))

        opener = MagicMock()
        opener.open.side_effect = fake_open
        with patch("urllib.request.build_opener", return_value=opener):
            tool.search("q", max_results=requested)
        return captured["body"]

    def test_caps_requested_results_at_limit(self):
        """max_results above the hard cap is clamped before the request."""
        body = self._capture_body(KeenableSearchTool(), requested=1000)
        assert body["max_results"] == KEENABLE_MAX_RESULTS

    def test_truncates_oversized_title(self):
        """Titles longer than the cap are truncated with an ellipsis."""
        opener = MagicMock()
        opener.open.return_value = _FakeResponse(
            _payload([{"title": "T" * 5000, "url": "https://a.com"}])
        )
        with patch("urllib.request.build_opener", return_value=opener):
            out = KeenableSearchTool().search("q")
        assert len(out[0]["title"]) == KEENABLE_MAX_TITLE_CHARS
        assert out[0]["title"].endswith("…")

    def test_truncates_oversized_snippet(self):
        """Snippets longer than the cap are truncated with an ellipsis."""
        opener = MagicMock()
        opener.open.return_value = _FakeResponse(
            _payload([{"snippet": "s " * 5000, "url": "https://a.com"}])
        )
        with patch("urllib.request.build_opener", return_value=opener):
            out = KeenableSearchTool().search("q")
        assert len(out[0]["snippet"]) == KEENABLE_MAX_SNIPPET_CHARS
        assert out[0]["snippet"].endswith("…")

    def test_skips_oversized_url(self):
        """Results whose URL exceeds the length cap are dropped."""
        long_url = "https://a.com/" + "x" * KEENABLE_MAX_URL_CHARS
        opener = MagicMock()
        opener.open.return_value = _FakeResponse(
            _payload([{"url": long_url}, {"url": "https://ok.com"}])
        )
        with patch("urllib.request.build_opener", return_value=opener):
            out = KeenableSearchTool().search("q")
        assert out == [{
            "title": "",
            "url": "https://ok.com",
            "snippet": "",
            "provider": "keenable",
        }]

    def test_read_is_capped_at_limit(self):
        """The body read is bounded, so an oversized stream still errors out."""
        tool = KeenableSearchTool()
        # Far larger than the cap; _FakeResponse.read honours the byte count,
        # so this verifies the read limit rather than a pre-sized buffer.
        opener = MagicMock()
        opener.open.return_value = _FakeResponse(b"x" * 5_000_000)
        with patch("urllib.request.build_opener", return_value=opener):
            out = tool.search("q")
        assert out == [{"error": "Keenable returned an oversized response"}]

    def test_refuses_redirects(self):
        """The redirect handler drops 3xx responses so no follow-up is sent."""
        handler = _NoRedirect()
        # Returning None is urllib's signal to NOT build/send a second request.
        assert handler.redirect_request(
            MagicMock(), MagicMock(), 302, "Found", {}, "https://evil.example"
        ) is None


# ── Module-level convenience function ───────────────────────────────


class TestConvenienceFunction:
    def test_keenable_search_function(self):
        opener = MagicMock()
        opener.open.return_value = _FakeResponse(_payload([{"url": "https://a.com"}]))
        with patch("urllib.request.build_opener", return_value=opener):
            out = keenable_search("q", max_results=2)
        assert out[0]["provider"] == "keenable"
