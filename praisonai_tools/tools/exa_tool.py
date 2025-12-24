"""Exa Search Tool for PraisonAI Agents.

AI-powered search using Exa API.

Usage:
    from praisonai_tools import ExaTool
    
    exa = ExaTool()
    results = exa.search("machine learning papers")

Environment Variables:
    EXA_API_KEY: Exa API key
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class ExaTool(BaseTool):
    """Tool for Exa AI-powered search."""
    
    name = "exa"
    description = "AI-powered web search using Exa."
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("EXA_API_KEY")
        self._client = None
        super().__init__()
    
    @property
    def client(self):
        if self._client is None:
            try:
                from exa_py import Exa
            except ImportError:
                raise ImportError("exa-py not installed. Install with: pip install exa-py")
            
            if not self.api_key:
                raise ValueError("EXA_API_KEY required")
            
            self._client = Exa(api_key=self.api_key)
        return self._client
    
    def run(
        self,
        action: str = "search",
        query: Optional[str] = None,
        url: Optional[str] = None,
        num_results: int = 10,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "search":
            return self.search(query=query, num_results=num_results, **kwargs)
        elif action == "find_similar":
            return self.find_similar(url=url, num_results=num_results)
        elif action == "get_contents":
            return self.get_contents(urls=kwargs.get("urls", []))
        else:
            return {"error": f"Unknown action: {action}"}
    
    def search(
        self,
        query: str,
        num_results: int = 10,
        use_autoprompt: bool = True,
        include_domains: List[str] = None,
        exclude_domains: List[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search with Exa."""
        if not query:
            return [{"error": "query is required"}]
        
        try:
            params = {
                "query": query,
                "num_results": num_results,
                "use_autoprompt": use_autoprompt,
            }
            if include_domains:
                params["include_domains"] = include_domains
            if exclude_domains:
                params["exclude_domains"] = exclude_domains
            
            results = self.client.search(**params)
            
            return [
                {
                    "title": r.title,
                    "url": r.url,
                    "score": r.score,
                    "published_date": r.published_date,
                }
                for r in results.results
            ]
        except Exception as e:
            logger.error(f"Exa search error: {e}")
            return [{"error": str(e)}]
    
    def find_similar(self, url: str, num_results: int = 10) -> List[Dict[str, Any]]:
        """Find similar pages."""
        if not url:
            return [{"error": "url is required"}]
        
        try:
            results = self.client.find_similar(url=url, num_results=num_results)
            return [
                {
                    "title": r.title,
                    "url": r.url,
                    "score": r.score,
                }
                for r in results.results
            ]
        except Exception as e:
            logger.error(f"Exa find_similar error: {e}")
            return [{"error": str(e)}]
    
    def get_contents(self, urls: List[str]) -> List[Dict[str, Any]]:
        """Get page contents."""
        if not urls:
            return [{"error": "urls is required"}]
        
        try:
            results = self.client.get_contents(urls)
            return [
                {
                    "url": r.url,
                    "title": r.title,
                    "text": r.text[:2000] if r.text else "",
                }
                for r in results.results
            ]
        except Exception as e:
            logger.error(f"Exa get_contents error: {e}")
            return [{"error": str(e)}]


def exa_search(query: str, num_results: int = 10) -> List[Dict[str, Any]]:
    """Search with Exa."""
    return ExaTool().search(query=query, num_results=num_results)
