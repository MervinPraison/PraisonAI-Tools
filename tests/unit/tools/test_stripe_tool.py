"""Unit tests for StripeTool."""

import os
from unittest.mock import MagicMock, patch

from praisonai_tools.tools.stripe_tool import StripeTool, get_stripe_customer


def _mock_response(payload):
    resp = MagicMock()
    resp.json.return_value = payload
    return resp


# ── Key handling / mode banner ──────────────────────────────────────


class TestKeyAndMode:
    def test_env_secret_key_fallback(self):
        with patch.dict(os.environ, {"STRIPE_SECRET_KEY": "sk_test_x"}, clear=True):
            tool = StripeTool()
            assert tool.api_key == "sk_test_x"
            assert tool._mode() == "test"

    def test_stripe_api_key_fallback(self):
        with patch.dict(os.environ, {"STRIPE_API_KEY": "sk_live_x"}, clear=True):
            tool = StripeTool()
            assert tool.api_key == "sk_live_x"
            assert tool._mode() == "live"

    def test_restricted_key_prefixes(self):
        assert StripeTool(api_key="rk_test_x")._mode() == "test"
        assert StripeTool(api_key="rk_live_x")._mode() == "live"

    def test_unknown_mode(self):
        assert StripeTool(api_key="weird")._mode() == "unknown"

    def test_missing_key_returns_error(self):
        with patch.dict(os.environ, {}, clear=True):
            tool = StripeTool()
            assert tool.get_customer(customer_id="cus_1") == {
                "error": "STRIPE_SECRET_KEY (or STRIPE_API_KEY) is required"
            }


# ── get_customer ────────────────────────────────────────────────────


class TestGetCustomer:
    def test_requires_customer_id(self):
        tool = StripeTool(api_key="sk_test_x")
        assert tool.get_customer(customer_id="") == {"error": "customer_id is required"}

    def test_returns_normalised_customer_with_banner(self):
        tool = StripeTool(api_key="sk_test_x")
        payload = {
            "id": "cus_1",
            "email": "a@b.com",
            "name": "Alice",
            "created": 123,
            "currency": "usd",
            "delinquent": False,
        }
        with patch("requests.request", return_value=_mock_response(payload)) as req:
            result = tool.get_customer(customer_id="cus_1")

        args, kwargs = req.call_args
        assert args[0] == "get"
        assert args[1].endswith("/customers/cus_1")
        assert kwargs["headers"]["Authorization"] == "Bearer sk_test_x"
        assert result["mode"] == "test"
        assert result["id"] == "cus_1"
        assert result["email"] == "a@b.com"

    def test_propagates_stripe_error(self):
        tool = StripeTool(api_key="sk_test_x")
        payload = {"error": {"message": "No such customer", "type": "invalid_request_error"}}
        with patch("requests.request", return_value=_mock_response(payload)):
            assert tool.get_customer(customer_id="cus_x") == {"error": "No such customer"}

    def test_handles_request_exception(self):
        import requests

        tool = StripeTool(api_key="sk_test_x")
        with patch(
            "requests.request",
            side_effect=requests.exceptions.RequestException("boom"),
        ):
            result = tool.get_customer(customer_id="cus_1")
        assert result["error"].startswith("API request failed")


# ── get_payment_intent ──────────────────────────────────────────────


class TestGetPaymentIntent:
    def test_requires_id(self):
        tool = StripeTool(api_key="sk_test_x")
        assert tool.get_payment_intent(payment_intent_id="") == {
            "error": "payment_intent_id is required"
        }

    def test_returns_normalised_intent(self):
        tool = StripeTool(api_key="sk_test_x")
        payload = {
            "id": "pi_1",
            "amount": 500,
            "currency": "usd",
            "status": "succeeded",
            "customer": "cus_1",
            "created": 1,
        }
        with patch("requests.request", return_value=_mock_response(payload)):
            result = tool.get_payment_intent(payment_intent_id="pi_1")
        assert result["status"] == "succeeded"
        assert result["amount"] == 500
        assert result["mode"] == "test"


# ── list_payment_links ──────────────────────────────────────────────


class TestListPaymentLinks:
    def test_returns_links(self):
        tool = StripeTool(api_key="sk_test_x")
        payload = {
            "data": [
                {"id": "plink_1", "url": "https://pay/1", "active": True, "metadata": {}},
                {"id": "plink_2", "url": "https://pay/2", "active": False, "metadata": {}},
            ]
        }
        with patch("requests.request", return_value=_mock_response(payload)):
            result = tool.list_payment_links(limit=2)
        assert result["mode"] == "test"
        assert len(result["payment_links"]) == 2
        assert result["payment_links"][0]["id"] == "plink_1"

    def test_clamps_limit(self):
        tool = StripeTool(api_key="sk_test_x")
        with patch("requests.request", return_value=_mock_response({"data": []})) as req:
            tool.list_payment_links(limit=999)
        assert "limit=100" in req.call_args[0][1]

    def test_propagates_error(self):
        tool = StripeTool(api_key="sk_test_x")
        payload = {"error": {"message": "bad"}}
        with patch("requests.request", return_value=_mock_response(payload)):
            assert tool.list_payment_links() == {"error": "bad"}


# ── create_payment_link (guardrails) ────────────────────────────────


class TestCreatePaymentLink:
    def test_requires_price_id(self):
        tool = StripeTool(api_key="sk_test_x")
        assert tool.create_payment_link(
            price_id="", correlation_id="c1"
        ) == {"error": "price_id is required"}

    def test_requires_correlation_id(self):
        tool = StripeTool(api_key="sk_test_x")
        assert tool.create_payment_link(price_id="price_1") == {
            "error": "correlation_id is required (stored as metadata)"
        }

    def test_rejects_bad_quantity(self):
        tool = StripeTool(api_key="sk_test_x")
        assert tool.create_payment_link(
            price_id="price_1", correlation_id="c1", quantity=0
        ) == {"error": "quantity must be >= 1"}

    def test_success_sends_metadata_and_idempotency_key(self):
        tool = StripeTool(api_key="sk_test_x")
        payload = {
            "id": "plink_1",
            "url": "https://pay/1",
            "active": True,
            "metadata": {"correlation_id": "order-42"},
        }
        with patch("requests.request", return_value=_mock_response(payload)) as req:
            result = tool.create_payment_link(
                price_id="price_1",
                quantity=2,
                correlation_id="order-42",
                idempotency_key="idem-1",
            )

        args, kwargs = req.call_args
        assert args[0] == "post"
        assert args[1].endswith("/payment_links")
        assert kwargs["data"]["line_items[0][price]"] == "price_1"
        assert kwargs["data"]["line_items[0][quantity]"] == 2
        assert kwargs["data"]["metadata[correlation_id]"] == "order-42"
        assert kwargs["headers"]["Idempotency-Key"] == "idem-1"
        assert result["id"] == "plink_1"
        assert result["mode"] == "test"


# ── run() dispatcher ────────────────────────────────────────────────


class TestRunDispatcher:
    def test_unknown_action(self):
        tool = StripeTool(api_key="sk_test_x")
        assert tool.run(action="bogus") == {"error": "Unknown action: bogus"}

    def test_routes_get_customer(self):
        tool = StripeTool(api_key="sk_test_x")
        with patch.object(tool, "get_customer", return_value={"ok": True}) as m:
            tool.run(action="get_customer", customer_id="cus_1")
        m.assert_called_once_with(customer_id="cus_1")

    def test_routes_create_payment_link(self):
        tool = StripeTool(api_key="sk_test_x")
        with patch.object(tool, "create_payment_link", return_value={"ok": True}) as m:
            tool.run(
                action="create-payment-link",
                price_id="price_1",
                quantity=1,
                correlation_id="c1",
                idempotency_key="i1",
            )
        m.assert_called_once_with(
            price_id="price_1", quantity=1, correlation_id="c1", idempotency_key="i1"
        )


# ── Module-level helper ─────────────────────────────────────────────


class TestHelper:
    def test_delegates_to_tool(self):
        with patch.object(StripeTool, "get_customer", return_value={"id": "cus_1"}) as m:
            assert get_stripe_customer("cus_1", api_key="sk_test_x") == {"id": "cus_1"}
        m.assert_called_once_with(customer_id="cus_1")
