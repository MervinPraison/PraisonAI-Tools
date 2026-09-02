"""Unit tests for FirefliesTool."""

import os
from unittest.mock import MagicMock, patch

from praisonai_tools.tools.fireflies_tool import (
    FirefliesTool,
    list_fireflies_meetings,
    DEFAULT_API_URL,
)


def _mock_response(payload, status_code=200, headers=None):
    resp = MagicMock()
    resp.json.return_value = payload
    resp.status_code = status_code
    resp.headers = headers or {}
    return resp


# ── Configuration ───────────────────────────────────────────────────


class TestConfiguration:
    def test_api_key_from_arg(self):
        tool = FirefliesTool(api_key="ff_xyz")
        assert tool.api_key == "ff_xyz"

    def test_api_key_from_env(self):
        with patch.dict(os.environ, {"FIREFLIES_API_KEY": "envkey"}, clear=True):
            tool = FirefliesTool()
            assert tool.api_key == "envkey"

    def test_default_api_url(self):
        with patch.dict(os.environ, {}, clear=True):
            tool = FirefliesTool(api_key="x")
            assert tool.api_url == DEFAULT_API_URL

    def test_api_url_override_from_env(self):
        with patch.dict(
            os.environ, {"FIREFLIES_API_URL": "https://proxy.local/graphql"}, clear=True
        ):
            tool = FirefliesTool(api_key="x")
            assert tool.api_url == "https://proxy.local/graphql"


# ── _graphql wiring ─────────────────────────────────────────────────


class TestGraphQL:
    def test_missing_key_returns_distinct_error(self):
        with patch.dict(os.environ, {}, clear=True):
            tool = FirefliesTool()
            assert tool._graphql("query { x }") == {"error": "FIREFLIES_API_KEY required"}

    def test_sends_bearer_header(self):
        tool = FirefliesTool(api_key="ff_xyz")
        with patch("requests.post") as post:
            post.return_value = _mock_response({"data": {"ok": True}})
            tool._graphql("query { x }", {"v": 1})
            kwargs = post.call_args.kwargs
            assert kwargs["headers"]["Authorization"] == "Bearer ff_xyz"
            assert kwargs["json"] == {"query": "query { x }", "variables": {"v": 1}}

    def test_maps_401_to_auth_error(self):
        tool = FirefliesTool(api_key="bad")
        with patch("requests.post", return_value=_mock_response({}, status_code=401)):
            result = tool._graphql("query { x }")
        assert result["status_code"] == 401
        assert "authentication failed" in result["error"]

    def test_maps_403_to_auth_error(self):
        tool = FirefliesTool(api_key="bad")
        with patch("requests.post", return_value=_mock_response({}, status_code=403)):
            result = tool._graphql("query { x }")
        assert result["status_code"] == 403

    def test_rate_limit_surfaces_retry_after(self):
        tool = FirefliesTool(api_key="x")
        resp = _mock_response({}, status_code=429, headers={"Retry-After": "12"})
        with patch("requests.post", return_value=resp):
            result = tool._graphql("query { x }")
        assert result["status_code"] == 429
        assert result["retry_after"] == "12"

    def test_graphql_errors_are_flattened(self):
        tool = FirefliesTool(api_key="x")
        payload = {"errors": [{"message": "boom"}, {"message": "bad"}]}
        with patch("requests.post", return_value=_mock_response(payload)):
            assert tool._graphql("query { x }") == {"error": "boom; bad"}

    def test_handles_request_exception(self):
        tool = FirefliesTool(api_key="x")
        with patch("requests.post", side_effect=RuntimeError("net")):
            assert tool._graphql("q") == {"error": "net"}


# ── list_recent_meetings ────────────────────────────────────────────


class TestListRecentMeetings:
    def test_returns_normalised_meetings(self):
        tool = FirefliesTool(api_key="x")
        payload = {
            "data": {
                "transcripts": [
                    {
                        "id": "m1",
                        "title": "Standup",
                        "date": "2026-01-01",
                        "duration": 15,
                        "organizer_email": "a@x.com",
                    }
                ]
            }
        }
        with patch("requests.post", return_value=_mock_response(payload)):
            meetings = tool.list_recent_meetings(limit=5)
        assert len(meetings) == 1
        assert meetings[0]["title"] == "Standup"
        assert meetings[0]["organizer_email"] == "a@x.com"

    def test_after_cursor_maps_to_skip(self):
        tool = FirefliesTool(api_key="x")
        with patch(
            "requests.post", return_value=_mock_response({"data": {"transcripts": []}})
        ) as post:
            tool.list_recent_meetings(limit=5, after="10")
        sent = post.call_args.kwargs["json"]["variables"]
        assert sent == {"limit": 5, "skip": 10}

    def test_invalid_after_cursor(self):
        tool = FirefliesTool(api_key="x")
        assert tool.list_recent_meetings(after="notint") == [
            {"error": "after must be an integer cursor"}
        ]

    def test_propagates_error(self):
        tool = FirefliesTool(api_key="x")
        with patch("requests.post", side_effect=RuntimeError("net")):
            assert tool.list_recent_meetings() == [{"error": "net"}]


# ── get_transcript ──────────────────────────────────────────────────


class TestGetTranscript:
    def test_requires_meeting_id(self):
        tool = FirefliesTool(api_key="x")
        assert tool.get_transcript(meeting_id="") == {"error": "meeting_id required"}

    def test_returns_normalised_transcript(self):
        tool = FirefliesTool(api_key="x")
        payload = {
            "data": {
                "transcript": {
                    "id": "m1",
                    "title": "Standup",
                    "date": "2026-01-01",
                    "duration": 15,
                    "organizer_email": "a@x.com",
                    "summary": {"overview": "We talked."},
                    "sentences": [
                        {"text": "Hi", "speaker_name": "A", "start_time": 0.0}
                    ],
                }
            }
        }
        with patch("requests.post", return_value=_mock_response(payload)):
            transcript = tool.get_transcript(meeting_id="m1")
        assert transcript["summary"] == "We talked."
        assert transcript["sentence_count"] == 1

    def test_not_found(self):
        tool = FirefliesTool(api_key="x")
        with patch(
            "requests.post",
            return_value=_mock_response({"data": {"transcript": None}}),
        ):
            assert tool.get_transcript(meeting_id="missing") == {
                "error": "transcript not found"
            }


# ── search ──────────────────────────────────────────────────────────


class TestSearch:
    def test_requires_keywords(self):
        tool = FirefliesTool(api_key="x")
        assert tool.search(keywords="") == [{"error": "keywords required"}]

    def test_returns_results(self):
        tool = FirefliesTool(api_key="x")
        payload = {
            "data": {
                "transcripts": [
                    {
                        "id": "m1",
                        "title": "Roadmap",
                        "date": "2026-01-01",
                        "organizer_email": "a@x.com",
                    }
                ]
            }
        }
        with patch("requests.post", return_value=_mock_response(payload)) as post:
            results = tool.search(keywords="roadmap", limit=3)
        sent = post.call_args.kwargs["json"]["variables"]
        assert sent == {"keyword": "roadmap", "limit": 3}
        assert results[0]["title"] == "Roadmap"


# ── run() dispatcher ────────────────────────────────────────────────


class TestRunDispatcher:
    def test_unknown_action(self):
        tool = FirefliesTool(api_key="x")
        assert tool.run(action="bogus") == {"error": "Unknown action: bogus"}

    def test_routes_get_transcript(self):
        tool = FirefliesTool(api_key="x")
        with patch.object(tool, "get_transcript", return_value={"ok": True}) as m:
            out = tool.run(action="get-transcript", meeting_id="m1")
        m.assert_called_once_with(meeting_id="m1")
        assert out == {"ok": True}

    def test_routes_search(self):
        tool = FirefliesTool(api_key="x")
        with patch.object(tool, "search", return_value=[]) as m:
            tool.run(action="search", keywords="hi", limit=5)
        m.assert_called_once_with(keywords="hi", limit=5)


# ── Module-level helper ─────────────────────────────────────────────


class TestListFirefliesMeetingsHelper:
    def test_delegates_to_tool(self):
        with patch.object(
            FirefliesTool, "list_recent_meetings", return_value=["x"]
        ) as m:
            assert list_fireflies_meetings(limit=5) == ["x"]
        m.assert_called_once_with(limit=5)
