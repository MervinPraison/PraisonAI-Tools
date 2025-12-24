"""SearxNG Tool for PraisonAI Agents.

Privacy-respecting metasearch using SearxNG.

Usage:
    from praisonai_tools import SearxNGTool
    
    searx = SearxNGTool()
    results = searx.search("AI news")

Environment Variables:
    SEARXNG_URL: SearxNG instance URL
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class SearxNGTool(BaseTool):
    """Tool for SearxNG metasearch."""
    
    name = "searxng"
    description = "Privacy-respecting metasearch using SearxNG."
    
    def __init__(self, url: Optional[str] = None):
        self.url = url or os.getenv("SEARXNG_URL", "https://searx.be")
        super().__init__()
    
    def run(
        self,
        action: str = "search",
        query: Optional[str] = None,
        categories: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        if action == "search":
            return self.search(query=query, categories=categories, **kwargs)
        return {"error": f"Unknown action: {action}"}
    
    def search(self, query: str, categories: str = "general", num: int = 10) -> List[Dict[str, Any]]:
        """Search SearxNG."""
        if not query:
            return [{"error": "query is required"}]
        
        try:
            import requests
        except ImportError:
            return [{"error": "requests not installed"}]
        
        try:
            params = {"q": query, "format": "json", "categories": categories}
            resp = requests.get(f"{self.url}/search", params=params, timeout=10)
            data = resp.json()
            
            results = []
            for item in data.get("results", [])[:num]:
                results.append({
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "content": item.get("content"),
                    "engine": item.get("engine"),
                })
            return results
        except Exception as e:
            logger.error(f"SearxNG search error: {e}")
            return [{"error": str(e)}]


def searxng_search(query: str, num: int = 10) -> List[Dict[str, Any]]:
    """Search with SearxNG."""
    return SearxNGTool().search(query=query, num=num)
