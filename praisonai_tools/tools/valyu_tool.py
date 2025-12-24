"""Valyu Tool for PraisonAI Agents.

Search using Valyu API.

Usage:
    from praisonai_tools import ValyuTool
    
    valyu = ValyuTool()
    results = valyu.search("AI news")

Environment Variables:
    VALYU_API_KEY: Valyu API key
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class ValyuTool(BaseTool):
    """Tool for Valyu search."""
    
    name = "valyu"
    description = "Search using Valyu API."
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("VALYU_API_KEY")
        super().__init__()
    
    def run(
        self,
        action: str = "search",
        query: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        if action == "search":
            return self.search(query=query, **kwargs)
        return {"error": f"Unknown action: {action}"}
    
    def search(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search Valyu."""
        if not query:
            return [{"error": "query is required"}]
        if not self.api_key:
            return [{"error": "VALYU_API_KEY required"}]
        
        try:
            import requests
        except ImportError:
            return [{"error": "requests not installed"}]
        
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            data = {"query": query, "max_results": max_results}
            resp = requests.post(
                "https://api.valyu.network/v1/search",
                headers=headers,
                json=data,
                timeout=30,
            )
            result = resp.json()
            return result.get("results", [])
        except Exception as e:
            logger.error(f"Valyu search error: {e}")
            return [{"error": str(e)}]


def valyu_search(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """Search with Valyu."""
    return ValyuTool().search(query=query, max_results=max_results)
