"""Tool-registry proxy connector implementation.

Three agent-callable functions over a registry's plain-HTTP surface:

- ``registry_search(query)``     free capability search over the catalogue
- ``registry_describe(tool_id)`` free read: params, price-per-call, example
- ``registry_call(tool_id, ...)``paid invoke through the proxy; the registry
  injects the upstream vendor credential server-side.

Design notes:
- ``httpx`` is lazy-imported so the connector adds zero import-time overhead and
  no hard dependency when unconfigured.
- The connector is disabled unless ``TOOL_PROXY_URL`` is set.
- Errors (auth / insufficient balance / upstream 4xx / timeout) are returned as
  ``{"error": ...}`` tool results, never raised as exceptions.
- ``registry_call`` supports optional per-call and per-session spend guards; the
  price is read from ``registry_describe`` and the call is denied + reported when
  a configured budget would be exceeded.
"""

import os
import logging
from typing import Any, Dict, Optional

from praisonai_tools.tools.base import BaseTool
from praisonai_tools.tools.decorator import tool

logger = logging.getLogger(__name__)

_INSTALL_HINT = "httpx not installed. Install with: pip install 'praisonai-tools[registry-proxy]'"

# Cumulative spend is tracked per (proxy_url, token) so that ``max_session_spend``
# persists across the short-lived connector instances created by the decorated
# functions, without mixing budgets across distinct accounts/endpoints.
_SESSION_SPEND: Dict[tuple, float] = {}


class RegistryProxyTool(BaseTool):
    """Connector for a self-hostable tool registry exposing a plain-HTTP proxy."""

    name = "registry_proxy"
    description = (
        "Discover and call third-party API endpoints through a tool registry "
        "proxy; credentials are injected server-side, never held by the agent."
    )

    def __init__(
        self,
        proxy_url: Optional[str] = None,
        token: Optional[str] = None,
        timeout: float = 60.0,
        max_cost_per_call: Optional[float] = None,
        max_session_spend: Optional[float] = None,
    ):
        url_from_env = proxy_url is None
        self.proxy_url = (proxy_url or os.getenv("TOOL_PROXY_URL") or "").rstrip("/")
        # Security: only fall back to the environment token when the URL is also
        # env-derived (trusted config). An agent-supplied ``proxy_url`` must never
        # receive the ambient ``TOOL_PROXY_TOKEN`` - otherwise a prompt-injected
        # agent could exfiltrate the token to an attacker-controlled endpoint.
        if token is not None:
            self.token = token
        elif url_from_env:
            self.token = os.getenv("TOOL_PROXY_TOKEN")
        else:
            self.token = None
        self.timeout = timeout
        self.max_cost_per_call = max_cost_per_call
        self.max_session_spend = max_session_spend
        super().__init__()

    @property
    def _spend_key(self) -> tuple:
        return (self.proxy_url, self.token)

    @property
    def _session_spend(self) -> float:
        return _SESSION_SPEND.get(self._spend_key, 0.0)

    @_session_spend.setter
    def _session_spend(self, value: float) -> None:
        _SESSION_SPEND[self._spend_key] = value

    def run(self, action: str, **kwargs: Any) -> Dict[str, Any]:
        """Dispatch to search/describe/call.

        Args:
            action: One of ``"search"``, ``"describe"`` or ``"call"``.
            **kwargs: Arguments forwarded to the selected operation.
        """
        if action == "search":
            return self.search(kwargs.get("query", ""))
        if action == "describe":
            return self.describe(kwargs.get("tool_id", ""))
        if action == "call":
            return self.call(kwargs.get("tool_id", ""), kwargs.get("params"))
        return {"error": f"Unknown action '{action}'. Use search, describe or call."}

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _require_config(self) -> Optional[Dict[str, Any]]:
        if not self.proxy_url:
            return {
                "error": (
                    "Tool registry proxy is not configured. Set TOOL_PROXY_URL "
                    "(and optionally TOOL_PROXY_TOKEN) to enable the connector."
                )
            }
        return None

    @staticmethod
    def _http_error(exc: Any) -> Dict[str, Any]:
        response = getattr(exc, "response", None)
        status = getattr(response, "status_code", None)
        text = getattr(response, "text", "") if response is not None else str(exc)
        if status == 401 or status == 403:
            return {"error": f"Authentication failed (HTTP {status}): {text}"}
        if status == 402:
            return {"error": f"Insufficient balance (HTTP {status}): {text}"}
        return {"error": f"HTTP {status}: {text}"}

    def search(self, query: str) -> Dict[str, Any]:
        """Search the registry catalogue by capability."""
        missing = self._require_config()
        if missing:
            return missing
        if not query:
            return {"error": "query is required"}
        try:
            import httpx
        except ImportError:
            return {"error": _INSTALL_HINT}
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(
                    f"{self.proxy_url}/catalog/search",
                    params={"q": query},
                    headers=self._headers(),
                )
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException:
            return {"error": f"Registry search timed out after {self.timeout} seconds"}
        except httpx.HTTPStatusError as exc:
            return self._http_error(exc)
        except Exception as exc:  # noqa: BLE001 - surface as tool-result error
            logger.error("registry search error: %s", exc)
            return {"error": str(exc)}

    def describe(self, tool_id: str) -> Dict[str, Any]:
        """Describe one catalogue entry: params, price-per-call, example."""
        missing = self._require_config()
        if missing:
            return missing
        if not tool_id:
            return {"error": "tool_id is required"}
        try:
            import httpx
        except ImportError:
            return {"error": _INSTALL_HINT}
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(
                    f"{self.proxy_url}/catalog/{tool_id}",
                    headers=self._headers(),
                )
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException:
            return {"error": f"Registry describe timed out after {self.timeout} seconds"}
        except httpx.HTTPStatusError as exc:
            return self._http_error(exc)
        except Exception as exc:  # noqa: BLE001 - surface as tool-result error
            logger.error("registry describe error: %s", exc)
            return {"error": str(exc)}

    def _check_budget(self, tool_id: str):
        """Deny + report if a configured spend guard would be exceeded.

        Returns ``(denial, price)``: ``denial`` is a ``{"error": ...}`` dict when
        the call must be rejected (else ``None``); ``price`` is the validated
        per-call price when a guard applies (else ``None``).
        """
        if self.max_cost_per_call is None and self.max_session_spend is None:
            return None, None
        described = self.describe(tool_id)
        if isinstance(described, dict) and "error" in described:
            return described, None
        price = described.get("price_per_call") if isinstance(described, dict) else None
        try:
            price = float(price)
        except (TypeError, ValueError):
            # Fail closed: a spend guard is configured but the price cannot be
            # validated, so we cannot guarantee the budget - deny the call.
            return {
                "error": (
                    "Denied: price_per_call is missing or invalid, cannot enforce "
                    "the configured spend guard."
                )
            }, None
        if self.max_cost_per_call is not None and price > self.max_cost_per_call:
            return {
                "error": (
                    f"Denied: price per call {price} exceeds max_cost_per_call "
                    f"{self.max_cost_per_call}."
                )
            }, price
        if (
            self.max_session_spend is not None
            and self._session_spend + price > self.max_session_spend
        ):
            return {
                "error": (
                    f"Denied: session spend would reach "
                    f"{self._session_spend + price}, exceeding max_session_spend "
                    f"{self.max_session_spend}."
                )
            }, price
        return None, price

    def call(self, tool_id: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Invoke an endpoint through the proxy (credential injected server-side)."""
        missing = self._require_config()
        if missing:
            return missing
        if not tool_id:
            return {"error": "tool_id is required"}
        denied, quoted_price = self._check_budget(tool_id)
        if denied:
            return denied
        try:
            import httpx
        except ImportError:
            return {"error": _INSTALL_HINT}
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.proxy_url}/call/{tool_id}",
                    json=params or {},
                    headers=self._headers(),
                )
                response.raise_for_status()
                result = response.json()
        except httpx.TimeoutException:
            return {"error": f"Registry call timed out after {self.timeout} seconds"}
        except httpx.HTTPStatusError as exc:
            return self._http_error(exc)
        except Exception as exc:  # noqa: BLE001 - surface as tool-result error
            logger.error("registry call error: %s", exc)
            return {"error": str(exc)}

        # Record cumulative spend. Prefer the charge reported by the proxy; fall
        # back to the price quoted at budget-check time so the session budget
        # still accrues when the response omits cost fields.
        charged = None
        if isinstance(result, dict):
            charged = result.get("price_per_call", result.get("cost"))
        try:
            self._session_spend += float(charged)
        except (TypeError, ValueError):
            if quoted_price is not None:
                self._session_spend += quoted_price
        return result


@tool
def registry_search(
    query: str,
    proxy_url: Optional[str] = None,
    token: Optional[str] = None,
) -> Dict[str, Any]:
    """Search the connected tool registry by capability.

    Free read. Returns catalogue matches for a natural-language capability query
    such as "backlinks for a domain" or "company enrichment by email".

    Args:
        query: Capability to search for.
        proxy_url: Registry base URL (defaults to TOOL_PROXY_URL env var).
        token: Proxy token (defaults to TOOL_PROXY_TOKEN env var).

    Returns:
        Dict with catalogue matches, or ``{"error": ...}`` on failure.
    """
    return RegistryProxyTool(proxy_url=proxy_url, token=token).search(query)


@tool
def registry_describe(
    tool_id: str,
    proxy_url: Optional[str] = None,
    token: Optional[str] = None,
) -> Dict[str, Any]:
    """Describe one registry catalogue entry.

    Free read. Returns the endpoint's parameters, price-per-call and an example
    response so the model can decide whether and how to invoke it.

    Args:
        tool_id: Catalogue entry identifier (from ``registry_search``).
        proxy_url: Registry base URL (defaults to TOOL_PROXY_URL env var).
        token: Proxy token (defaults to TOOL_PROXY_TOKEN env var).

    Returns:
        Dict describing the entry, or ``{"error": ...}`` on failure.
    """
    return RegistryProxyTool(proxy_url=proxy_url, token=token).describe(tool_id)


@tool
def registry_call(
    tool_id: str,
    params: Optional[Dict[str, Any]] = None,
    proxy_url: Optional[str] = None,
    token: Optional[str] = None,
    max_cost_per_call: Optional[float] = None,
    max_session_spend: Optional[float] = None,
) -> Dict[str, Any]:
    """Invoke a registry endpoint through the proxy.

    Paid call. The registry injects the upstream vendor credential server-side,
    so no vendor keys are ever held by the agent. Optional spend guards deny +
    report the call when a configured budget would be exceeded.

    Args:
        tool_id: Catalogue entry identifier (from ``registry_search``).
        params: Parameters for the upstream endpoint.
        proxy_url: Registry base URL (defaults to TOOL_PROXY_URL env var).
        token: Proxy token (defaults to TOOL_PROXY_TOKEN env var).
        max_cost_per_call: Deny the call if its price exceeds this value.
        max_session_spend: Deny the call if it would push cumulative spend past this value.

    Returns:
        Dict with the endpoint response, or ``{"error": ...}`` on failure/denial.
    """
    return RegistryProxyTool(
        proxy_url=proxy_url,
        token=token,
        max_cost_per_call=max_cost_per_call,
        max_session_spend=max_session_spend,
    ).call(tool_id, params)
