"""SerpAPI Tool for PraisonAI Agents.

Google search using SerpAPI.

Usage:
    from praisonai_tools import SerpAPITool
    
    serp = SerpAPITool()
    results = serp.search("AI news")

Environment Variables:
    SERPAPI_API_KEY: SerpAPI key
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class SerpAPITool(BaseTool):
    """Tool for SerpAPI Google search."""
    
    name = "serpapi"
    description = "Search Google using SerpAPI."
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("SERPAPI_API_KEY")
        super().__init__()
    
    def run(
        self,
        action: str = "search",
        query: Optional[str] = None,
        num: int = 10,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "search":
            return self.search(query=query, num=num)
        elif action == "images":
            return self.images(query=query, num=num)
        elif action == "news":
            return self.news(query=query, num=num)
        else:
            return {"error": f"Unknown action: {action}"}
    
    def search(self, query: str, num: int = 10) -> List[Dict[str, Any]]:
        """Google search."""
        if not query:
            return [{"error": "query is required"}]
        if not self.api_key:
            return [{"error": "SERPAPI_API_KEY required"}]
        
        try:
            import requests
        except ImportError:
            return [{"error": "requests not installed"}]
        
        try:
            params = {
                "q": query,
                "api_key": self.api_key,
                "num": num,
            }
            resp = requests.get("https://serpapi.com/search", params=params, timeout=10)
            data = resp.json()
            
            results = []
            for item in data.get("organic_results", [])[:num]:
                results.append({
                    "title": item.get("title"),
                    "url": item.get("link"),
                    "snippet": item.get("snippet"),
                })
            return results
        except Exception as e:
            logger.error(f"SerpAPI search error: {e}")
            return [{"error": str(e)}]
    
    def images(self, query: str, num: int = 10) -> List[Dict[str, Any]]:
        """Image search."""
        if not query:
            return [{"error": "query is required"}]
        if not self.api_key:
            return [{"error": "SERPAPI_API_KEY required"}]
        
        try:
            import requests
        except ImportError:
            return [{"error": "requests not installed"}]
        
        try:
            params = {
                "q": query,
                "api_key": self.api_key,
                "tbm": "isch",
            }
            resp = requests.get("https://serpapi.com/search", params=params, timeout=10)
            data = resp.json()
            
            results = []
            for item in data.get("images_results", [])[:num]:
                results.append({
                    "title": item.get("title"),
                    "url": item.get("original"),
                    "thumbnail": item.get("thumbnail"),
                })
            return results
        except Exception as e:
            logger.error(f"SerpAPI images error: {e}")
            return [{"error": str(e)}]
    
    def news(self, query: str, num: int = 10) -> List[Dict[str, Any]]:
        """News search."""
        if not query:
            return [{"error": "query is required"}]
        if not self.api_key:
            return [{"error": "SERPAPI_API_KEY required"}]
        
        try:
            import requests
        except ImportError:
            return [{"error": "requests not installed"}]
        
        try:
            params = {
                "q": query,
                "api_key": self.api_key,
                "tbm": "nws",
            }
            resp = requests.get("https://serpapi.com/search", params=params, timeout=10)
            data = resp.json()
            
            results = []
            for item in data.get("news_results", [])[:num]:
                results.append({
                    "title": item.get("title"),
                    "url": item.get("link"),
                    "source": item.get("source"),
                    "date": item.get("date"),
                })
            return results
        except Exception as e:
            logger.error(f"SerpAPI news error: {e}")
            return [{"error": str(e)}]


def serpapi_search(query: str, num: int = 10) -> List[Dict[str, Any]]:
    """Search with SerpAPI."""
    return SerpAPITool().search(query=query, num=num)
