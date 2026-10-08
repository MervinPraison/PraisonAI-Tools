"""Keenable Search Tool for PraisonAI Agents.

Keyless (or keyed) web search using Keenable.

Keenable works with no API key and no extra install: it calls the keyless
public endpoint with the Python standard library (``urllib``). Setting
``KEENABLE_API_KEY`` switches to the authenticated endpoint for higher limits.

Usage:
    from praisonai_tools import KeenableSearchTool

    keenable = KeenableSearchTool()
    results = keenable.search("AI news 2024")

Environment Variables:
    KEENABLE_API_KEY: Optional. When set, the authenticated endpoint is used.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional, Union
from urllib.request import HTTPRedirectHandler

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)

KEENABLE_SEARCH_URL = "https://api.keenable.ai/v1/search"
KEENABLE_PUBLIC_SEARCH_URL = "https://api.keenable.ai/v1/search/public"
KEENABLE_APP_TITLE = "PraisonAI"
KEENABLE_SEARCH_TIMEOUT_SECONDS = 30
KEENABLE_MAX_RESPONSE_BYTES = 1_000_000
KEENABLE_MAX_RESULTS = 50
KEENABLE_MAX_TITLE_CHARS = 256
KEENABLE_MAX_URL_CHARS = 2048
KEENABLE_MAX_SNIPPET_CHARS = 1200


def _truncate_text(value: Any, limit: int) -> str:
    """Trim whitespace and cap ``value`` to ``limit`` characters."""
    text = str(value or "").strip()
    if len(text) > limit:
        return text[:limit - 1] + "\u2026"
    return text


class _NoRedirect(HTTPRedirectHandler):
    """Redirect handler that refuses to follow any redirect.

    Keenable never redirects. Following a 3xx would resend ``X-API-Key`` to
    whatever host it points at, so the redirect is dropped (urllib then raises
    the 3xx as an error, surfaced to the caller) and no second request is sent.
    """

    def redirect_request(self, *args, **kwargs):
        """Return ``None`` so urllib does not issue a follow-up request."""
        return None


class KeenableSearchTool(BaseTool):
    """Tool for keyless (or keyed) web search using Keenable."""

    name = "keenable_search"
    description = "Search the web using Keenable (keyless; an API key raises limits)."

    def __init__(self, api_key: Optional[str] = None):
        """Create the tool, resolving the API key from the argument or env.

        Args:
            api_key: Optional Keenable API key. Falls back to the
                ``KEENABLE_API_KEY`` environment variable; keyless if unset.
        """
        self.api_key = (api_key or os.getenv("KEENABLE_API_KEY") or "").strip()
        super().__init__()

    def run(
        self,
        action: str = "search",
        query: Optional[str] = None,
        max_results: int = 5,
        **kwargs,
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        """Dispatch a Keenable action; only ``search`` is supported."""
        action = action.lower().replace("-", "_")
        if action == "search":
            return self.search(query=query, max_results=max_results)
        return {"error": f"Unknown action: {action}"}

    def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search the web with Keenable.

        Args:
            query: Search query string.
            max_results: Maximum results to return (capped at 50).

        Returns:
            List of dicts with ``title``, ``url``, ``snippet`` and ``provider``,
            or a single-item list with an ``error`` key on failure.
        """
        if not query:
            return [{"error": "query is required"}]

        result_limit = max(0, min(int(max_results), KEENABLE_MAX_RESULTS))
        if result_limit == 0:
            return []

        from urllib.error import URLError
        from urllib.request import Request, build_opener

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "praisonai-tools",
            # Required on keyless calls; names the app, carries no user identifier.
            "X-Keenable-Title": KEENABLE_APP_TITLE,
        }
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        body = json.dumps({
            "query": query,
            "max_results": result_limit,
            "snippet_max_length": KEENABLE_MAX_SNIPPET_CHARS,
        }).encode("utf-8")
        request = Request(
            KEENABLE_SEARCH_URL if self.api_key else KEENABLE_PUBLIC_SEARCH_URL,
            data=body,
            headers=headers,
            method="POST",
        )

        try:
            opener = build_opener(_NoRedirect)
            with opener.open(request, timeout=KEENABLE_SEARCH_TIMEOUT_SECONDS) as response:
                raw = response.read(KEENABLE_MAX_RESPONSE_BYTES + 1)
        except URLError as exc:
            logger.error(f"Keenable search error: {exc}")
            return [{"error": str(exc)}]
        except Exception as exc:
            logger.error(f"Keenable search error: {exc}")
            return [{"error": str(exc)}]

        if len(raw) > KEENABLE_MAX_RESPONSE_BYTES:
            return [{"error": "Keenable returned an oversized response"}]

        try:
            payload = json.loads(raw)
        except ValueError as exc:
            return [{"error": f"Keenable returned invalid JSON: {exc}"}]
        if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
            return [{"error": "Keenable returned an invalid response shape"}]

        results = []
        for result in payload["results"]:
            if not isinstance(result, dict):
                continue
            url = result.get("url")
            if not isinstance(url, str) or not url or len(url) > KEENABLE_MAX_URL_CHARS:
                continue
            # The page text is in `snippet`; `description` is usually empty.
            snippet = " ".join(str(result.get("snippet") or result.get("description") or "").split())
            results.append({
                "title": _truncate_text(result.get("title", ""), KEENABLE_MAX_TITLE_CHARS),
                "url": url,
                "snippet": _truncate_text(snippet, KEENABLE_MAX_SNIPPET_CHARS),
                "provider": "keenable",
            })
            if len(results) >= result_limit:
                break
        return results


def keenable_search(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """Search the web with Keenable (keyless; KEENABLE_API_KEY raises limits)."""
    return KeenableSearchTool().search(query=query, max_results=max_results)
