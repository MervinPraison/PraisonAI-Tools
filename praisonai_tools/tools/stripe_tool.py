"""Stripe Tool for PraisonAI Agents.

Narrow, audited Stripe operations — retrieve customers/payment intents,
list payment links, and create payment links with required correlation
metadata and optional idempotency keys.

Design constraint: prefer narrow, audited operations over a "god tool"
that dumps the entire Stripe surface. One verb per action.

Usage:
    from praisonai_tools import StripeTool

    stripe = StripeTool()  # reads STRIPE_SECRET_KEY (or STRIPE_API_KEY)
    customer = stripe.run(action="get_customer", customer_id="cus_123")
    link = stripe.run(
        action="create_payment_link",
        price_id="price_123",
        quantity=1,
        correlation_id="order-42",
    )

Environment Variables:
    STRIPE_SECRET_KEY: Stripe secret key. Restricted keys are recommended.
        Accepts test (``sk_test_``/``rk_test_``) or live
        (``sk_live_``/``rk_live_``) keys. STRIPE_API_KEY is also accepted
        as a fallback.

Security notes:
    * Secrets are read from the environment only and never logged.
    * Responses include a ``mode`` banner (``test``/``live``) derived from
      the key prefix so live operations are visible to callers.
    * Structured logs record only the operation, mode, idempotency key, and
      the Stripe object id — never full request/response payloads.
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)

API_BASE = "https://api.stripe.com/v1"

_TEST_PREFIXES = ("sk_test_", "rk_test_")
_LIVE_PREFIXES = ("sk_live_", "rk_live_")


class StripeTool(BaseTool):
    """Tool for narrow, audited Stripe operations."""

    name = "stripe"
    description = (
        "Retrieve Stripe customers and payment intents, list payment links, "
        "and create payment links with required correlation metadata."
    )

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = (
            api_key
            or os.getenv("STRIPE_SECRET_KEY")
            or os.getenv("STRIPE_API_KEY")
        )
        super().__init__()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _mode(self) -> str:
        """Return ``test``, ``live``, or ``unknown`` from the key prefix."""
        key = self.api_key or ""
        if key.startswith(_LIVE_PREFIXES):
            return "live"
        if key.startswith(_TEST_PREFIXES):
            return "test"
        return "unknown"

    def _require_key(self) -> Optional[Dict[str, str]]:
        if not self.api_key:
            return {"error": "STRIPE_SECRET_KEY (or STRIPE_API_KEY) is required"}
        return None

    @staticmethod
    def _import_requests():
        try:
            import requests
            return requests
        except ImportError:
            return None

    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Make a request to the Stripe REST API.

        Centralises key validation, the optional ``requests`` import, the
        HTTP call, auditable logging, and error handling.
        """
        err = self._require_key()
        if err:
            return err

        requests = self._import_requests()
        if requests is None:
            return {"error": "requests package is not installed"}

        headers = {"Authorization": f"Bearer {self.api_key}"}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        try:
            resp = requests.request(
                method,
                f"{API_BASE}/{endpoint}",
                headers=headers,
                data=data,
                timeout=30,
            )
            body = resp.json()
        except requests.exceptions.RequestException as e:
            logger.error("Stripe request error: %s", e)
            return {"error": f"API request failed: {e}"}
        except ValueError as e:
            logger.error("Stripe JSON decode error: %s", e)
            return {"error": "Failed to decode API response"}

        if isinstance(body, dict) and "error" in body:
            stripe_err = body["error"]
            message = stripe_err.get("message", "Stripe API error")
            logger.error(
                "Stripe API error: op=%s mode=%s type=%s",
                endpoint, self._mode(), stripe_err.get("type"),
            )
            return {"error": message}

        obj_id = body.get("id") if isinstance(body, dict) else None
        logger.info(
            "Stripe op=%s mode=%s idempotency_key=%s object_id=%s",
            endpoint, self._mode(), idempotency_key, obj_id,
        )
        return body

    def _banner(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Attach a live/test mode banner to a successful response."""
        if isinstance(payload, dict) and "error" not in payload:
            payload = {"mode": self._mode(), **payload}
        return payload

    # ------------------------------------------------------------------
    # Dispatcher
    # ------------------------------------------------------------------

    def run(
        self,
        action: str = "get_customer",
        customer_id: Optional[str] = None,
        payment_intent_id: Optional[str] = None,
        price_id: Optional[str] = None,
        quantity: int = 1,
        correlation_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        limit: int = 10,
        **kwargs,
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """Dispatch to the appropriate Stripe action.

        Actions:
            get_customer         — Retrieve a customer by id (read).
            get_payment_intent   — Retrieve a payment intent by id (read).
            list_payment_links   — List payment links (read).
            create_payment_link  — Create a payment link (write, guarded).
        """
        action = action.lower().replace("-", "_")

        if action == "get_customer":
            return self.get_customer(customer_id=customer_id)
        elif action == "get_payment_intent":
            return self.get_payment_intent(payment_intent_id=payment_intent_id)
        elif action == "list_payment_links":
            return self.list_payment_links(limit=limit)
        elif action == "create_payment_link":
            return self.create_payment_link(
                price_id=price_id,
                quantity=quantity,
                correlation_id=correlation_id,
                idempotency_key=idempotency_key,
            )
        else:
            return {"error": f"Unknown action: {action}"}

    # ------------------------------------------------------------------
    # Phase 1 — Read-mostly safety
    # ------------------------------------------------------------------

    def get_customer(self, customer_id: Optional[str] = None) -> Dict[str, Any]:
        """Retrieve a customer by id.

        Args:
            customer_id: The Stripe customer id (``cus_...``).
        """
        if not customer_id:
            return {"error": "customer_id is required"}

        result = self._request("get", f"customers/{customer_id}")
        if "error" in result:
            return result

        return self._banner({
            "id": result.get("id"),
            "email": result.get("email"),
            "name": result.get("name"),
            "created": result.get("created"),
            "currency": result.get("currency"),
            "delinquent": result.get("delinquent"),
        })

    def get_payment_intent(
        self, payment_intent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Retrieve a payment intent by id.

        Args:
            payment_intent_id: The Stripe payment intent id (``pi_...``).
        """
        if not payment_intent_id:
            return {"error": "payment_intent_id is required"}

        result = self._request("get", f"payment_intents/{payment_intent_id}")
        if "error" in result:
            return result

        return self._banner({
            "id": result.get("id"),
            "amount": result.get("amount"),
            "currency": result.get("currency"),
            "status": result.get("status"),
            "customer": result.get("customer"),
            "created": result.get("created"),
        })

    def list_payment_links(self, limit: int = 10) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """List payment links.

        Args:
            limit: Maximum number of payment links to return (1–100).
        """
        limit = max(1, min(int(limit), 100))
        result = self._request("get", f"payment_links?limit={limit}")
        if "error" in result:
            return result

        links = [
            {
                "id": link.get("id"),
                "url": link.get("url"),
                "active": link.get("active"),
                "metadata": link.get("metadata", {}),
            }
            for link in result.get("data", [])
        ]
        return self._banner({"mode": self._mode(), "payment_links": links})

    # ------------------------------------------------------------------
    # Phase 2 — Mutations with guardrails
    # ------------------------------------------------------------------

    def create_payment_link(
        self,
        price_id: Optional[str] = None,
        quantity: int = 1,
        correlation_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a payment link.

        A ``correlation_id`` is required and stored as payment-link metadata
        so every created link is traceable back to the request that made it.
        An optional ``idempotency_key`` is surfaced to make retries safe.

        Args:
            price_id: An existing Stripe Price id (``price_...``).
            quantity: Quantity for the line item (>= 1).
            correlation_id: Required correlation id stored as metadata.
            idempotency_key: Optional Stripe ``Idempotency-Key`` header value.
        """
        if not price_id:
            return {"error": "price_id is required"}
        if not correlation_id:
            return {"error": "correlation_id is required (stored as metadata)"}
        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            return {"error": "quantity must be an integer"}
        if quantity < 1:
            return {"error": "quantity must be >= 1"}

        data = {
            "line_items[0][price]": price_id,
            "line_items[0][quantity]": quantity,
            "metadata[correlation_id]": correlation_id,
        }
        result = self._request(
            "post",
            "payment_links",
            data=data,
            idempotency_key=idempotency_key,
        )
        if "error" in result:
            return result

        return self._banner({
            "id": result.get("id"),
            "url": result.get("url"),
            "active": result.get("active"),
            "metadata": result.get("metadata", {}),
        })


def get_stripe_customer(
    customer_id: str, api_key: Optional[str] = None
) -> Dict[str, Any]:
    """Retrieve a Stripe customer by id."""
    return StripeTool(api_key=api_key).get_customer(customer_id=customer_id)
