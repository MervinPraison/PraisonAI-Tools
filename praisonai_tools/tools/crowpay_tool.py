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
    ) -> Union[str, Dict[str, Any]]:
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

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def setup(self) -> Dict[str, Any]:
        """Create an agent wallet."""
        err = self._require_key()
        if err:
            return err

        requests = self._import_requests()
        if requests is None:
            return {"error": "requests package is not installed"}

        try:
            resp = requests.post(
                f"{API_BASE}/v1/setup",
                headers=self._headers(),
                json={},
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error("CrowPay setup error: %s", e)
            return {"error": str(e)}

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
        err = self._require_key()
        if err:
            return err
        if not payment_required:
            return {"error": "payment_required is required"}

        requests = self._import_requests()
        if requests is None:
            return {"error": "requests package is not installed"}

        payload: Dict[str, Any] = {"paymentRequired": payment_required}
        if merchant:
            payload["merchant"] = merchant
        if reason:
            payload["reason"] = reason

        try:
            resp = requests.post(
                f"{API_BASE}/v1/authorize",
                headers=self._headers(),
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error("CrowPay authorize error: %s", e)
            return {"error": str(e)}

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
        err = self._require_key()
        if err:
            return err
        if not amount or not currency:
            return {"error": "amount and currency are required"}

        requests = self._import_requests()
        if requests is None:
            return {"error": "requests package is not installed"}

        payload: Dict[str, Any] = {"amount": amount, "currency": currency}
        if merchant:
            payload["merchant"] = merchant
        if reason:
            payload["reason"] = reason

        try:
            resp = requests.post(
                f"{API_BASE}/v1/authorize/card",
                headers=self._headers(),
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error("CrowPay authorize_card error: %s", e)
            return {"error": str(e)}

    def poll_status(self, approval_id: Optional[str] = None) -> Dict[str, Any]:
        """Poll the status of a pending approval.

        Args:
            approval_id: The approval identifier to check.
        """
        err = self._require_key()
        if err:
            return err
        if not approval_id:
            return {"error": "approval_id is required"}

        requests = self._import_requests()
        if requests is None:
            return {"error": "requests package is not installed"}

        try:
            from urllib.parse import quote
            resp = requests.get(
                f"{API_BASE}/v1/approvals/{quote(approval_id, safe='')}",
                headers=self._headers(),
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error("CrowPay poll_status error: %s", e)
            return {"error": str(e)}

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
        err = self._require_key()
        if err:
            return err
        if not transaction_id:
            return {"error": "transaction_id is required"}

        requests = self._import_requests()
        if requests is None:
            return {"error": "requests package is not installed"}

        payload: Dict[str, Any] = {"transactionId": transaction_id}
        if tx_hash:
            payload["txHash"] = tx_hash

        try:
            resp = requests.post(
                f"{API_BASE}/v1/settle",
                headers=self._headers(),
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error("CrowPay settle error: %s", e)
            return {"error": str(e)}


def crowpay_setup(api_key: Optional[str] = None) -> Dict[str, Any]:
    """Create an agent wallet."""
    return CrowPayTool(api_key=api_key).setup()
