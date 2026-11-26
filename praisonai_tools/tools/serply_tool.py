"""Serply Tool for PraisonAI Agents.

Google Scholar search using the Serply API (https://serply.io).
API reference: https://serply.io/docs

Usage:
    from praisonai_tools import SerplyTool

    papers = SerplyTool().scholar("large language models")

Environment Variables:
    SERPLY_API_KEY: Serply API key
"""

import os
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

SERPLY_SCHOLAR_URL = "https://api.serply.io/v1/scholar/"


class SerplyTool(BaseTool):
    """Tool for Google Scholar search using Serply."""

    name = "serply"
    description = "Search Google Scholar for papers, authors, and citation counts using the Serply API."

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("SERPLY_API_KEY")
        super().__init__()

    def run(
        self,
        action: str = "scholar",
        query: Optional[str] = None,
        max_results: int = 10,
        **kwargs
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        if action.lower() == "scholar":
            return self.scholar(query=query, max_results=max_results)
        return {"error": f"Unknown action: {action}"}

    def scholar(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search Google Scholar."""
        if not query:
            return [{"error": "query is required"}]
        if not self.api_key:
            return [{"error": "SERPLY_API_KEY not configured"}]
        try:
            import requests
        except ImportError:
            return [{"error": "requests not installed"}]

        try:
            # One Serply page holds at most 10 results.
            num = max(1, min(int(max_results), 10))
        except (TypeError, ValueError):
            num = 10

        try:
            response = requests.get(
                SERPLY_SCHOLAR_URL,
                headers={"X-Api-Key": self.api_key, "Accept": "application/json"},
                params={"q": query, "num": num},
                # Uncached Scholar queries can take 10 to 15 seconds.
                timeout=30,
                # requests forwards X-Api-Key to redirect targets, so never follow them.
                allow_redirects=False,
            )
            if not 200 <= response.status_code < 300:
                return [{"error": f"Serply API error {response.status_code}: {response.text[:200]}"}]
            data = response.json()
        except Exception as e:
            return [{"error": str(e)}]

        results = []
        for item in data.get("articles", [])[:num]:
            citations = (item.get("extras") or {}).get("citations") or {}
            results.append({
                "title": item.get("title"),
                "url": item.get("link"),
                "authors": (item.get("author") or {}).get("names"),
                "snippet": item.get("description"),
                "citations": citations.get("count"),
                "document_url": (item.get("doc") or {}).get("link"),
            })
        return results


def serply_scholar_search(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """Search Google Scholar with Serply."""
    return SerplyTool().scholar(query=query, max_results=max_results)
