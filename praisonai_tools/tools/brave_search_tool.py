"""Brave Search Tool for PraisonAI Agents.

Web search using Brave Search API.

Usage:
    from praisonai_tools import BraveSearchTool
    
    brave = BraveSearchTool()
    results = brave.search("AI news")

Environment Variables:
    BRAVE_API_KEY: Brave Search API key
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class BraveSearchTool(BaseTool):
    """Tool for Brave Search."""
    
    name = "brave_search"
    description = "Search the web using Brave Search API."
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("BRAVE_API_KEY")
        super().__init__()
    
    def run(
        self,
        action: str = "search",
        query: Optional[str] = None,
        count: int = 10,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "search":
            return self.search(query=query, count=count)
        elif action == "news":
            return self.news(query=query, count=count)
        else:
            return {"error": f"Unknown action: {action}"}
    
    def search(self, query: str, count: int = 10) -> List[Dict[str, Any]]:
        """Search the web."""
        if not query:
            return [{"error": "query is required"}]
        if not self.api_key:
            return [{"error": "BRAVE_API_KEY required"}]
        
        try:
            import requests
        except ImportError:
            return [{"error": "requests not installed"}]
        
        try:
            headers = {"X-Subscription-Token": self.api_key}
            params = {"q": query, "count": count}
            resp = requests.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers=headers,
                params=params,
                timeout=10,
            )
            data = resp.json()
            
            results = []
            for item in data.get("web", {}).get("results", [])[:count]:
                results.append({
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "description": item.get("description"),
                })
            return results
        except Exception as e:
            logger.error(f"Brave search error: {e}")
            return [{"error": str(e)}]
    
    def news(self, query: str, count: int = 10) -> List[Dict[str, Any]]:
        """Search news."""
        if not query:
            return [{"error": "query is required"}]
        if not self.api_key:
            return [{"error": "BRAVE_API_KEY required"}]
        
        try:
            import requests
        except ImportError:
            return [{"error": "requests not installed"}]
        
        try:
            headers = {"X-Subscription-Token": self.api_key}
            params = {"q": query, "count": count}
            resp = requests.get(
                "https://api.search.brave.com/res/v1/news/search",
                headers=headers,
                params=params,
                timeout=10,
            )
            data = resp.json()
            
            results = []
            for item in data.get("results", [])[:count]:
                results.append({
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "description": item.get("description"),
                    "age": item.get("age"),
                })
            return results
        except Exception as e:
            logger.error(f"Brave news error: {e}")
            return [{"error": str(e)}]


def brave_search(query: str, count: int = 10) -> List[Dict[str, Any]]:
    """Search with Brave."""
    return BraveSearchTool().search(query=query, count=count)
