"""CrowPay Tool for PraisonAI Agents.

AI agent payments via CrowPay — wallet setup, x402 payment authorization,
credit card payments, approval polling, and settlement reporting.

Usage:
    from praisonai_tools import CrowPayTool

    tool = CrowPayTool()
    wallet = tool.run(action="setup")
    result = tool.run(action="authorize", payment_required="x402-header-value",
                      merchant="merchant-id", reason="Access premium API")

Environment Variables:
    CROWPAY_API_KEY: CrowPay API key (https://crowpay.ai)
"""

import os
import logging
from typing import Any, Dict, Optional, Union
from urllib.parse import quote

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)

API_BASE = "https://api.crowpay.ai"


class CrowPayTool(BaseTool):
    """Tool for AI agent payments via CrowPay."""

    name = "crowpay"
    description = (
        "Handle AI agent payments — wallet setup, x402 payment authorization, "
        "credit card payments, approval polling, and settlement."
    )

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("CROWPAY_API_KEY")
        super().__init__()

    def run(
        self,
        action: str = "setup",
        payment_required: Optional[str] = None,
        merchant: Optional[str] = None,
        reason: Optional[str] = None,
        amount: Optional[str] = None,
        currency: Optional[str] = None,
        approval_id: Optional[str] = None,
        transaction_id: Optional[str] = None,
        tx_hash: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Dispatch to the appropriate CrowPay action.

        Actions:
            setup            — Create an agent wallet.
            authorize        — Authorize an x402 payment.
            authorize_card   — Authorize a credit card payment.
            poll_status      — Poll status of a pending approval.
            settle           — Report settlement of a transaction.
        """
        action = action.lower().replace("-", "_")

        if action == "setup":
            return self.setup()
        elif action == "authorize":
            return self.authorize(
                payment_required=payment_required,
                merchant=merchant,
                reason=reason,
            )
        elif action == "authorize_card":
            return self.authorize_card(
                amount=amount,
                currency=currency,
                merchant=merchant,
                reason=reason,
            )
        elif action == "poll_status":
            return self.poll_status(approval_id=approval_id)
        elif action == "settle":
            return self.settle(transaction_id=transaction_id, tx_hash=tx_hash)
        else:
            return {"error": f"Unknown action: {action}"}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _require_key(self) -> Optional[Dict[str, str]]:
        if not self.api_key:
            return {"error": "CROWPAY_API_KEY is required"}
        return None

    @staticmethod
    def _import_requests():
        try:
            import requests
            return requests
        except ImportError:
            return None

    def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """Make a request to the CrowPay API.

        Centralizes key validation, requests import, HTTP call, and
        error handling for all action methods.
        """
        err = self._require_key()
        if err:
            return err

        requests = self._import_requests()
        if requests is None:
            return {"error": "requests package is not installed"}

        try:
            resp = requests.request(
                method,
                f"{API_BASE}/v1/{endpoint}",
                headers=self._headers(),
                **kwargs,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            logger.error("CrowPay request error: %s", e)
            return {"error": f"API request failed: {e}"}
        except ValueError as e:
            logger.error("CrowPay JSON decode error: %s", e)
            return {"error": f"Failed to decode API response: {e}"}

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def setup(self) -> Dict[str, Any]:
        """Create an agent wallet."""
        return self._make_request("post", "setup", json={}, timeout=30)

    def authorize(
        self,
        payment_required: Optional[str] = None,
        merchant: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Authorize an x402 payment.

        Args:
            payment_required: The ``X-Payment-Required`` or ``402`` header
                value returned by the upstream service.
            merchant: Merchant identifier.
            reason: Human-readable reason for the payment.
        """
        if not payment_required:
            return {"error": "payment_required is required"}

        payload: Dict[str, Any] = {"paymentRequired": payment_required}
        if merchant:
            payload["merchant"] = merchant
        if reason:
            payload["reason"] = reason

        return self._make_request("post", "authorize", json=payload, timeout=30)

    def authorize_card(
        self,
        amount: Optional[str] = None,
        currency: Optional[str] = None,
        merchant: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Authorize a credit card payment.

        Args:
            amount: Payment amount (e.g. ``"9.99"``).
            currency: ISO 4217 currency code (e.g. ``"USD"``).
            merchant: Merchant identifier.
            reason: Human-readable reason for the payment.
        """
        if not amount or not currency:
            return {"error": "amount and currency are required"}

        payload: Dict[str, Any] = {"amount": amount, "currency": currency}
        if merchant:
            payload["merchant"] = merchant
        if reason:
            payload["reason"] = reason

        return self._make_request("post", "authorize/card", json=payload, timeout=30)

    def poll_status(self, approval_id: Optional[str] = None) -> Dict[str, Any]:
        """Poll the status of a pending approval.

        Args:
            approval_id: The approval identifier to check.
        """
        if not approval_id:
            return {"error": "approval_id is required"}

        return self._make_request(
            "get",
            f"approvals/{quote(approval_id, safe='')}",
            timeout=15,
        )

    def settle(
        self,
        transaction_id: Optional[str] = None,
        tx_hash: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Report settlement of a transaction.

        Args:
            transaction_id: The CrowPay transaction identifier.
            tx_hash: The on-chain transaction hash.
        """
        if not transaction_id:
            return {"error": "transaction_id is required"}

        payload: Dict[str, Any] = {"transactionId": transaction_id}
        if tx_hash:
            payload["txHash"] = tx_hash

        return self._make_request("post", "settle", json=payload, timeout=30)


def crowpay_setup(api_key: Optional[str] = None) -> Dict[str, Any]:
    """Create an agent wallet."""
    return CrowPayTool(api_key=api_key).setup()
