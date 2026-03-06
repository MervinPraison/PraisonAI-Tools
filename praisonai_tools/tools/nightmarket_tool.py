"""Nightmarket Tool for PraisonAI Agents.

Discover and call API services on the Nightmarket marketplace. Optionally
integrates with CrowPay for automatic x402 payment handling.

Usage:
    from praisonai_tools import NightmarketTool

    tool = NightmarketTool()
    results = tool.run(action="search", query="weather API")
    details = tool.run(action="get_service", endpoint_id="ep_abc123")
    response = tool.run(action="call_service", endpoint_id="ep_abc123",
                        method="GET", body=None)

Environment Variables:
    CROWPAY_API_KEY: (Optional) CrowPay API key for automatic x402 payments.
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)

API_BASE = "https://nightmarket.ai/api"


class NightmarketTool(BaseTool):
    """Tool for discovering and calling APIs on Nightmarket."""

    name = "nightmarket"
    description = (
        "Search the Nightmarket marketplace for API services, get service "
        "details, and call services with optional automatic x402 payment "
        "via CrowPay."
    )

    def __init__(self, crowpay_api_key: Optional[str] = None):
        self.crowpay_api_key = crowpay_api_key or os.getenv("CROWPAY_API_KEY")
        super().__init__()

    def run(
        self,
        action: str = "search",
        query: Optional[str] = None,
        sort: Optional[str] = None,
        endpoint_id: Optional[str] = None,
        method: Optional[str] = None,
        body: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """Dispatch to the appropriate Nightmarket action.

        Actions:
            search       — Search the marketplace for services.
            get_service  — Get details about a specific service.
            call_service — Call an API service (handles 402 with CrowPay).
        """
        action = action.lower().replace("-", "_")

        if action == "search":
            return self.search(query=query, sort=sort)
        elif action == "get_service":
            return self.get_service(endpoint_id=endpoint_id)
        elif action == "call_service":
            return self.call_service(
                endpoint_id=endpoint_id,
                method=method,
                body=body,
                headers=headers,
            )
        else:
            return {"error": f"Unknown action: {action}"}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

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

    def search(
        self,
        query: Optional[str] = None,
        sort: Optional[str] = None,
    ) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """Search the Nightmarket marketplace.

        Args:
            query: Search query string.
            sort: Sort order (e.g. ``"popular"``, ``"recent"``).
        """
        if not query:
            return {"error": "query is required"}

        requests = self._import_requests()
        if requests is None:
            return {"error": "requests package is not installed"}

        try:
            from urllib.parse import quote
            params: Dict[str, str] = {"q": query}
            if sort:
                params["sort"] = sort

            resp = requests.get(
                f"{API_BASE}/v1/search",
                params=params,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            results = []
            for item in data.get("results", data.get("services", [])):
                results.append({
                    "endpoint_id": item.get("endpointId") or item.get("id"),
                    "name": item.get("name"),
                    "description": item.get("description"),
                    "pricing": item.get("pricing"),
                    "url": item.get("url"),
                })
            return results
        except (requests.exceptions.RequestException, ValueError) as e:
            logger.error("Nightmarket search error: %s", e)
            return {"error": str(e)}

    def get_service(
        self,
        endpoint_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get details about a specific service.

        Args:
            endpoint_id: The endpoint / service identifier.
        """
        if not endpoint_id:
            return {"error": "endpoint_id is required"}

        requests = self._import_requests()
        if requests is None:
            return {"error": "requests package is not installed"}

        try:
            from urllib.parse import quote
            resp = requests.get(
                f"{API_BASE}/v1/services/{quote(endpoint_id, safe='')}",
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error("Nightmarket get_service error: %s", e)
            return {"error": str(e)}

    def call_service(
        self,
        endpoint_id: Optional[str] = None,
        method: Optional[str] = None,
        body: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Call an API service on Nightmarket.

        If the service returns HTTP 402 and a ``CROWPAY_API_KEY`` is
        configured, the tool will automatically authorize the payment
        via CrowPay and retry the request.

        Args:
            endpoint_id: The endpoint / service identifier.
            method: HTTP method (default ``"GET"``).
            body: Request body (for POST/PUT/PATCH).
            headers: Additional request headers.
        """
        if not endpoint_id:
            return {"error": "endpoint_id is required"}

        requests_lib = self._import_requests()
        if requests_lib is None:
            return {"error": "requests package is not installed"}

        method = (method or "GET").upper()
        req_headers: Dict[str, str] = {"Content-Type": "application/json"}
        if headers:
            req_headers.update(headers)

        try:
            from urllib.parse import quote

            url = f"{API_BASE}/v1/services/{quote(endpoint_id, safe='')}/call"

            request_kwargs: Dict[str, Any] = {
                "method": method,
                "url": url,
                "headers": req_headers,
                "timeout": 60,
            }
            if body is not None and method in ("POST", "PUT", "PATCH"):
                request_kwargs["json"] = body

            resp = requests_lib.request(**request_kwargs)

            # Handle x402 payment flow
            if resp.status_code == 402 and self.crowpay_api_key:
                logger.info("Received 402 — attempting CrowPay authorization")
                payment_header = (
                    resp.headers.get("X-Payment-Required")
                    or resp.headers.get("X-Payment")
                    or resp.text
                )
                auth_result = self._authorize_payment(
                    requests_lib, payment_header, endpoint_id
                )
                if "error" in auth_result:
                    return auth_result

                # Attach payment token and retry
                payment_token = auth_result.get("token") or auth_result.get(
                    "paymentToken"
                )
                if payment_token:
                    req_headers["X-Payment"] = payment_token
                    request_kwargs["headers"] = req_headers
                    resp = requests_lib.request(**request_kwargs)

            resp.raise_for_status()
            try:
                return resp.json()
            except ValueError:
                return {"response": resp.text}

        except Exception as e:
            logger.error("Nightmarket call_service error: %s", e)
            return {"error": str(e)}

    def _authorize_payment(
        self,
        requests_lib: Any,
        payment_required: str,
        merchant: str,
    ) -> Dict[str, Any]:
        """Authorize a payment via CrowPay for a 402 response."""
        try:
            resp = requests_lib.post(
                "https://api.crowpay.ai/v1/authorize",
                headers={
                    "Authorization": f"Bearer {self.crowpay_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "paymentRequired": payment_required,
                    "merchant": merchant,
                    "reason": f"Nightmarket service call: {merchant}",
                },
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error("CrowPay authorization failed: %s", e)
            return {"error": f"CrowPay authorization failed: {e}"}


def nightmarket_search(
    query: str, sort: Optional[str] = None
) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    """Search the Nightmarket marketplace."""
    return NightmarketTool().search(query=query, sort=sort)
