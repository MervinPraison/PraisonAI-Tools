"""Serper Tool for PraisonAI Agents.

Google search using Serper API.

Usage:
    from praisonai_tools import SerperTool
    
    serper = SerperTool()
    results = serper.search("Python programming")

Environment Variables:
    SERPER_API_KEY: Serper API key
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class SerperTool(BaseTool):
    """Tool for Google search using Serper."""
    
    name = "serper"
    description = "Search Google using Serper API."
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("SERPER_API_KEY")
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
        elif action == "images":
            return self.images(query=query, max_results=max_results)
        else:
            return {"error": f"Unknown action: {action}"}
    
    def _request(self, endpoint: str, query: str, num: int = 10) -> Dict:
        """Make Serper API request."""
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}
        
        if not self.api_key:
            return {"error": "SERPER_API_KEY not configured"}
        
        try:
            response = requests.post(
                f"https://google.serper.dev/{endpoint}",
                headers={"X-API-KEY": self.api_key, "Content-Type": "application/json"},
                json={"q": query, "num": num},
                timeout=10,
            )
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def search(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search Google."""
        if not query:
            return [{"error": "query is required"}]
        
        result = self._request("search", query, max_results)
        if "error" in result:
            return [result]
        
        results = []
        for item in result.get("organic", []):
            results.append({
                "title": item.get("title"),
                "url": item.get("link"),
                "snippet": item.get("snippet"),
                "position": item.get("position"),
            })
        return results
    
    def news(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search Google News."""
        if not query:
            return [{"error": "query is required"}]
        
        result = self._request("news", query, max_results)
        if "error" in result:
            return [result]
        
        results = []
        for item in result.get("news", []):
            results.append({
                "title": item.get("title"),
                "url": item.get("link"),
                "source": item.get("source"),
                "date": item.get("date"),
                "snippet": item.get("snippet"),
            })
        return results
    
    def images(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search Google Images."""
        if not query:
            return [{"error": "query is required"}]
        
        result = self._request("images", query, max_results)
        if "error" in result:
            return [result]
        
        results = []
        for item in result.get("images", []):
            results.append({
                "title": item.get("title"),
                "image_url": item.get("imageUrl"),
                "source": item.get("source"),
            })
        return results


def serper_search(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """Search with Serper."""
    return SerperTool().search(query=query, max_results=max_results)
