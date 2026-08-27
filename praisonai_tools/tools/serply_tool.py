"""Serply Tool for PraisonAI Agents.

Google web, news, and scholar search using the Serply API (https://serply.io).
API reference: https://serply.io/docs

Usage:
    from praisonai_tools import SerplyTool

    serply = SerplyTool()
    results = serply.search("Python programming")
    papers = serply.scholar("large language models")

Environment Variables:
    SERPLY_API_KEY: Serply API key
"""

import os
import re
import html
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)

SERPLY_BASE_URL = "https://api.serply.io/v1"
# One Serply page holds at most 10 results; larger values are ignored server-side.
_MAX_PAGE_SIZE = 10


def _page_size(max_results: Any) -> int:
    """Clamp a requested result count to the 1..10 range the API serves."""
    try:
        n = int(max_results)
    except (TypeError, ValueError):
        return _MAX_PAGE_SIZE
    return max(1, min(n, _MAX_PAGE_SIZE))


class SerplyTool(BaseTool):
    """Tool for Google web, news, and scholar search using Serply."""

    name = "serply"
    description = "Search Google web, news, and scholar results using the Serply API."

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("SERPLY_API_KEY")
        super().__init__()

    def run(
        self,
        action: str = "search",
        query: Optional[str] = None,
        max_results: int = 10,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")

        if action == "search":
            return self.search(query=query, max_results=max_results)
        elif action == "news":
            return self.news(query=query, max_results=max_results)
        elif action == "scholar":
            return self.scholar(query=query, max_results=max_results)
        else:
            return {"error": f"Unknown action: {action}"}

    def _request(self, endpoint: str, query: str, num: int = 10) -> Dict:
        """Make a Serply API request."""
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}

        if not self.api_key:
            return {"error": "SERPLY_API_KEY not configured"}

        try:
            response = requests.get(
                f"{SERPLY_BASE_URL}/{endpoint}/",
                headers={"X-Api-Key": self.api_key, "Accept": "application/json"},
                params={"q": query, "num": num},
                timeout=10,
            )
            if not response.ok:
                return {"error": f"Serply API error {response.status_code}: {response.text[:200]}"}
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def search(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search Google."""
        if not query:
            return [{"error": "query is required"}]

        max_results = _page_size(max_results)
        result = self._request("search", query, max_results)
        if "error" in result:
            return [result]

        results = []
        for item in result.get("results", [])[:max_results]:
            results.append({
                "title": item.get("title"),
                "url": item.get("link"),
                "snippet": item.get("description"),
                "position": item.get("position"),
            })
        return results

    def news(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search Google News."""
        if not query:
            return [{"error": "query is required"}]

        max_results = _page_size(max_results)
        result = self._request("news", query, max_results)
        if "error" in result:
            return [result]

        results = []
        for item in result.get("entries", [])[:max_results]:
            source = item.get("source") or {}
            results.append({
                "title": item.get("title"),
                "url": item.get("link"),
                "source": source.get("title"),
                "date": item.get("published"),
                "snippet": " ".join(html.unescape(re.sub(r"<[^>]+>", "", item.get("summary") or "")).split()),
            })
        return results

    def scholar(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search Google Scholar."""
        if not query:
            return [{"error": "query is required"}]

        max_results = _page_size(max_results)
        result = self._request("scholar", query, max_results)
        if "error" in result:
            return [result]

        results = []
        for item in result.get("articles", [])[:max_results]:
            author = item.get("author") or {}
            citations = (item.get("extras") or {}).get("citations") or {}
            results.append({
                "title": item.get("title"),
                "url": item.get("link"),
                "authors": author.get("names"),
                "snippet": item.get("description"),
                "citations": citations.get("count"),
                "document_url": (item.get("doc") or {}).get("link"),
            })
        return results


def serply_search(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """Search Google with Serply."""
    return SerplyTool().search(query=query, max_results=max_results)


def serply_news_search(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """Search Google News with Serply."""
    return SerplyTool().news(query=query, max_results=max_results)


def serply_scholar_search(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """Search Google Scholar with Serply."""
    return SerplyTool().scholar(query=query, max_results=max_results)
