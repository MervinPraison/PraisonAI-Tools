"""Giphy Tool for PraisonAI Agents.

Search and get GIFs from Giphy.

Usage:
    from praisonai_tools import GiphyTool
    
    giphy = GiphyTool()
    gifs = giphy.search("funny cat")

Environment Variables:
    GIPHY_API_KEY: Giphy API key
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class GiphyTool(BaseTool):
    """Tool for Giphy GIF search."""
    
    name = "giphy"
    description = "Search and get GIFs from Giphy."
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GIPHY_API_KEY")
        super().__init__()
    
    def run(
        self,
        action: str = "search",
        query: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        if action == "search":
            return self.search(query=query, **kwargs)
        elif action == "trending":
            return self.trending(**kwargs)
        elif action == "random":
            return self.random(tag=kwargs.get("tag"))
        return {"error": f"Unknown action: {action}"}
    
    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search GIFs."""
        if not query:
            return [{"error": "query is required"}]
        if not self.api_key:
            return [{"error": "GIPHY_API_KEY required"}]
        
        try:
            import requests
        except ImportError:
            return [{"error": "requests not installed"}]
        
        try:
            params = {"api_key": self.api_key, "q": query, "limit": limit}
            resp = requests.get("https://api.giphy.com/v1/gifs/search", params=params, timeout=10)
            data = resp.json()
            
            gifs = []
            for g in data.get("data", []):
                gifs.append({
                    "id": g.get("id"),
                    "title": g.get("title"),
                    "url": g.get("url"),
                    "gif_url": g.get("images", {}).get("original", {}).get("url"),
                })
            return gifs
        except Exception as e:
            logger.error(f"Giphy search error: {e}")
            return [{"error": str(e)}]
    
    def trending(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get trending GIFs."""
        if not self.api_key:
            return [{"error": "GIPHY_API_KEY required"}]
        
        try:
            import requests
        except ImportError:
            return [{"error": "requests not installed"}]
        
        try:
            params = {"api_key": self.api_key, "limit": limit}
            resp = requests.get("https://api.giphy.com/v1/gifs/trending", params=params, timeout=10)
            data = resp.json()
            
            gifs = []
            for g in data.get("data", []):
                gifs.append({
                    "id": g.get("id"),
                    "title": g.get("title"),
                    "url": g.get("url"),
                    "gif_url": g.get("images", {}).get("original", {}).get("url"),
                })
            return gifs
        except Exception as e:
            logger.error(f"Giphy trending error: {e}")
            return [{"error": str(e)}]
    
    def random(self, tag: str = None) -> Dict[str, Any]:
        """Get random GIF."""
        if not self.api_key:
            return {"error": "GIPHY_API_KEY required"}
        
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}
        
        try:
            params = {"api_key": self.api_key}
            if tag:
                params["tag"] = tag
            resp = requests.get("https://api.giphy.com/v1/gifs/random", params=params, timeout=10)
            data = resp.json().get("data", {})
            
            return {
                "id": data.get("id"),
                "title": data.get("title"),
                "url": data.get("url"),
                "gif_url": data.get("images", {}).get("original", {}).get("url"),
            }
        except Exception as e:
            logger.error(f"Giphy random error: {e}")
            return {"error": str(e)}


def giphy_search(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Search Giphy."""
    return GiphyTool().search(query=query, limit=limit)
