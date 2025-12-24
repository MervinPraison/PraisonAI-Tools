"""LinkUp Tool for PraisonAI Agents.

Search using LinkUp API.

Usage:
    from praisonai_tools import LinkUpTool
    
    linkup = LinkUpTool()
    results = linkup.search("AI news")

Environment Variables:
    LINKUP_API_KEY: LinkUp API key
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class LinkUpTool(BaseTool):
    """Tool for LinkUp search."""
    
    name = "linkup"
    description = "Search using LinkUp API."
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("LINKUP_API_KEY")
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
    
    def search(self, query: str, depth: str = "standard", output_type: str = "searchResults") -> List[Dict[str, Any]]:
        """Search LinkUp."""
        if not query:
            return [{"error": "query is required"}]
        if not self.api_key:
            return [{"error": "LINKUP_API_KEY required"}]
        
        try:
            import requests
        except ImportError:
            return [{"error": "requests not installed"}]
        
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            data = {"q": query, "depth": depth, "outputType": output_type}
            resp = requests.post(
                "https://api.linkup.so/v1/search",
                headers=headers,
                json=data,
                timeout=30,
            )
            result = resp.json()
            
            if output_type == "searchResults":
                return result.get("results", [])
            return [{"content": result.get("answer", "")}]
        except Exception as e:
            logger.error(f"LinkUp search error: {e}")
            return [{"error": str(e)}]


def linkup_search(query: str) -> List[Dict[str, Any]]:
    """Search with LinkUp."""
    return LinkUpTool().search(query=query)
