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

    def test_update_contact_requires_props(self):
        tool = HubSpotTool(access_token="x")
        assert tool.update_contact(contact_id="1") == {"error": "no properties to update"}

    def test_search_contacts_returns_results(self):
        tool = HubSpotTool(access_token="x")
        payload = {"results": [{"id": "1"}, {"id": "2"}]}
        with patch("requests.request", return_value=_mock_response(payload)):
            out = tool.search_contacts(query="alice")
        assert len(out) == 2

    def test_delete_contact_requires_id(self):
        tool = HubSpotTool(access_token="x")
        assert tool.delete_contact(contact_id="") == {"error": "contact_id required"}


# ── Deals ───────────────────────────────────────────────────────────
class TestDeals:
    def test_create_deal_requires_name(self):
        tool = HubSpotTool(access_token="x")
        assert tool.create_deal(dealname="") == {"error": "dealname required"}

    def test_move_deal_stage_patches_dealstage(self):
        tool = HubSpotTool(access_token="x")
        with patch("requests.request", return_value=_mock_response({"id": "1"})) as req:
            tool.move_deal_stage(deal_id="1", stage_id="closedwon")
        assert req.call_args.kwargs["json"]["properties"]["dealstage"] == "closedwon"
        assert req.call_args.args[0] == "PATCH"

    def test_associate_deal_with_contact_uses_type_id_3(self):
        tool = HubSpotTool(access_token="x")
        with patch("requests.request", return_value=_mock_response({"ok": True})) as req:
            tool.associate_deal_with_contact(deal_id="2", contact_id="1")
        url = req.call_args.args[1]
        assert "/deals/2/associations/contacts/1" in url
        assert req.call_args.kwargs["json"][0]["associationTypeId"] == 3


# ── Activities use v3 CRM objects (not legacy /engagements/v1) ───────
class TestActivities:
    def test_log_call_hits_v3_calls_endpoint(self):
        tool = HubSpotTool(access_token="x")
        with patch("requests.request", return_value=_mock_response({"id": "3"})) as req:
            tool.log_call(contact_id="1", body="Discovery call")
        assert req.call_args.args[1].endswith("/crm/v3/objects/calls")
        body = req.call_args.kwargs["json"]
        assert body["properties"]["hs_call_body"] == "Discovery call"
        assert body["associations"][0]["to"]["id"] == "1"

    def test_create_note_associates_multiple_objects(self):
        tool = HubSpotTool(access_token="x")
        with patch("requests.request", return_value=_mock_response({"id": "5"})) as req:
            tool.create_note(body="note", contact_id="1", deal_id="2")
        assocs = req.call_args.kwargs["json"]["associations"]
        assert len(assocs) == 2


# ── Pipelines ───────────────────────────────────────────────────────
class TestPipelines:
    def test_list_pipelines_returns_results(self):
        tool = HubSpotTool(access_token="x")
        with patch(
            "requests.request",
            return_value=_mock_response({"results": [{"id": "default"}]}),
        ):
            out = tool.list_pipelines()
        assert out == [{"id": "default"}]


# ── search_crm ──────────────────────────────────────────────────────
class TestSearchCrm:
    def test_requires_query(self):
        tool = HubSpotTool(access_token="x")
        assert tool.search_crm(query="") == {"error": "query required"}

    def test_searches_all_object_types(self):
        tool = HubSpotTool(access_token="x")
        with patch("requests.request", return_value=_mock_response({"results": []})):
            out = tool.search_crm(query="acme")
        assert set(out.keys()) == {"contacts", "companies", "deals"}


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
        m.assert_called_once_with(email="a@b.com", firstname="Al", lastname="", company="")
