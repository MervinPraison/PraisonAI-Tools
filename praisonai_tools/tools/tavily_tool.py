"""Tavily Search Tool for PraisonAI Agents.

AI-powered web search using Tavily API.

Usage:
    from praisonai_tools import TavilyTool
    
    tavily = TavilyTool()
    results = tavily.search("What is quantum computing?")

Environment Variables:
    TAVILY_API_KEY: Tavily API key
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class TavilyTool(BaseTool):
    """Tool for AI-powered web search using Tavily."""
    
    name = "tavily"
    description = "Search the web with AI-powered results using Tavily."
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        search_depth: str = "advanced",
        include_answer: bool = True,
        max_tokens: int = 6000,
    ):
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")
        self.search_depth = search_depth
        self.include_answer = include_answer
        self.max_tokens = max_tokens
        self._client = None
        super().__init__()
    
    @property
    def client(self):
        if self._client is None:
            if not self.api_key:
                raise ValueError("TAVILY_API_KEY is required")
            try:
                from tavily import TavilyClient
            except ImportError:
                raise ImportError("tavily-python not installed. Install with: pip install tavily-python")
            self._client = TavilyClient(api_key=self.api_key)
        return self._client
    
    def run(
        self,
        action: str = "search",
        query: Optional[str] = None,
        max_results: int = 5,
        urls: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "search":
            return self.search(query=query, max_results=max_results)
        elif action == "search_context":
            return self.search_context(query=query)
        elif action == "extract":
            return self.extract(urls=urls)
        else:
            return {"error": f"Unknown action: {action}"}
    
    def search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Search the web."""
        if not query:
            return {"error": "query is required"}
        
        if not self.api_key:
            return {"error": "TAVILY_API_KEY not configured"}
        
        try:
            response = self.client.search(
                query=query,
                search_depth=self.search_depth,
                include_answer=self.include_answer,
                max_results=max_results,
            )
            
            result = {"query": query}
            
            if "answer" in response:
                result["answer"] = response["answer"]
            
            results = []
            for r in response.get("results", []):
                results.append({
                    "title": r.get("title"),
                    "url": r.get("url"),
                    "content": r.get("content"),
                    "score": r.get("score"),
                })
            result["results"] = results
            
            return result
        except Exception as e:
            logger.error(f"Tavily search error: {e}")
            return {"error": str(e)}
    
    def search_context(self, query: str) -> str:
        """Get search context for RAG."""
        if not query:
            return "Error: query is required"
        
        if not self.api_key:
            return "Error: TAVILY_API_KEY not configured"
        
        try:
            return self.client.get_search_context(
                query=query,
                search_depth=self.search_depth,
                max_tokens=self.max_tokens,
            )
        except Exception as e:
            logger.error(f"Tavily search_context error: {e}")
            return f"Error: {e}"
    
    def extract(self, urls: str) -> List[Dict[str, Any]]:
        """Extract content from URLs."""
        if not urls:
            return [{"error": "urls is required"}]
        
        if not self.api_key:
            return [{"error": "TAVILY_API_KEY not configured"}]
        
        try:
            url_list = [u.strip() for u in urls.split(",") if u.strip()]
            response = self.client.extract(urls=url_list)
            
            results = []
            for r in response.get("results", []):
                results.append({
                    "url": r.get("url"),
                    "content": r.get("raw_content", "")[:2000],
                })
            return results
        except Exception as e:
            logger.error(f"Tavily extract error: {e}")
            return [{"error": str(e)}]


def tavily_search(query: str, max_results: int = 5) -> Dict[str, Any]:
    """Search with Tavily."""
    return TavilyTool().search(query=query, max_results=max_results)
