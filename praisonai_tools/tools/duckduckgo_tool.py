"""DuckDuckGo Search Tool for PraisonAI Agents.

Search the web using DuckDuckGo.

Usage:
    from praisonai_tools import DuckDuckGoTool
    
    ddg = DuckDuckGoTool()
    results = ddg.search("Python programming")
    news = ddg.news("AI technology")
"""

import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class DuckDuckGoTool(BaseTool):
    """Tool for searching with DuckDuckGo."""
    
    name = "duckduckgo"
    description = "Search the web and get news using DuckDuckGo."
    
    def __init__(
        self,
        proxy: Optional[str] = None,
        timeout: int = 10,
    ):
        self.proxy = proxy
        self.timeout = timeout
        super().__init__()
    
    def run(
        self,
        action: str = "search",
        query: Optional[str] = None,
        max_results: int = 5,
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
    
    def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search the web."""
        if not query:
            return [{"error": "query is required"}]
        
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            return [{"error": "duckduckgo-search not installed. Install with: pip install duckduckgo-search"}]
        
        try:
            with DDGS(proxy=self.proxy, timeout=self.timeout) as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
            
            return [
                {
                    "title": r.get("title"),
                    "url": r.get("href"),
                    "snippet": r.get("body"),
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"DuckDuckGo search error: {e}")
            return [{"error": str(e)}]
    
    def news(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Get news articles."""
        if not query:
            return [{"error": "query is required"}]
        
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            return [{"error": "duckduckgo-search not installed"}]
        
        try:
            with DDGS(proxy=self.proxy, timeout=self.timeout) as ddgs:
                results = list(ddgs.news(query, max_results=max_results))
            
            return [
                {
                    "title": r.get("title"),
                    "url": r.get("url"),
                    "source": r.get("source"),
                    "date": r.get("date"),
                    "snippet": r.get("body"),
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"DuckDuckGo news error: {e}")
            return [{"error": str(e)}]
    
    def images(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search for images."""
        if not query:
            return [{"error": "query is required"}]
        
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            return [{"error": "duckduckgo-search not installed"}]
        
        try:
            with DDGS(proxy=self.proxy, timeout=self.timeout) as ddgs:
                results = list(ddgs.images(query, max_results=max_results))
            
            return [
                {
                    "title": r.get("title"),
                    "image_url": r.get("image"),
                    "thumbnail": r.get("thumbnail"),
                    "source": r.get("source"),
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"DuckDuckGo images error: {e}")
            return [{"error": str(e)}]


def duckduckgo_search(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """Search DuckDuckGo."""
    return DuckDuckGoTool().search(query=query, max_results=max_results)
