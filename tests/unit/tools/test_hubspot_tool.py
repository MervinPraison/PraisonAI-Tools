"""Unit tests for HubSpotTool."""

import os
from unittest.mock import MagicMock, patch

from praisonai_tools.tools.hubspot_tool import (
    HubSpotTool,
    hubspot_create_contact,
    hubspot_search_contacts,
)


def _mock_response(payload, status_code=200, headers=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.headers = headers or {}
    resp.content = b"{}" if payload is not None else b""
    resp.json.return_value = payload
    resp.text = ""
    return resp


# ── _request wiring ─────────────────────────────────────────────────
class TestRequest:
    def test_missing_token_returns_error(self):
        with patch.dict(os.environ, {}, clear=True):
            tool = HubSpotTool()
            assert tool._request("GET", "/x") == {"error": "HUBSPOT_ACCESS_TOKEN required"}

    def test_sends_bearer_header(self):
        tool = HubSpotTool(access_token="pat-123")
        with patch("requests.request") as req:
            req.return_value = _mock_response({"ok": True})
            tool._request("GET", "/crm/v3/objects/contacts")
            headers = req.call_args.kwargs["headers"]
            assert headers["Authorization"] == "Bearer pat-123"

    def test_masks_token_in_error(self):
        tool = HubSpotTool(access_token="secret-tok")
        with patch("requests.request", side_effect=RuntimeError("boom secret-tok leaked")):
            result = tool._request("GET", "/x")
        assert "secret-tok" not in result["error"]
        assert "***" in result["error"]

    def test_retries_on_429_then_succeeds(self):
        tool = HubSpotTool(access_token="x", max_retries=2)
        responses = [
            _mock_response(None, status_code=429, headers={"Retry-After": "0"}),
            _mock_response({"ok": True}),
        ]
        with patch("requests.request", side_effect=responses), patch("time.sleep"):
            result = tool._request("GET", "/x")
        assert result == {"ok": True}

    def test_retry_after_http_date_falls_back_to_backoff(self):
        # A non-numeric Retry-After (HTTP-date form) must not crash the request.
        tool = HubSpotTool(access_token="x", max_retries=1)
        responses = [
            _mock_response(
                None,
                status_code=429,
                headers={"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"},
            ),
            _mock_response({"ok": True}),
        ]
        with patch("requests.request", side_effect=responses), patch("time.sleep") as slp:
            result = tool._request("GET", "/x")
        assert result == {"ok": True}
        assert slp.call_args.args[0] == 1  # 2 ** attempt(0)

    def test_negative_retry_after_is_clamped(self):
        tool = HubSpotTool(access_token="x", max_retries=1)
        responses = [
            _mock_response(None, status_code=429, headers={"Retry-After": "-5"}),
            _mock_response({"ok": True}),
        ]
        with patch("requests.request", side_effect=responses), patch("time.sleep") as slp:
            tool._request("GET", "/x")
        assert slp.call_args.args[0] == 1

    def test_huge_retry_after_is_capped(self):
        tool = HubSpotTool(access_token="x", max_retries=1)
        responses = [
            _mock_response(None, status_code=429, headers={"Retry-After": "99999"}),
            _mock_response({"ok": True}),
        ]
        with patch("requests.request", side_effect=responses), patch("time.sleep") as slp:
            tool._request("GET", "/x")
        assert slp.call_args.args[0] == 60

    def test_bodyless_error_is_not_success(self):
        tool = HubSpotTool(access_token="x")
        with patch("requests.request", return_value=_mock_response(None, status_code=404)):
            result = tool._request("GET", "/x")
        assert result == {"error": "HTTP 404", "status_code": 404}

    def test_http_error_returns_message(self):
        tool = HubSpotTool(access_token="x")
        with patch(
            "requests.request",
            return_value=_mock_response({"message": "Invalid input"}, status_code=400),
        ):
            result = tool._request("POST", "/x", {})
        assert result["error"] == "Invalid input"
        assert result["status_code"] == 400


# ── Contacts ────────────────────────────────────────────────────────
class TestContacts:
    def test_create_contact_requires_email(self):
        tool = HubSpotTool(access_token="x")
        assert tool.create_contact(email="") == {"error": "email required"}

    def test_create_contact_builds_properties(self):
        tool = HubSpotTool(access_token="x")
        with patch("requests.request", return_value=_mock_response({"id": "1"})) as req:
            tool.create_contact(email="a@b.com", firstname="Al", company="Acme")
        body = req.call_args.kwargs["json"]
        assert body["properties"]["email"] == "a@b.com"
        assert body["properties"]["firstname"] == "Al"
        assert body["properties"]["company"] == "Acme"

    def test_get_contact_requires_id_and_passes_properties(self):
        tool = HubSpotTool(access_token="x")
        assert tool.get_contact(contact_id="") == {"error": "contact_id required"}
        with patch("requests.request", return_value=_mock_response({"id": "7"})) as req:
            assert tool.get_contact(contact_id="7", properties=["email", "phone"]) == {"id": "7"}
        assert req.call_args.args[1].endswith("/crm/v3/objects/contacts/7")
        assert req.call_args.kwargs["params"] == {"properties": "email,phone"}

    def test_create_contact_omits_unset_fields(self):
        tool = HubSpotTool(access_token="x")
        with patch("requests.request", return_value=_mock_response({"id": "1"})) as req:
            assert tool.create_contact(email="a@b.com") == {"id": "1"}
        assert req.call_args.kwargs["json"] == {"properties": {"email": "a@b.com"}}

    def test_search_contacts_surfaces_error(self):
        tool = HubSpotTool(access_token="x")
        with patch("requests.request", return_value=_mock_response({"message": "bad"}, status_code=400)):
            assert tool.search_contacts(query="a") == [{"error": "bad", "status_code": 400}]

    def test_search_contacts_returns_results(self):
        tool = HubSpotTool(access_token="x")
        payload = {"results": [{"id": "1"}, {"id": "2"}]}
        with patch("requests.request", return_value=_mock_response(payload)):
            out = tool.search_contacts(query="alice")
        assert len(out) == 2


# ── run() dispatcher ────────────────────────────────────────────────
class TestRunDispatcher:
    def test_unknown_action(self):
        tool = HubSpotTool(access_token="x")
        assert tool.run(action="bogus") == {"error": "Unknown action: bogus"}

    def test_routes_create_contact(self):
        tool = HubSpotTool(access_token="x")
        with patch.object(tool, "create_contact", return_value={"ok": True}) as m:
            tool.run(action="create-contact", email="a@b.com")
        m.assert_called_once_with(email="a@b.com")


# ── Standalone helpers ──────────────────────────────────────────────
class TestStandaloneHelpers:
    def test_search_contacts_helper(self):
        with patch.object(HubSpotTool, "search_contacts", return_value=["x"]) as m:
            assert hubspot_search_contacts(query="a") == ["x"]
        m.assert_called_once_with(query="a")

    def test_create_contact_helper(self):
        with patch.object(HubSpotTool, "create_contact", return_value={"id": "1"}) as m:
            hubspot_create_contact(email="a@b.com", firstname="Al")
        m.assert_called_once_with(email="a@b.com", firstname="Al", lastname=None, company=None)
