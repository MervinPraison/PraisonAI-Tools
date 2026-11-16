"""Unit tests for SaltTool."""

import os
from unittest.mock import MagicMock, patch

from praisonai_tools.tools.salt_tool import SaltTool, create_salt_card


def _mock_response(payload, status_code=200):
    resp = MagicMock()
    resp.json.return_value = payload
    resp.status_code = status_code
    resp.content = b"1"  # non-empty, so SaltTool._request calls resp.json()
    return resp


# ── Key handling ─────────────────────────────────────────────────────


class TestKeyHandling:
    def test_env_key_fallback(self):
        with patch.dict(os.environ, {"SALT_API_KEY": "sk_x"}, clear=True):
            tool = SaltTool()
            assert tool.api_key == "sk_x"

    def test_explicit_key_overrides_env(self):
        with patch.dict(os.environ, {"SALT_API_KEY": "sk_env"}, clear=True):
            tool = SaltTool(api_key="sk_explicit")
            assert tool.api_key == "sk_explicit"

    def test_missing_key_returns_error(self):
        with patch.dict(os.environ, {}, clear=True):
            tool = SaltTool()
            assert tool.create_card(chat_id=1, blocks=[{"type": "divider"}]) == {
                "error": "SALT_API_KEY is required"
            }

    def test_default_api_base(self):
        with patch.dict(os.environ, {}, clear=True):
            tool = SaltTool(api_key="sk_x")
            assert tool.api_base == "https://saltapp.ai/api/v1"

    def test_api_base_override(self):
        with patch.dict(os.environ, {"SALT_API_BASE": "https://staging.saltapp.ai/api/v1/"}, clear=True):
            tool = SaltTool(api_key="sk_x")
            assert tool.api_base == "https://staging.saltapp.ai/api/v1"

    def test_rejects_non_https_api_base(self):
        with patch.dict(os.environ, {}, clear=True):
            try:
                SaltTool(api_key="sk_x", api_base="http://staging.saltapp.ai/api/v1")
                assert False, "expected ValueError for a non-HTTPS api_base"
            except ValueError as e:
                assert "https" in str(e).lower()

    def test_rejects_non_https_api_base_from_env(self):
        with patch.dict(os.environ, {"SALT_API_BASE": "http://example.com"}, clear=True):
            try:
                SaltTool(api_key="sk_x")
                assert False, "expected ValueError for a non-HTTPS SALT_API_BASE"
            except ValueError:
                pass


# ── create_card ──────────────────────────────────────────────────────


class TestCreateCard:
    def test_requires_chat_id(self):
        tool = SaltTool(api_key="sk_x")
        result = tool.create_card(chat_id=None, blocks=[{"type": "divider"}])
        assert result == {"error": "chat_id is required"}

    def test_requires_blocks(self):
        tool = SaltTool(api_key="sk_x")
        result = tool.create_card(chat_id=1, blocks=None)
        assert result == {"error": "blocks is required (at least one block)"}

    def test_posts_card_and_returns_message_payload(self):
        tool = SaltTool(api_key="sk_x")
        blocks = [
            {"type": "section", "text": "Approve?"},
            {"type": "actions", "elements": [
                {"type": "button", "action_id": "approve", "label": "Approve"},
            ]},
        ]
        payload = {"id": 55, "message_id": 900, "resource_id": 42, "resource_type": "Card"}
        with patch("requests.request", return_value=_mock_response(payload)) as req:
            result = tool.create_card(chat_id=123, text="hi", blocks=blocks)

        args, kwargs = req.call_args
        assert args[0] == "post"
        assert args[1].endswith("/cards")
        assert kwargs["headers"]["api-key"] == "sk_x"
        assert kwargs["json"] == {"chat_id": 123, "text": "hi", "state": {"blocks": blocks}}
        assert result["resource_id"] == 42

    def test_propagates_validation_errors(self):
        tool = SaltTool(api_key="sk_x")
        payload = {"errors": ["block 0: unknown type nil"]}
        with patch("requests.request", return_value=_mock_response(payload, status_code=422)):
            result = tool.create_card(chat_id=1, blocks=[{}])
        assert result == {"error": "block 0: unknown type nil"}

    def test_non_list_errors_falls_back_without_crashing(self):
        tool = SaltTool(api_key="sk_x")
        payload = {"errors": {"blocks": ["unknown type nil"]}}
        with patch("requests.request", return_value=_mock_response(payload, status_code=422)):
            result = tool.create_card(chat_id=1, blocks=[{}])
        assert result["error"] == "Salt API returned HTTP 422"
        assert result["details"] == payload


# ── read_card ────────────────────────────────────────────────────────


class TestReadCard:
    def test_requires_card_id(self):
        tool = SaltTool(api_key="sk_x")
        assert tool.read_card(card_id=None) == {"error": "card_id is required"}

    def test_returns_state_and_interactions(self):
        tool = SaltTool(api_key="sk_x")
        payload = {
            "id": 42,
            "state": {"blocks": []},
            "owner_id": 1,
            "interactions": [{"id": 1, "action_id": "approve"}],
        }
        with patch("requests.request", return_value=_mock_response(payload)) as req:
            result = tool.read_card(card_id=42, after="10")

        args, kwargs = req.call_args
        assert args[0] == "get"
        assert args[1].endswith("/cards/42")
        assert kwargs["params"] == {"after": "10"}
        assert result["interactions"][0]["action_id"] == "approve"

    def test_not_found_is_an_error(self):
        tool = SaltTool(api_key="sk_x")
        with patch(
            "requests.request",
            return_value=_mock_response({"error": "Not found"}, status_code=404),
        ):
            result = tool.read_card(card_id=999)
        assert result == {"error": "Not found"}


# ── create_payment_request ──────────────────────────────────────────


class TestCreatePaymentRequest:
    def test_requires_chat_id(self):
        tool = SaltTool(api_key="sk_x")
        result = tool.create_payment_request(
            chat_id=None, wallet_id="w1", receiver_id=2, amount="5.00"
        )
        assert result == {"error": "chat_id is required"}

    def test_requires_wallet_id(self):
        tool = SaltTool(api_key="sk_x")
        result = tool.create_payment_request(
            chat_id=1, wallet_id=None, receiver_id=2, amount="5.00"
        )
        assert result == {"error": "wallet_id is required"}

    def test_requires_receiver_id(self):
        tool = SaltTool(api_key="sk_x")
        result = tool.create_payment_request(
            chat_id=1, wallet_id="w1", receiver_id=None, amount="5.00"
        )
        assert result == {"error": "receiver_id is required"}

    def test_requires_amount(self):
        tool = SaltTool(api_key="sk_x")
        result = tool.create_payment_request(
            chat_id=1, wallet_id="w1", receiver_id=2, amount=None
        )
        assert result == {"error": "amount is required"}

    def test_creates_request(self):
        tool = SaltTool(api_key="sk_x")
        payload = {"id": 77, "amount": "5.00", "status": "pending"}
        with patch("requests.request", return_value=_mock_response(payload)) as req:
            result = tool.create_payment_request(
                chat_id=1, wallet_id="w1", receiver_id=2, amount="5.00", message="thanks"
            )

        args, kwargs = req.call_args
        assert args[0] == "post"
        assert args[1].endswith("/transfer_requests")
        assert kwargs["json"] == {
            "chat_id": 1,
            "wallet_id": "w1",
            "receiver_id": 2,
            "amount": "5.00",
            "message": "thanks",
        }
        assert result["id"] == 77


# ── run() dispatcher ─────────────────────────────────────────────────


class TestRunDispatcher:
    def test_unknown_action(self):
        tool = SaltTool(api_key="sk_x")
        assert tool.run(action="delete_everything") == {"error": "Unknown action: delete_everything"}

    def test_dispatches_create_card(self):
        tool = SaltTool(api_key="sk_x")
        with patch.object(tool, "create_card", return_value={"ok": True}) as m:
            result = tool.run(action="create-card", chat_id=1, blocks=[{"type": "divider"}])
        m.assert_called_once_with(chat_id=1, text=None, blocks=[{"type": "divider"}])
        assert result == {"ok": True}


# ── module-level convenience function ───────────────────────────────


def test_create_salt_card_helper():
    with patch.object(SaltTool, "create_card", return_value={"ok": True}) as m:
        result = create_salt_card(chat_id=1, blocks=[{"type": "divider"}], api_key="sk_x")
    m.assert_called_once_with(chat_id=1, text=None, blocks=[{"type": "divider"}])
    assert result == {"ok": True}
